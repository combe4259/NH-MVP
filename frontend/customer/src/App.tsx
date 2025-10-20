import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import AIAssistant from './components/AIAssistant';
import PDFViewer from './components/PDFViewer';
import EyeTracker from './components/EyeTracker';
import { FACEMESH_TESSELATION } from '@mediapipe/face_mesh';

const SENTENCE_A = '(8) 위 (6)의 경우에 해당하지 않고, 투자기간 중 종가 기준으로 최초기준가격의 50% 미만으로 하락한 기초자산이 있는 경우';
const SENTENCE_B = '=> 원금손실(손실률 = 만기평가가격이 최초기준가격 대비 가장 낮은 기초자산의 하락률)';

function App() {
  const [isTracking, setIsTracking] = useState(true);
  const [customerName] = useState('김민수');
  const [productType] = useState('ELS(주가연계증권)');
  
  const sharedVideoRef = useRef<HTMLVideoElement>(null);
  const webcamCanvasRef = useRef<HTMLCanvasElement>(null);
  const [faceLandmarks, setFaceLandmarks] = useState<any>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [currentGazePosition, setCurrentGazePosition] = useState<{x: number, y: number} | null>(null);
  const [currentSentence, setCurrentSentence] = useState<string>(SENTENCE_A); // 초기 상태를 SENTENCE_A로 설정
  const [emotionState, setEmotionState] = useState<'분석 중' | '혼란'>('분석 중');
  const [difficultyLevel, setDifficultyLevel] = useState<number>(7);
  const [showAssistantAlert, setShowAssistantAlert] = useState<boolean>(false);

  // 카메라 초기화
  useEffect(() => {
    const initCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        setCameraStream(stream);
        if (sharedVideoRef.current) {
          sharedVideoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error("카메라 접근 실패:", err);
      }
    };
    if (isTracking && !cameraStream) {
      initCamera();
    }
    return () => {
      cameraStream?.getTracks().forEach(track => track.stop());
    };
  }, [isTracking, cameraStream]);

  // 텍스트 분석 시연용 키보드 이벤트
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Shift + 9: PDF 형광펜 토글
      if (e.shiftKey && e.key === '(') {
        e.preventDefault();
      }
      // Shift + 0: 텍스트 변경 + 표정 분석 "혼란" + 난이도 10 + 도우미 알림
      if (e.shiftKey && e.key === ')') {
        e.preventDefault();
        setCurrentSentence(SENTENCE_B);
        setEmotionState('혼란');
        setDifficultyLevel(10);
        setShowAssistantAlert(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleFaceLandmarks = useCallback((landmarkData: any) => {
    setFaceLandmarks(landmarkData);
  }, []);

  const handleGazeData = useCallback((gazeData: any) => {
    setCurrentGazePosition({ x: gazeData.x, y: gazeData.y });
  }, []);

  // 얼굴 윤곽선 그리기
  useEffect(() => {
    if (!faceLandmarks || !webcamCanvasRef.current || !sharedVideoRef.current) return;
    const canvas = webcamCanvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const video = sharedVideoRef.current;
    canvas.width = video.clientWidth;
    canvas.height = video.clientHeight;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const { landmarks, videoWidth, videoHeight } = faceLandmarks;
    const scaleX = canvas.width / videoWidth;
    const scaleY = canvas.height / videoHeight;
    ctx.strokeStyle = 'rgba(0, 166, 81, 0.7)';
    ctx.lineWidth = 0.5;
    if (landmarks) {
        for (const connection of FACEMESH_TESSELATION) {
            const start = landmarks[connection[0]];
            const end = landmarks[connection[1]];
            if (start && end) {
                ctx.beginPath();
                ctx.moveTo((1 - start.x) * videoWidth * scaleX, start.y * videoHeight * scaleY);
                ctx.lineTo((1 - end.x) * videoWidth * scaleX, end.y * videoHeight * scaleY);
                ctx.stroke();
            }
        }
    }
  }, [faceLandmarks]);

  return (
    <div className="app-container">
      <EyeTracker 
        isTracking={isTracking} 
        onGazeData={handleGazeData} 
        onFaceAnalysis={() => {}} 
        onFaceLandmarks={handleFaceLandmarks}
      />
      <header className="app-header">
        <div className="header-left">
          <div className="logo"><span className="logo-nh">NH</span></div>
          <div className="customer-info">
            <span className="customer-name">{customerName} 고객님</span>
            <span className="product-badge">{productType} 상담</span>
          </div>
        </div>
        <div className="header-right">
          <div className="time">{new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      </header>
      <main className="app-main">
        <div className="main-grid simplified">
          <aside className="sidebar-left">
            <div className="progress-card">
              <h3 className="card-title">상담 진행도</h3>
              <div className="progress-steps">
                <div className="step completed"><span className="step-number">1</span><span className="step-label">상품소개</span></div>
                <div className="step active"><span className="step-number">2</span><span className="step-label">약관확인</span></div>
                <div className="step"><span className="step-number">3</span><span className="step-label">가입신청</span></div>
              </div>
            </div>
          </aside>
          <div className="main-content">
            <PDFViewer fileUrl="/NM0044.pdf" onPdfLoaded={() => {}} />
          </div>
          <aside className="sidebar-right">
            <div className="ai-monitor-card">
              <h3 className="card-title">AI 실시간 분석 현황</h3>
              <div className="monitor-list">
                <div className="monitor-item-video">
                  <div className="monitor-item-header">
                    <span className="monitor-name">표정 기반 이해도 분석 AI</span>
                    <div className="monitor-status">
                      <span
                        className={`status-dot ${emotionState === '혼란' ? 'alert' : 'analyzing'}`}
                        style={{
                          animation: emotionState === '혼란' ? 'pulse 1s infinite' : 'none'
                        }}
                      ></span>
                      <span style={{
                        color: emotionState === '혼란' ? '#ff4444' : '#666',
                        fontWeight: emotionState === '혼란' ? '600' : '400'
                      }}>
                        {emotionState}
                      </span>
                    </div>
                  </div>
                  <div className="webcam-view-container">
                    <video ref={sharedVideoRef} autoPlay muted playsInline className="webcam-video-feed" />
                    <canvas ref={webcamCanvasRef} className="webcam-overlay-canvas" />
                  </div>
                </div>
                <div className="monitor-item">
                  <span className="monitor-name">시선 추적</span>
                  <div className="monitor-status">
                    {currentGazePosition ? (
                      <span className="gaze-coords">X: {currentGazePosition.x.toFixed(0)}, Y: {currentGazePosition.y.toFixed(0)}</span>
                    ) : (
                      <><span className="status-dot analyzing"></span><span>추적 중...</span></>
                    )}
                  </div>
                </div>
                <div className="monitor-item-text">
                  <div className="monitor-item-header">
                     <span className="monitor-name">읽고 있는 텍스트의 난이도 분석</span>
                     <div className="monitor-status">
                       <span style={{
                         color: difficultyLevel >= 8 ? '#ff4444' : difficultyLevel >= 6 ? '#ff9800' : '#00A651',
                         fontWeight: '700',
                         fontSize: '16px'
                       }}>
                         난이도 {difficultyLevel}
                       </span>
                     </div>
                  </div>
                  <div className="current-sentence-container">
                    <p className="current-sentence-text">{currentSentence}</p>
                  </div>
                  {showAssistantAlert && (
                    <div style={{
                      marginTop: '12px',
                      padding: '12px 16px',
                      background: 'linear-gradient(135deg, #00A651 0%, #4CAF50 100%)',
                      borderRadius: '8px',
                      border: '2px solid #00A651',
                      boxShadow: '0 4px 12px rgba(0, 166, 81, 0.3)',
                      animation: 'slideIn 0.3s ease-out'
                    }}>
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginBottom: '6px'
                      }}>
                        <span style={{
                          fontSize: '18px'
                        }}>⚠️</span>
                        <span style={{
                          color: 'white',
                          fontWeight: '700',
                          fontSize: '14px'
                        }}>
                          이해도 하락 구간 감지
                        </span>
                      </div>
                      <div style={{
                        color: 'white',
                        fontSize: '13px',
                        lineHeight: '1.5',
                        paddingLeft: '26px'
                      }}>
                        NH 문장 도우미가 문장을 쉽게 변환했습니다.
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </aside>
        </div>
      </main>
      <footer className="app-footer">
        <div className="footer-left"><span className="footer-text">NH투자증권 디지털 상담 시스템</span></div>
        <div className="footer-actions">
          <button className="action-btn secondary">이전</button>
          <button className="action-btn primary">다음 단계</button>
        </div>
      </footer>
      {currentGazePosition && isTracking && (
        <div
          style={{
            position: 'fixed',
            left: currentGazePosition.x - 10,
            top: currentGazePosition.y - 10,
            width: '20px',
            height: '20px',
            borderRadius: '50%',
            border: '2px solid rgba(0, 123, 255, 0.4)',
            backgroundColor: 'rgba(0, 123, 255, 0.07)',
            pointerEvents: 'none',
            zIndex: 9999,
            transition: 'all 0.1s ease-out'
          }}
        />
      )}
    </div>
  );
}

export default App;
