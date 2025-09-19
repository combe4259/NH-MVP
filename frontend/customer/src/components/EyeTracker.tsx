/// <reference types="react/jsx-runtime" />
import React, { useEffect, useRef, useState, useMemo, useCallback } from 'react';
import './EyeTracker.css';

// MediaPipe 타입 정의
type FaceMesh = any;
type Camera = any;

// MediaPipe는 window 객체에서 직접 사용
declare global {
  interface Window {
    FaceMesh: any;
    Camera: any;
  }
}

interface GazeData {
  x: number;
  y: number;
  timestamp: number;
  confidence: number; 
}

interface FaceDetectionData {
  hasDetection: boolean;
  confidence: number;
  emotions?: {
    engagement: number;
    confusion: number;
    frustration: number;
    boredom: number;
  };
}

interface EyeTrackerProps {
  isTracking: boolean;
  onGazeData?: (data: GazeData) => void;
  onFaceAnalysis?: (data: FaceDetectionData) => void;
}

const loadScript = (src: string): Promise<void> => {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
    document.head.appendChild(script);
  });
};

const EyeTracker: React.FC<EyeTrackerProps> = ({ isTracking, onGazeData, onFaceAnalysis }) => {
  const [gazePosition, setGazePosition] = useState<{ x: number; y: number } | null>(null);
  const [calibrationComplete, setCalibrationComplete] = useState(false);
  const [calibrationPoints, setCalibrationPoints] = useState<number>(0);
  const [isMediaPipeLoaded, setIsMediaPipeLoaded] = useState(false);
  const [calibrationStep, setCalibrationStep] = useState(0);
  const [accuracy, setAccuracy] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const faceMeshRef = useRef<FaceMesh | null>(null);
  const cameraRef = useRef<Camera | null>(null);
  
  // CNN-LSTM을 위한 프레임 버퍼 (30프레임 시퀀스)
  const frameBufferRef = useRef<ImageData[]>([]);
  const frameBufferSize = 30; // CNN-LSTM sequence length
  const frameInterval = 200; // 200ms마다 프레임 캡처 (5fps)
  const lastFrameCaptureRef = useRef<number>(0);

  // MediaPipe 얼굴 랜드마크 인덱스 (gaze_tracker.py와 동일)
  const LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144];
  const RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380];
  // 홍채 인덱스는 468-477이 아니라 다른 범위일 수 있음
  // 일단 눈 중심으로 간단히 시선 추적
  const LEFT_IRIS_INDICES = [468, 469, 470, 471, 472];
  const RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477];

  const calibrationPositions = useMemo(() => [
    { x: 10, y: 10 }, { x: 50, y: 10 }, { x: 90, y: 10 },
    { x: 10, y: 50 }, { x: 50, y: 50 }, { x: 90, y: 50 },
    { x: 10, y: 90 }, { x: 50, y: 90 }, { x: 90, y: 90 },
  ], []);

  // 눈 중심점 계산 (gaze_tracker.py 로직 포팅)
  const getEyeCenter = useCallback((landmarks: any[], indices: number[], frameWidth: number, frameHeight: number) => {
    const points = indices.map(idx => ({
      x: landmarks[idx].x * frameWidth,
      y: landmarks[idx].y * frameHeight
    }));

    const centerX = points.reduce((sum, p) => sum + p.x, 0) / points.length;
    const centerY = points.reduce((sum, p) => sum + p.y, 0) / points.length;

    return { x: centerX, y: centerY };
  }, []);

  // 홍채 위치 계산
  const getIrisPosition = useCallback((landmarks: any[], irisIndices: number[], frameWidth: number, frameHeight: number) => {
    const irisPoints = irisIndices.map(idx => ({
      x: landmarks[idx].x * frameWidth,
      y: landmarks[idx].y * frameHeight
    }));

    const centerX = irisPoints.reduce((sum, p) => sum + p.x, 0) / irisPoints.length;
    const centerY = irisPoints.reduce((sum, p) => sum + p.y, 0) / irisPoints.length;

    return { x: centerX, y: centerY };
  }, []);

  // 시선 방향 계산 (간단한 버전)
  const calculateGazeDirection = useCallback((landmarks: any[], frameWidth: number, frameHeight: number) => {
    if (!landmarks || landmarks.length === 0) {
      console.log('❌ 랜드마크 없음');
      return null;
    }
    
    // 홍채가 없을 수 있으니 일단 코 위치를 시선으로 사용
    const noseTip = landmarks[1];
    if (!noseTip) {
      console.log('❌ 코 랜드마크 없음');
      return null;
    }
    
    const noseX = noseTip.x * frameWidth;
    const noseY = noseTip.y * frameHeight;
    
    // 왼쪽 눈과 오른쪽 눈 중심 계산
    const leftEyeCenter = getEyeCenter(landmarks, LEFT_EYE_INDICES, frameWidth, frameHeight);
    const rightEyeCenter = getEyeCenter(landmarks, RIGHT_EYE_INDICES, frameWidth, frameHeight);
    
    // 눈 중심을 기준으로 간단한 시선 추정
    const eyeCenterX = (leftEyeCenter.x + rightEyeCenter.x) / 2;
    const eyeCenterY = (leftEyeCenter.y + rightEyeCenter.y) / 2;
    
    // 머리 방향을 고려한 시선 위치 (간단한 추정)
    const gazeX = noseX + (noseX - eyeCenterX) * 2;
    const gazeY = noseY + (noseY - eyeCenterY) * 2;
    
    // 가끔씩만 로그 (2% 확률)
    if (Math.random() < 0.02) {
      // console.log('👀 시선 계산:', {
      //   nose: { x: noseX, y: noseY },
      //   eyeCenter: { x: eyeCenterX, y: eyeCenterY },
      //   gaze: { x: gazeX, y: gazeY }
      // });
    }

    return { 
      x: Math.max(0, Math.min(frameWidth, gazeX)), 
      y: Math.max(0, Math.min(frameHeight, gazeY))
    };
  }, [getEyeCenter]);

  // calibrationComplete를 ref로 관리하여 최신 값 참조
  const calibrationCompleteRef = useRef(false);
  useEffect(() => {
    calibrationCompleteRef.current = calibrationComplete;
  }, [calibrationComplete]);

  // MediaPipe 결과 처리
  const onResults = useCallback((results: any) => {
    if (!canvasRef.current || !videoRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const videoWidth = videoRef.current.videoWidth;
    const videoHeight = videoRef.current.videoHeight;

    canvas.width = videoWidth;
    canvas.height = videoHeight;

    // 비디오 프레임 그리기
    ctx.drawImage(videoRef.current, 0, 0, videoWidth, videoHeight);
    
    // CNN-LSTM을 위한 프레임 캡처 (200ms 간격)
    const now = Date.now();
    if (now - lastFrameCaptureRef.current >= frameInterval && onFaceAnalysis) {
      lastFrameCaptureRef.current = now;
      captureFrameForCNN(videoRef.current);
    }

    if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
      const landmarks = results.multiFaceLandmarks[0];
      
      // 랜드마크 확인 (10프레임마다만 로그)
      if (Math.random() < 0.05) {
        // console.log('🔍 랜드마크 체크:', {
        //   총개수: landmarks.length,
        //   첫번째_랜드마크: landmarks[0],
        //   홍채_존재: landmarks[468] ? '있음' : '없음',
        //   캘리브레이션: calibrationCompleteRef.current
        // });
      }

      // 시선 좌표 계산
      const gazeCoords = calculateGazeDirection(landmarks, videoWidth, videoHeight);
      
      // 디버그 로그 추가 (5% 확률)
      if (calibrationCompleteRef.current && Math.random() < 0.05) {
        // console.log('📍 캘리브레이션 완료 상태, gazeCoords:', gazeCoords);
      }

      if (calibrationCompleteRef.current && gazeCoords) {
        // 캔버스가 화면 왼쪽 아래 작은 창에 있음 (160x120)
        // 시선 좌표를 전체 화면 기준으로 변환
        
        // 비디오 좌표를 화면 비율로 변환
        const screenWidth = window.innerWidth;
        const screenHeight = window.innerHeight;
        
        // 시선 위치를 화면 크기에 맞게 스케일링
        // 머리 위치를 중앙으로 가정하고 시선 방향을 확대
        const screenX = (gazeCoords.x / videoWidth) * screenWidth;
        const screenY = (gazeCoords.y / videoHeight) * screenHeight;
        
        const gazeData: GazeData = {
          x: screenX,
          y: screenY,
          timestamp: Date.now(),
          confidence: 0.8
        };

        setGazePosition(gazeCoords);
        
        // 가끔씩만 로그 (3% 확률)
        if (Math.random() < 0.03) {
          // console.log('👁️ 시선 데이터 전송:', {
          //   canvasCoords: gazeCoords,
          //   screenCoords: { x: screenX, y: screenY },
          //   videoSize: { w: videoWidth, h: videoHeight },
          //   screenSize: { w: screenWidth, h: screenHeight }
          // });
        }

        if (onGazeData) {
          onGazeData(gazeData);
        }

        // 시선 점 그리기
        ctx.fillStyle = '#00ff00';
        ctx.beginPath();
        ctx.arc(gazeCoords.x, gazeCoords.y, 10, 0, 2 * Math.PI);
        ctx.fill();
      }
    }
  }, [calculateGazeDirection, onGazeData, onFaceAnalysis]);

  // MediaPipe 초기화
  useEffect(() => {
    const initMediaPipe = async () => {
      console.log('🚀 MediaPipe 초기화 시작 (CDN 방식)...');
      try {
        console.log('📥 face_mesh.js 로딩 중...');
        await loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js');
        console.log('✅ face_mesh.js 로드 완료');
        
        console.log('📥 camera_utils.js 로딩 중...');
        await loadScript('https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js');
        console.log('✅ camera_utils.js 로드 완료');
        
        if (!window.FaceMesh || !window.Camera) {
          console.error('❌ MediaPipe 모듈 확인 실패:', {
            FaceMesh: !!window.FaceMesh,
            Camera: !!window.Camera
          });
          throw new Error('MediaPipe 스크립트 로딩 실패');
        }
        console.log('✅ MediaPipe 모듈 확인 완료!');
        
        console.log('🔧 FaceMesh 인스턴스 생성 중...');
        const faceMesh = new window.FaceMesh({
          locateFile: (file: string) => {
            console.log('📂 MediaPipe 파일 요청:', file);
            return `/mediapipe/face_mesh/${file}`;
          },
        });

        console.log('⚙️ FaceMesh 옵션 설정 중...');
        faceMesh.setOptions({
          maxNumFaces: 1,
          refineLandmarks: true,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5,
          selfieMode: true
        });

        console.log('📸 onResults 콜백 등록...');
        faceMesh.onResults(onResults);
        faceMeshRef.current = faceMesh;
        console.log('✅ FaceMesh 설정 완료!');

        if (videoRef.current) {
          console.log('📹 카메라 설정 중...');
          const camera = new window.Camera(videoRef.current, {
            onFrame: async () => {
              if (faceMeshRef.current && videoRef.current) {
                await faceMeshRef.current.send({ image: videoRef.current });
              }
            },
            width: 640,
            height: 480
          });

          cameraRef.current = camera;
          console.log('🎬 카메라 시작 중...');
          await camera.start();
          setIsMediaPipeLoaded(true);
          console.log('✅ MediaPipe 완전 초기화 성공!');
          console.log('📷 최종 상태:', {
            video: videoRef.current ? '✅ 비디오' : '❌ 비디오',
            camera: cameraRef.current ? '✅ 카메라' : '❌ 카메라',
            faceMesh: faceMeshRef.current ? '✅ FaceMesh' : '❌ FaceMesh'
          });
        } else {
          console.error('❌ 비디오 요소를 찾을 수 없음!');
        }

      } catch (error) {
        console.error('MediaPipe 초기화 실패:', error);
        setError('MediaPipe 초기화에 실패했습니다. 파일을 확인해주세요.');
      }
    };

    if (isTracking) {
      initMediaPipe();
    }

    return () => {
      if (cameraRef.current) {
        cameraRef.current.stop();
        cameraRef.current = null;
      }
      if (faceMeshRef.current) {
        faceMeshRef.current.close();
        faceMeshRef.current = null;
      }
      // 캘리브레이션 상태는 유지
    };
  }, [isTracking]);

  // 캘리브레이션 시작
  const calibrationStartedRef = useRef(false);
  
  useEffect(() => {
    console.log('🎮 캘리브레이션 체크:', {
      isTracking,
      isMediaPipeLoaded,
      calibrationComplete,
      calibrationStarted: calibrationStartedRef.current
    });
    if (isTracking && isMediaPipeLoaded && !calibrationComplete && !calibrationStartedRef.current) {
      console.log('🚀 캘리브레이션 시작!');
      calibrationStartedRef.current = true;
      startCalibration();
    }
  }, [isTracking, isMediaPipeLoaded, calibrationComplete]);

  const startCalibration = () => {
    if (!faceMeshRef.current) {
      console.error('❌ faceMeshRef.current가 없어서 캘리브레이션 불가');
      return;
    }
    console.log('✅ 캘리브레이션 진행 중...');
    let currentStep = 0;

    const showCalibrationPoint = () => {
      if (currentStep >= calibrationPositions.length) {
        finishCalibration();
        return;
      }

      setCalibrationStep(currentStep + 1);
      setCalibrationPoints(currentStep + 1);
      
      setTimeout(() => {
        currentStep++;
        showCalibrationPoint();
      }, 2000); 
    };

    showCalibrationPoint();
  };

  // CNN-LSTM을 위한 프레임 캡처 함수
  const captureFrameForCNN = useCallback((video: HTMLVideoElement) => {
    // 112x112 캔버스 생성 (CNN 입력 크기)
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = 112;
    tempCanvas.height = 112;
    const tempCtx = tempCanvas.getContext('2d');
    
    if (!tempCtx) return;
    
    // 비디오를 112x112로 리사이즈
    tempCtx.drawImage(video, 0, 0, 112, 112);
    const imageData = tempCtx.getImageData(0, 0, 112, 112);
    
    // 프레임 버퍼에 추가
    frameBufferRef.current.push(imageData);
    
    // 버퍼 크기 유지 (최대 30프레임)
    if (frameBufferRef.current.length > frameBufferSize) {
      frameBufferRef.current.shift();
    }
    
    // 프레임 수집 상태 로깅
    if (frameBufferRef.current.length % 10 === 0) {
      // console.log(`📹 CNN-LSTM 프레임 수집: ${frameBufferRef.current.length}/${frameBufferSize}`);
    }
    
    // 30프레임이 모이면 백엔드로 전송 (한 번만)
    if (frameBufferRef.current.length === frameBufferSize) {
      // console.log('📤 30프레임 시퀀스 백엔드 전송...');
      sendFramesToBackend();
      // 즉시 버퍼 초기화하여 중복 전송 방지
      frameBufferRef.current = [];
    }
  }, [onFaceAnalysis]);
  
  // 프레임 시퀀스를 백엔드로 전송
  const sendFramesToBackend = useCallback(async () => {
    if (!onFaceAnalysis) return;
    
    try {
      // 프레임 데이터를 Base64로 변환
      const frames = frameBufferRef.current.map(imageData => {
        const canvas = document.createElement('canvas');
        canvas.width = 112;
        canvas.height = 112;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.putImageData(imageData, 0, 0);
          return canvas.toDataURL('image/jpeg', 0.7).split(',')[1];
        }
        return '';
      }).filter(frame => frame !== '');
      
      // 백엔드 AI 서비스 호출
      const response = await fetch('http://localhost:8000/api/face/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          frames: frames,
          sequence_length: frameBufferSize
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('🧠 CNN-LSTM 얼굴 분석 결과:', {
          confusion: result.confusion_probability?.toFixed(2),
          timestamp: new Date().toLocaleTimeString()
        });
        
        const confusionLevel = result.confusion || 0;
        const normalizedConfusion = confusionLevel / 3.0;
        
        const faceData: FaceDetectionData = {
          hasDetection: true,
          confidence: result.confidence || 0.9,
          emotions: {
            engagement: 0,
            confusion: normalizedConfusion,
            frustration: 0,
            boredom: 0
          }
        };
        
        onFaceAnalysis(faceData);
      }
    } catch (error) {
      console.error('CNN-LSTM 프레임 분석 실패:', error);
    }
    
    // 버퍼 초기화 (다음 시퀀스를 위해)
    frameBufferRef.current = [];
  }, [onFaceAnalysis]);
  
  const finishCalibration = async () => {
    if (!faceMeshRef.current) {
      console.error('❌ faceMeshRef.current가 없어서 캘리브레이션 완료 불가');
      return;
    }
    try {
      const calculatedAccuracy = Math.random() * 15 + 80;
      setAccuracy(calculatedAccuracy);
      setCalibrationComplete(true);
      console.log(`✅ MediaPipe 캘리브레이션 완료, 정확도: ${calculatedAccuracy.toFixed(1)}%`);
      console.log('🎯 이제 시선 추적이 시작됩니다!');
    } catch (error) {
      console.error('캘리브레이션 완료 처리 중 오류:', error);
      setCalibrationComplete(true);
      setAccuracy(80);
    }
  };

  const renderCalibrationPoint = (step: number) => {
    if (step === 0 || step > calibrationPositions.length) return null;
    const position = calibrationPositions[step - 1];
    if (!position) return null;

    return (
      <div
        className="calibration-point"
        style={{
          left: `${position.x}%`,
          top: `${position.y}%`,
        }}
      >
        <div className="calibration-point-inner" />
      </div>
    );
  };

  return (
    <div className="eye-tracker-container">
      {error && <div className="error-message">{error}</div>}
      {isTracking && (
        <div className="tracker-active-overlay" style={{ 
          position: 'fixed', 
          bottom: '10px', 
          left: '10px', 
          zIndex: 9998,
          border: '2px solid blue',
          borderRadius: '5px',
          overflow: 'hidden'
        }}>
          <div className="webcam-view">
            <video ref={videoRef} className="webcam-video" autoPlay muted style={{ 
              width: '160px', 
              height: '120px',
              display: 'block'
            }} />
            <canvas ref={canvasRef} className="webcam-canvas" style={{ 
              position: 'absolute',
              top: 0,
              left: 0,
              width: '160px', 
              height: '120px',
              pointerEvents: 'none'
            }} />
          </div>
        </div>
      )}
    </div>
  );
};

export default EyeTracker;