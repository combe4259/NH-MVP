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

  // 목업데이터 폴백 시작
  const startMockDataFallback = () => {
    setIsMockMode(true);
    setIsWebcamActive(false);
    setError('웹캠 연결 실패 - 목업데이터로 진행합니다');

    // 주기적으로 목업 얼굴 분석 데이터 전송
    const mockInterval = setInterval(() => {
      const mockFaceData: FaceDetectionData = {
        hasDetection: true,
        confidence: 0.9,
        emotions: {
          engagement: 0.75,
          confusion: 0.2,
          frustration: 0.1,
          boredom: 0.15
        }
      };
      onFaceAnalysis(mockFaceData);
      setFaceDetected(true);
    }, 3000);

    // 컴포넌트 언마운트 시 정리를 위해 interval ID 저장
    return () => clearInterval(mockInterval);
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

    // 캔버스에 현재 프레임 그리기
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    // 간단한 얼굴 감지 시뮬레이션 (실제로는 AI 모델 사용)
    const hasDetection = await simulateFaceDetection(canvas);

    setFaceDetected(hasDetection);

    if (hasDetection) {
      // Mock 감정 분석 데이터 생성
      const mockEmotions = {
        engagement: Math.random() * 0.4 + 0.6, // 0.6-1.0
        confusion: Math.random() * 0.3 + 0.1,   // 0.1-0.4
        frustration: Math.random() * 0.2,       // 0.0-0.2
        boredom: Math.random() * 0.3            // 0.0-0.3
      };

      const faceData: FaceDetectionData = {
        hasDetection: true,
        confidence: 0.85 + Math.random() * 0.15, // 0.85-1.0
        emotions: mockEmotions
      };

      onFaceAnalysis(faceData);
    } else {
      onFaceAnalysis({
        hasDetection: false,
        confidence: 0
      });
    }
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

    const interval = setInterval(captureAndAnalyze, 2000); // 2초마다

    return () => clearInterval(interval);
  }, [isActive, isWebcamActive]);

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