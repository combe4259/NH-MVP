import React, { useRef, useEffect, useState } from 'react';
import './WebcamFaceDetection.css';

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

interface WebcamFaceDetectionProps {
  onFaceAnalysis: (data: FaceDetectionData) => void;
  isActive: boolean;
}

const WebcamFaceDetection: React.FC<WebcamFaceDetectionProps> = ({
  onFaceAnalysis,
  isActive
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isWebcamActive, setIsWebcamActive] = useState(false);
  const [error, setError] = useState<string>('');
  const [faceDetected, setFaceDetected] = useState(false);
  const [isMockMode, setIsMockMode] = useState(false);
  
  // CNN-LSTM을 위한 프레임 버퍼 (30프레임 시퀀스)
  const frameBufferRef = useRef<ImageData[]>([]);
  const frameBufferSize = 30; // CNN-LSTM sequence length
  const frameInterval = 200; // 200ms마다 프레임 캡처 (5fps, 6초간 수집)

  // 웹캠 시작
  const startWebcam = async () => {
    try {
      // 브라우저 지원 확인
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('브라우저가 웹캠을 지원하지 않습니다');
      }

      // 웹캠 접근에 타임아웃 추가 (15초로 연장)
      const mediaStreamPromise = navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640, min: 320 },
          height: { ideal: 480, min: 240 },
          facingMode: 'user'
        },
        audio: false
      });

      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('웹캠 접근 시간 초과')), 15000);
      });

      const mediaStream = await Promise.race([mediaStreamPromise, timeoutPromise]);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        setStream(mediaStream);
        setIsWebcamActive(true);
        setError('');
      }
    } catch (err: any) {
      console.error('웹캠 접근 실패:', err);
      let errorMessage = '';

      switch (err.name) {
        case 'NotAllowedError':
          errorMessage = '웹캠 접근이 거부되었습니다. 브라우저 주소창의 카메라 아이콘을 클릭하여 허용해주세요.';
          break;
        case 'NotFoundError':
          errorMessage = '웹캠을 찾을 수 없습니다. 카메라가 연결되어 있는지 확인해주세요.';
          break;
        case 'NotReadableError':
          errorMessage = '웹캠이 다른 앱에서 사용 중입니다. 다른 프로그램을 종료 후 다시 시도해주세요.';
          break;
        case 'OverconstrainedError':
          errorMessage = '웹캠 설정이 지원되지 않습니다. 카메라 드라이버를 확인해주세요.';
          break;
        default:
          if (err.message === '웹캠 접근 시간 초과') {
            errorMessage = '웹캠 연결이 지연되고 있습니다. 잠시 후 다시 시도해주세요.';
          } else if (err.message === '브라우저가 웹캠을 지원하지 않습니다') {
            errorMessage = '브라우저가 웹캠을 지원하지 않습니다. Chrome, Firefox, Edge를 사용해주세요.';
          } else {
            errorMessage = '웹캠 접근 중 오류가 발생했습니다.';
          }
      }

      setError(errorMessage);

      // 웹캠 실패 시 목업데이터로 폴백
      startMockDataFallback();
    }
  };

  // 목업데이터 폴백 시작 - 제거
  const startMockDataFallback = () => {
    setIsMockMode(true);
    setIsWebcamActive(false);
    setError('웹캠 연결 실패 - 프레임 수집 모드로 전환');
    
    // 목업 데이터 대신 프레임 버퍼 초기화만
    console.log('웹캠 실패 - 실제 얼굴 분석을 위한 프레임 버퍼 초기화');
  };

  // 웹캠 중지
  const stopWebcam = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      setStream(null);
      setIsWebcamActive(false);
      setFaceDetected(false);
    }
  };

  // 프레임 캡처 및 분석
  const captureAndAnalyze = async () => {
    if (!videoRef.current || !canvasRef.current || !isWebcamActive) return;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (!ctx) return;

    // 비디오가 준비되지 않았으면 대기
    if (video.readyState < 2) return;

    // 112x112로 리사이즈 (CNN-LSTM 입력 크기)
    canvas.width = 112;
    canvas.height = 112;
    ctx.drawImage(video, 0, 0, 112, 112);

    // 프레임 데이터 가져오기
    const imageData = ctx.getImageData(0, 0, 112, 112);
    
    // 프레임 버퍼에 추가
    frameBufferRef.current.push(imageData);
    
    // 버퍼 크기 유지 (최대 30프레임)
    if (frameBufferRef.current.length > frameBufferSize) {
      frameBufferRef.current.shift();
    }

    // 30프레임이 모이면 백엔드로 전송
    if (frameBufferRef.current.length === frameBufferSize) {
      await sendFramesToBackend();
    }

    // 간단한 얼굴 감지 (픽셀 체크)
    const hasDetection = await simulateFaceDetection(canvas);
    setFaceDetected(hasDetection);
  };

  // 프레임 시퀀스를 백엔드로 전송
  const sendFramesToBackend = async () => {
    try {
      // 프레임 데이터를 Base64로 변환
      const frames = frameBufferRef.current.map(imageData => {
        const canvas = document.createElement('canvas');
        canvas.width = 112;
        canvas.height = 112;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.putImageData(imageData, 0, 0);
          return canvas.toDataURL('image/jpeg', 0.7).split(',')[1]; // Base64만 추출
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
        
        // confusion 레벨만 사용 (0-3 -> 0-1 정규화)
        const confusionLevel = result.confusion || 0;
        const normalizedConfusion = confusionLevel / 3.0; // 0-3을 0-1로 정규화
        
        const faceData: FaceDetectionData = {
          hasDetection: true,
          confidence: result.confidence || 0.9,
          emotions: {
            engagement: 0, // 사용 안 함
            confusion: normalizedConfusion,
            frustration: 0, // 사용 안 함
            boredom: 0 // 사용 안 함
          }
        };
        
        onFaceAnalysis(faceData);
      }
    } catch (error) {
      console.error('프레임 분석 실패:', error);
    }
    
    // 버퍼 초기화 (다음 시퀀스를 위해)
    frameBufferRef.current = [];
  };

  // 간단한 얼굴 감지 시뮬레이션 (픽셀 분석)
  const simulateFaceDetection = async (canvas: HTMLCanvasElement): Promise<boolean> => {
    const ctx = canvas.getContext('2d');
    if (!ctx) return false;

    try {
      // 중앙 영역의 픽셀 데이터 분석
      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const sampleSize = 50;

      const imageData = ctx.getImageData(
        centerX - sampleSize/2,
        centerY - sampleSize/2,
        sampleSize,
        sampleSize
      );

      // 피부색 범위 체크 (매우 간단한 방법)
      let skinPixels = 0;
      const data = imageData.data;

      for (let i = 0; i < data.length; i += 4) {
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];

        // 간단한 피부색 감지
        if (r > 95 && g > 40 && b > 20 &&
            Math.max(r, g, b) - Math.min(r, g, b) > 15 &&
            Math.abs(r - g) > 15 && r > g && r > b) {
          skinPixels++;
        }
      }

      // 픽셀의 10% 이상이 피부색이면 얼굴로 간주
      return skinPixels > (sampleSize * sampleSize * 0.1);
    } catch (error) {
      console.error('얼굴 감지 시뮬레이션 실패:', error);
      return false;
    }
  };

  // 주기적 분석 실행
  useEffect(() => {
    if (!isActive || !isWebcamActive) return;

    const interval = setInterval(captureAndAnalyze, frameInterval); // 200ms마다 (5fps)

    return () => clearInterval(interval);
  }, [isActive, isWebcamActive, frameInterval]);

  // 컴포넌트 마운트/언마운트 시 웹캠 관리
  useEffect(() => {
    if (isActive) {
      startWebcam();
    } else {
      stopWebcam();
    }

    return () => {
      stopWebcam();
    };
  }, [isActive]);

  return (
    <div className="webcam-face-detection">
      {error && (
        <div className={`webcam-error ${isMockMode ? 'mock-mode' : ''}`}>
          <div className="error-icon"></div>
          <p>{error}</p>
          {!isMockMode && (
            <button onClick={startWebcam} className="retry-btn">
              다시 시도
            </button>
          )}
        </div>
      )}

      {isWebcamActive && (
        <div className="webcam-container">
          <div className="video-wrapper">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="webcam-video"
            />

            {/* 얼굴 감지 상태 표시 */}
            <div className={`detection-indicator ${faceDetected ? 'detected' : 'not-detected'}`}>
              <div className="indicator-dot"></div>
              <span>{faceDetected ? '얼굴 감지됨' : '얼굴을 찾는 중...'}</span>
            </div>
          </div>

          {/* 숨겨진 캔버스 (프레임 캡처용) */}
          <canvas
            ref={canvasRef}
            style={{ display: 'none' }}
          />
        </div>
      )}

      {!isActive && (
        <div className="webcam-inactive">
          <div className="inactive-icon"></div>
          <p>웹캠이 비활성화되었습니다</p>
        </div>
      )}
    </div>
  );
};

export default WebcamFaceDetection;