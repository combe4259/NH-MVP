import React, { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import PDFViewer from './components/PDFViewer';
import EyeTracker from './components/EyeTracker';
import { FACEMESH_TESSELATION } from '@mediapipe/face_mesh';
import axios from 'axios';

function App() {
  const [isTracking, setIsTracking] = useState(true);
  const [customerName] = useState('김민수');
  const [productType] = useState('ELS(주가연계증권)');
  
  const sharedVideoRef = useRef<HTMLVideoElement>(null);
  const webcamCanvasRef = useRef<HTMLCanvasElement>(null);
  const [faceLandmarks, setFaceLandmarks] = useState<any>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [currentGazePosition, setCurrentGazePosition] = useState<{x: number, y: number} | null>(null);
  const [currentSentence, setCurrentSentence] = useState<string>('');
  const [emotionState, setEmotionState] = useState<'정상' | '주의' | '혼란'>('정상');
  const [difficultyLevel, setDifficultyLevel] = useState<number>(0);
  const [showAssistantAlert, setShowAssistantAlert] = useState<boolean>(false);
  const [pdfTextRegions, setPdfTextRegions] = useState<any[]>([]);
  const [faceFrames, setFaceFrames] = useState<string[]>([]);
  const [aiExplanation, setAiExplanation] = useState<string>('');
  const [confusedSections, setConfusedSections] = useState<any[]>([]);

  // 시선 추적 이력 저장 (최근 30초)
  const [gazeHistory, setGazeHistory] = useState<Array<{x: number, y: number, timestamp: number, textRegion?: string}>>([]);
  const [lastReadingStartTime, setLastReadingStartTime] = useState<number>(Date.now());

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


  const handleFaceLandmarks = useCallback((landmarkData: any) => {
    setFaceLandmarks(landmarkData);
  }, []);

  const handleGazeData = useCallback((gazeData: any) => {
    const newPosition = { x: gazeData.x, y: gazeData.y };
    setCurrentGazePosition(newPosition);

    // 시선 이력에 추가 (최근 30초만 유지)
    setGazeHistory(prev => {
      const now = Date.now();
      const newHistory = [
        ...prev.filter(point => now - point.timestamp < 30000), // 30초 이상 된 데이터 제거
        { ...newPosition, timestamp: now }
      ];
      return newHistory;
    });
  }, []);

  const handleFaceAnalysis = useCallback((faceData: any) => {
    // 프레임 데이터 저장 (백엔드로 보낼 때 사용)
    if (faceData.frames && faceData.frames.length > 0) {
      setFaceFrames(faceData.frames);
      console.log('📹 얼굴 프레임 수신:', faceData.frames.length, '개');
    }

    // 이미 분석된 결과가 있으면 UI 업데이트
    if (faceData.emotions?.confusion > 0.6) {
      setEmotionState('혼란');
    } else if (faceData.emotions?.confusion > 0.35) {
      setEmotionState('주의');
    } else if (faceData.emotions?.confusion !== undefined) {
      setEmotionState('정상');
    }
  }, []);

  const handlePdfLoaded = useCallback((textRegions: any[]) => {
    setPdfTextRegions(textRegions);
    console.log('📄 PDF 텍스트 영역 로드됨:', textRegions.length);
  }, []);

  // 시선 데이터 분석 함수들
  const calculateGazeMetrics = useCallback((history: typeof gazeHistory) => {
    if (history.length < 5) {
      return {
        avg_fixation_duration: 250,
        regression_count: 0,
        gaze_dispersion: 50,
        skip_count: 0
      };
    }

    // 1. 고정 시간 계산 (fixation duration)
    const fixations: number[] = [];
    let currentFixationStart = history[0].timestamp;
    let lastPos = history[0];
    const FIXATION_THRESHOLD = 50; // 50px 이내면 같은 지점으로 간주

    for (let i = 1; i < history.length; i++) {
      const curr = history[i];
      const distance = Math.sqrt(
        Math.pow(curr.x - lastPos.x, 2) + Math.pow(curr.y - lastPos.y, 2)
      );

      if (distance > FIXATION_THRESHOLD) {
        // 고정 끝남
        const fixationDuration = lastPos.timestamp - currentFixationStart;
        if (fixationDuration > 100) { // 100ms 이상만 고정으로 인정
          fixations.push(fixationDuration);
        }
        currentFixationStart = curr.timestamp;
      }
      lastPos = curr;
    }

    const avg_fixation_duration = fixations.length > 0
      ? fixations.reduce((a, b) => a + b, 0) / fixations.length
      : 250;

    // 2. 회귀 감지 (regression count) - Y 좌표가 위로 올라가는 횟수
    let regression_count = 0;
    for (let i = 1; i < history.length; i++) {
      const prev = history[i - 1];
      const curr = history[i];
      // Y 좌표가 50px 이상 위로 이동하면 회귀로 간주
      if (prev.y - curr.y > 50) {
        regression_count++;
      }
    }

    // 3. 시선 분산도 (gaze dispersion) - 표준편차
    const meanX = history.reduce((sum, p) => sum + p.x, 0) / history.length;
    const meanY = history.reduce((sum, p) => sum + p.y, 0) / history.length;
    const variance = history.reduce((sum, p) => {
      return sum + Math.pow(p.x - meanX, 2) + Math.pow(p.y - meanY, 2);
    }, 0) / history.length;
    const gaze_dispersion = Math.sqrt(variance);

    // 4. 스킵 카운트 - 급격한 이동 (200px 이상)
    let skip_count = 0;
    for (let i = 1; i < history.length; i++) {
      const prev = history[i - 1];
      const curr = history[i];
      const distance = Math.sqrt(
        Math.pow(curr.x - prev.x, 2) + Math.pow(curr.y - prev.y, 2)
      );
      if (distance > 200) {
        skip_count++;
      }
    }

    return {
      avg_fixation_duration: Math.round(avg_fixation_duration),
      regression_count,
      gaze_dispersion: Math.round(gaze_dispersion),
      skip_count
    };
  }, []);

  // 시선 좌표로 현재 읽고 있는 문장 찾기
  useEffect(() => {
    if (!currentGazePosition || pdfTextRegions.length === 0) return;

    const { x, y } = currentGazePosition;

    // 시선 좌표와 가장 가까운 텍스트 영역 찾기
    let closestRegion: any = null;
    let minDistance = Infinity;

    pdfTextRegions.forEach(region => {
      const regionCenterX = region.x + region.width / 2;
      const regionCenterY = region.y + region.height / 2;

      const distance = Math.sqrt(
        Math.pow(x - regionCenterX, 2) + Math.pow(y - regionCenterY, 2)
      );

      if (distance < minDistance && distance < 100) {
        minDistance = distance;
        closestRegion = region;
      }
    });

    if (closestRegion && closestRegion.text !== currentSentence) {
      setCurrentSentence(closestRegion.text);
      setLastReadingStartTime(Date.now()); // 새 문장 읽기 시작
      console.log('👁️ 현재 읽고 있는 문장:', closestRegion.text);
    }
  }, [currentGazePosition, pdfTextRegions, currentSentence]);

  // 현재 문장이 바뀔 때마다 통합 분석 요청 (텍스트 + 얼굴 + 시선)
  useEffect(() => {
    if (!currentSentence || currentSentence.length < 5) {
      return;
    }

    const analyzeIntegrated = async () => {
      try {
        // 시선 메트릭 계산
        const gazeMetrics = calculateGazeMetrics(gazeHistory);
        const readingTime = (Date.now() - lastReadingStartTime) / 1000; // 초 단위

        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('📊 통합 분석 시작');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('📝 현재 읽고 있는 문장:', currentSentence);
        console.log('👁️ 시선 추적 데이터:', currentGazePosition ?
          `X: ${currentGazePosition.x.toFixed(0)}, Y: ${currentGazePosition.y.toFixed(0)}` :
          '없음'
        );
        console.log('📊 시선 메트릭:', {
          '고정 시간': `${gazeMetrics.avg_fixation_duration}ms`,
          '회귀 횟수': gazeMetrics.regression_count,
          '시선 분산도': gazeMetrics.gaze_dispersion,
          '스킵 횟수': gazeMetrics.skip_count,
          '읽기 시간': `${readingTime.toFixed(1)}초`,
          '시선 포인트': gazeHistory.length
        });
        console.log('📹 얼굴 프레임:', faceFrames.length > 0 ? `${faceFrames.length}개 수집됨` : '없음');

        // 통합 분석 요청: 텍스트 + 얼굴 프레임 + 시선 메트릭
        const response = await axios.post('http://localhost:8000/api/eyetracking/analyze', {
          consultation_id: 'demo-session',
          customer_id: 'demo-customer',
          current_section: 'current-reading',
          section_text: currentSentence,
          reading_time: readingTime,
          gaze_data: gazeHistory.length >= 5 ? gazeMetrics : undefined,
          face_analysis: faceFrames.length > 0 ? {
            frames: faceFrames,
            sequence_length: faceFrames.length
          } : undefined
        });

        const result = response.data;

        console.log('');
        console.log('🎯 AI 분석 결과');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('📖 [텍스트 난이도 분석 AI]');
        console.log(`   난이도 점수: ${(result.difficulty_score * 10).toFixed(1)}/10`);
        console.log(`   이해도 수준: ${result.comprehension_level}`);
        console.log('');
        console.log('😊 [표정 기반 이해도 분석 AI (CNN-LSTM)]');
        console.log(`   혼란도: ${(result.confusion_probability * 100).toFixed(1)}%`);
        const emotionStatus = result.confusion_probability > 0.6 ? '혼란 😰' :
                             result.confusion_probability > 0.35 ? '주의 😐' : '정상 😊';
        console.log(`   상태: ${emotionStatus}`);
        console.log('');
        console.log('👁️ [시선 추적 분석]');
        console.log(`   시선 위치: X=${currentGazePosition?.x.toFixed(0) || 'N/A'}, Y=${currentGazePosition?.y.toFixed(0) || 'N/A'}`);
        console.log(`   고정 시간: ${gazeMetrics.avg_fixation_duration}ms`);
        console.log(`   회귀 횟수: ${gazeMetrics.regression_count}회`);
        console.log(`   시선 분산도: ${gazeMetrics.gaze_dispersion}`);
        console.log(`   스킵 횟수: ${gazeMetrics.skip_count}회`);
        console.log(`   읽기 시간: ${readingTime.toFixed(1)}초`);
        console.log(`   읽고 있는 텍스트: "${currentSentence.substring(0, 30)}${currentSentence.length > 30 ? '...' : ''}"`);
        console.log('');
        console.log('🔥 [통합 분석 결과]');
        console.log(`   AI 도우미 필요: ${result.needs_ai_assistance ? 'YES ⚠️' : 'NO ✅'}`);
        console.log(`   최종 판정: ${result.needs_ai_assistance ? 'NH 문장 도우미 발동!' : '정상 진행'}`);
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

        // 난이도 점수 업데이트 (0~1 → 0~10)
        if (result.difficulty_score !== undefined) {
          setDifficultyLevel(Math.round(result.difficulty_score * 10));
        }

        // 얼굴 표정 분석 결과로 UI 업데이트
        if (result.confusion_probability !== undefined) {
          if (result.confusion_probability > 0.6) {
            setEmotionState('혼란');
          } else if (result.confusion_probability > 0.35) {
            setEmotionState('주의');
          } else {
            setEmotionState('정상');
          }
        }

        // AI 도우미 트리거
        if (result.needs_ai_assistance) {
          setShowAssistantAlert(true);

          // 백엔드 AI 설명 저장
          if (result.ai_explanation) {
            setAiExplanation(result.ai_explanation);
            console.log('💡 AI 간소화 설명:', result.ai_explanation);
          }

          // 혼란스러운 섹션 저장
          if (result.confused_sentences_detail) {
            setConfusedSections(result.confused_sentences_detail);
            console.log('📌 혼란스러운 섹션:', result.confused_sentences_detail);
          }
        } else {
          setShowAssistantAlert(false);
          setAiExplanation('');
          setConfusedSections([]);
        }

      } catch (error) {
        console.error('❌ 통합 분석 요청 실패:', error);
      }
    };

    // 디바운싱: 문장이 바뀌고 1초 후에 분석 요청
    const timer = setTimeout(analyzeIntegrated, 1000);
    return () => clearTimeout(timer);
  }, [currentSentence]); // currentSentence만 의존성으로 (무한루프 방지)

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
        onFaceAnalysis={handleFaceAnalysis}
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
            <PDFViewer
              fileUrl="/NM0044.pdf"
              onPdfLoaded={handlePdfLoaded}
              triggerHighlight={showAssistantAlert}
              aiExplanation={aiExplanation}
              confusedSections={confusedSections}
              currentSentence={currentSentence}
            />
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
                        className={`status-dot ${
                          emotionState === '혼란' ? 'alert' :
                          emotionState === '주의' ? 'warning' :
                          'normal'
                        }`}
                        style={{
                          animation: emotionState === '혼란' ? 'pulse 1s infinite' : 'none',
                          backgroundColor:
                            emotionState === '혼란' ? '#ff4444' :
                            emotionState === '주의' ? '#ff9800' :
                            '#00A651'
                        }}
                      ></span>
                      <span style={{
                        color:
                          emotionState === '혼란' ? '#ff4444' :
                          emotionState === '주의' ? '#ff9800' :
                          '#00A651',
                        fontWeight: emotionState !== '정상' ? '600' : '500'
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
