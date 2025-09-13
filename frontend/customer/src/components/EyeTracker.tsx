import React, { useEffect, useRef, useState } from 'react';
import './EyeTracker.css';

interface EyeTrackerProps {
  isTracking: boolean;
  onGazeData?: (data: GazeData) => void;
}

interface GazeData {
  x: number;
  y: number;
  timestamp: number;
  confidence: number;
}

const EyeTracker: React.FC<EyeTrackerProps> = ({ isTracking, onGazeData }) => {
  const [gazePosition, setGazePosition] = useState<{ x: number; y: number } | null>(null);
  const [calibrationComplete, setCalibrationComplete] = useState(false);
  const [calibrationPoints, setCalibrationPoints] = useState<number>(0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (isTracking && !calibrationComplete) {
      // 캘리브레이션 시뮬레이션
      startCalibration();
    }
  }, [isTracking, calibrationComplete]);

  const startCalibration = () => {
    const totalPoints = 9;
    let currentPoint = 0;
    
    const interval = setInterval(() => {
      currentPoint++;
      setCalibrationPoints(currentPoint);
      
      if (currentPoint >= totalPoints) {
        clearInterval(interval);
        setCalibrationComplete(true);
        console.log('캘리브레이션 완료');
      }
    }, 1000);
  };

  useEffect(() => {
    if (isTracking && calibrationComplete) {
      // 시선 추적 시뮬레이션
      const interval = setInterval(() => {
        const mockGaze = {
          x: Math.random() * window.innerWidth,
          y: Math.random() * window.innerHeight,
          timestamp: Date.now(),
          confidence: 0.85 + Math.random() * 0.15
        };
        
        setGazePosition({ x: mockGaze.x, y: mockGaze.y });
        
        if (onGazeData) {
          onGazeData(mockGaze);
        }
      }, 100);

      return () => clearInterval(interval);
    }
  }, [isTracking, calibrationComplete, onGazeData]);

  return (
    <div className="eye-tracker-container">
      {/* 웹캠 뷰 */}
      <div className="webcam-view">
        <video ref={videoRef} className="webcam-video" autoPlay muted />
        <canvas ref={canvasRef} className="eye-overlay" />
        
        {!calibrationComplete && isTracking && (
          <div className="calibration-overlay">
            <div className="calibration-content">
              <h3>시선 캘리브레이션 중...</h3>
              <div className="calibration-progress">
                <div className="progress-bar">
                  <div 
                    className="progress-fill" 
                    style={{ width: `${(calibrationPoints / 9) * 100}%` }}
                  />
                </div>
                <span className="progress-text">{calibrationPoints} / 9</span>
              </div>
              <p>화면의 점을 순서대로 바라봐 주세요</p>
            </div>
          </div>
        )}
      </div>

      {/* 시선 추적 상태 */}
      <div className="tracking-info">
        <div className="info-item">
          <span className="info-label">상태</span>
          <span className={`info-value ${isTracking ? 'active' : ''}`}>
            {isTracking ? (calibrationComplete ? '추적 중' : '캘리브레이션 중') : '대기'}
          </span>
        </div>
        
        {calibrationComplete && gazePosition && (
          <>
            <div className="info-item">
              <span className="info-label">시선 위치</span>
              <span className="info-value">
                X: {Math.round(gazePosition.x)}, Y: {Math.round(gazePosition.y)}
              </span>
            </div>
            <div className="info-item">
              <span className="info-label">정확도</span>
              <span className="info-value">85.0%</span>
            </div>
          </>
        )}
      </div>

      {/* 시선 히트맵 미리보기 */}
      <div className="heatmap-preview">
        <h4>시선 히트맵</h4>
        <div className="heatmap-canvas">
          {calibrationComplete && isTracking ? (
            <div className="heatmap-active">
              <div className="heat-point" style={{
                left: `${(gazePosition?.x || 0) / window.innerWidth * 100}%`,
                top: `${(gazePosition?.y || 0) / window.innerHeight * 100}%`
              }} />
            </div>
          ) : (
            <div className="heatmap-placeholder">
              <span>추적 시작 시 표시됩니다</span>
            </div>
          )}
        </div>
      </div>

      {/* 시선 추적 가이드 */}
      {!isTracking && (
        <div className="tracker-guide">
          <h4>시선 추적 준비사항</h4>
          <ul>
            <li>카메라가 얼굴을 정면으로 볼 수 있도록 위치를 조정하세요</li>
            <li>안경을 착용하신 경우 반사가 없도록 조명을 조절하세요</li>
            <li>캘리브레이션 중에는 머리를 고정하고 눈만 움직여주세요</li>
          </ul>
        </div>
      )}
    </div>
  );
};

export default EyeTracker;