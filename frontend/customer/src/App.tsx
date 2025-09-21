import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import './App.css';
import AIAssistant from './components/AIAssistant';
import PDFViewer from './components/PDFViewer';
import EyeTracker from './components/EyeTracker';

const API_BASE_URL = 'http://localhost:8000/api';

interface ConfusedSection {
  id: string;
  title: string;
  content: string;
  timestamp: Date;
}

interface HighlightedText {
  text: string;
  explanation: string;
}

interface DifficultSentence {
  sentence: string;
  sentence_id: string;
  difficulty_score: number;
  simplified_explanation: string;
  original_position: number;
  location?: {
    page_number: number;
    page_width: number;
    page_height: number;
    x: number;
    y: number;
    width: number;
    height: number;
  };
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

function App() {
  const [isTracking, setIsTracking] = useState(true);
  const [currentSection, setCurrentSection] = useState('중도해지 시 불이익');
  const [customerName] = useState('김민수');
  const [productType] = useState('정기예금');
  const [showAIHelper, setShowAIHelper] = useState(true);  // 기본으로 표시
  const [confusedSections, setConfusedSections] = useState<ConfusedSection[]>([
    {
      id: 'section_hardcoded',
      title: '압류 제한 조항',
      content: '계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한',
      timestamp: new Date()
    }
  ]);
  
  const consultationId = '29853704-6f54-4df2-bb40-6efa9a63cf53';
  const [aiSuggestion, setAiSuggestion] = useState<{
    section: string;
    explanation: string;
    simpleExample?: string;
  } | null>({
    section: '압류 제한 조항',
    explanation: '계좌에 법적 조치가 취해지면 예금을 찾을 수 없게 됩니다.',
    simpleExample: '예를 들어, 빚을 갚지 못해 법원이 계좌를 막으면, 통장에 돈이 있어도 찾을 수 없어요. 마치 자물쇠가 걸린 것처럼요.'
  });
  const [highlightedTexts, setHighlightedTexts] = useState<HighlightedText[]>([
    { text: '계좌에 압류', explanation: '법원이 계좌를 막는 것' },
    { text: '가압류', explanation: '재판 전에 임시로 재산을 못 쓰게 막는 것' },
    { text: '질권설정 등이', explanation: '빚의 담보로 예금을 잡히는 것' },
    { text: '등록될 경우', explanation: '이러한 조치가 적용되면' },
    { text: '원금 및 이자', explanation: '처음 넣은 돈과 이자' },
    { text: '지급 제한', explanation: '돈을 찾을 수 없게 되는 것' }
  ]);
  const [difficultSentences, setDifficultSentences] = useState<DifficultSentence[]>([
    {
      sentence: '계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한',  // 전체 문장
      sentence_id: 'sentence_full',
      difficulty_score: 0.8,
      simplified_explanation: '법원이나 채권자가 계좌를 막으면 돈을 찾을 수 없게 됩니다. 압류는 법원이 재산을 못 쓰게 막는 것, 가압류는 임시로 막는 것, 질권설정은 담보로 잡히는 것입니다.',
      original_position: 0
    }
  ]);
  const [mainTerms, setMainTerms] = useState<{term: string, definition: string}[]>([]);
  const [gazeDataBuffer, setGazeDataBuffer] = useState<any[]>([]);
  const gazeDataBufferRef = useRef<any[]>([]);
  const [faceAnalysisBuffer, setFaceAnalysisBuffer] = useState<any[]>([]);
  const pdfViewerRef = useRef<HTMLDivElement>(null);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [pdfTextRegions, setPdfTextRegions] = useState<any[]>([]);
  
  // 시선 추적 시각화용 상태
  const [currentGazePosition, setCurrentGazePosition] = useState<{x: number, y: number} | null>(null);
  const [showDebugInfo, setShowDebugInfo] = useState(true); // 디버그 정보 표시 여부
  
  // 공유 비디오 ref (두 컴포넌트가 같은 비디오 스트림 사용)
  const sharedVideoRef = useRef<HTMLVideoElement>(null);
  
  // 카메라 스트림 초기화 (한 번만)
  useEffect(() => {
    const initCamera = async () => {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          console.error('❌ 브라우저가 웹캠을 지원하지 않음');
          return;
        }
        
        console.log('🎥 공유 카메라 스트림 초기화 시작...');
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user'
          },
          audio: false
        });
        
        // 공유 비디오 요소에 스트림 연결
        if (sharedVideoRef.current) {
          sharedVideoRef.current.srcObject = stream;
          await sharedVideoRef.current.play();
        }
        
        setCameraStream(stream);
        console.log('✅ 공유 카메라 스트림 초기화 성공!');
      } catch (err) {
        console.error('❌ 카메라 초기화 실패:', err);
      }
    };
    
    if (!cameraStream && isTracking) {
      initCamera();
    }
    
    return () => {
      if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [isTracking]);


  const analyzeTextContent = useCallback(async (sectionName: string, sectionText: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/text/analyze-text`, {
        section_text: sectionText,
        consultation_id: '29853704-6f54-4df2-bb40-6efa9a63cf53',
        current_section: sectionName
      });

      const analysisData = response.data;

      if (analysisData.difficult_sentences && analysisData.difficult_sentences.length > 0) {
        const difficultSentencesFromAI: DifficultSentence[] = analysisData.difficult_sentences.map((sent: any, idx: number) => ({
          sentence: sent.sentence || sent.text,
          sentence_id: sent.id || `sentence_${idx}`,
          difficulty_score: sent.difficulty_score || 0.7,
          simplified_explanation: sent.simplified_explanation || sent.explanation || '이 부분이 어려울 수 있습니다. 천천히 읽어보세요.',
          original_position: sent.position || idx
        }));
        
        setDifficultSentences(difficultSentencesFromAI);
        console.log('AI 분석 어려운 문장:', difficultSentencesFromAI);
      } else {
        setDifficultSentences([]);
        console.log('AI 분석 결과 없음');
      }

      setMainTerms([
        { term: '압류', definition: '법원의 재산 동결 조치' },
        { term: '가압류', definition: '임시 재산 동결' },
        { term: '질권설정', definition: '담보 목적 예금 잠금' }
      ]);

      console.log('텍스트 분석 완료:', analysisData);

    } catch (error) {
      console.error('텍스트 분석 실패:', error);
    }
  }, []);

  const sendAnalysisData = useCallback(async (sectionName: string, sectionText: string, readingTime: number) => {
    try {
      const latestFaceData = faceAnalysisBuffer.length > 0 
        ? faceAnalysisBuffer[faceAnalysisBuffer.length - 1]
        : null;
      
      const currentGazeData = gazeDataBufferRef.current;

      const response = await axios.post(`${API_BASE_URL}/eyetracking/analyze`, {
        consultation_id: '29853704-6f54-4df2-bb40-6efa9a63cf53',
        customer_id: '069efa8e-8d80-4700-9355-ec57caca3fe0',  // TODO: 실제 고객 ID 사용
        current_section: sectionName,
        section_text: sectionText,
        reading_time: readingTime,
        face_analysis: latestFaceData,
        pdf_text_regions: pdfTextRegions,
        gaze_data: currentGazeData.length > 0 ? {
          raw_points: currentGazeData.slice(-20).map(point => ({
            x: point.screen_x || point.x || 0,
            y: point.screen_y || point.y || 0,
            timestamp: point.timestamp || Date.now(),
            confidence: point.confidence || 0.8
          })),
          total_duration: currentGazeData.reduce((sum, point) => sum + (point.duration || 200), 0),
          fixation_count: currentGazeData.length,
          saccade_count: Math.max(1, Math.floor(currentGazeData.length / 3)),
          regression_count: Math.floor(currentGazeData.length * 0.1)
        } : undefined
      });

      const analysis = response.data;

      // 백엔드가 이미 판단한 결과 사용
      console.log('🎯 AI 분석 결과:', {
        confusion: analysis.confusion_probability,
        needsAI: analysis.needs_ai_assistance,
        aiExplanation: analysis.ai_explanation
      });
      
      // 백엔드가 AI 도우미가 필요하다고 판단했거나 AI 설명이 있으면
      if (analysis.needs_ai_assistance || analysis.ai_explanation) {
        const confusedSection = {
          id: 'section_' + Date.now(),
          title: sectionName,
          content: sectionText,
          timestamp: new Date()
        };

        setConfusedSections([confusedSection]);
        setAiSuggestion({
          section: sectionName,
          explanation: analysis.ai_explanation || '이 부분이 복잡할 수 있습니다. 더 자세한 설명이 필요하시면 상담원에게 문의해주세요.',
          simpleExample: analysis.simple_explanation
        });
        
        // confused_sentences_detail 처리 (백엔드에서 온 어려운 문장 상세 정보)
        if (analysis.confused_sentences_detail && analysis.confused_sentences_detail.length > 0) {
          const difficultSentencesFromBackend: DifficultSentence[] = analysis.confused_sentences_detail.map((sent: any, idx: number) => ({
            sentence: sent.sentence,
            sentence_id: sent.sentence_id,
            difficulty_score: sent.difficulty_score,
            simplified_explanation: sent.simplified_explanation,
            original_position: idx
          }));
          
          setDifficultSentences(difficultSentencesFromBackend);
          console.log('🔴 어려운 문장 하이라이트:', difficultSentencesFromBackend);
        } else if (analysis.confused_sentences && analysis.confused_sentences.length > 0) {
          // confused_sentences_detail이 없으면 기본 처리
          console.log('⚠️ confused_sentences_detail 없음, 인덱스만 사용:', analysis.confused_sentences);
        }

        // difficult_terms 처리 (어려운 용어들)
        if (analysis.difficult_terms && analysis.detailed_explanations) {
          const newHighlights: HighlightedText[] = analysis.difficult_terms.map((term: string) => ({
            text: term,
            explanation: analysis.detailed_explanations[term] || '이 용어에 대한 설명이 필요합니다.'
          }));

          setHighlightedTexts(prev => {
            const prevTexts = prev.map(h => h.text).join(',');
            const newTexts = newHighlights.map(h => h.text).join(',');
            return prevTexts !== newTexts ? newHighlights : prev;
          });
          console.log('🟡 어려운 용어 하이라이트:', newHighlights);
        }
        setShowAIHelper(true);
      }
    } catch (error) {
      console.error('분석 데이터 전송 실패:', error);
    }
  }, [faceAnalysisBuffer, pdfTextRegions]);

  useEffect(() => {
    console.log('컴포넌트 마운트됨 - 시선 추적 시작');
    setIsTracking(true);
    return () => {
      console.log('컴포넌트 언마운트됨 - 시선 추적 중지');
      setIsTracking(false);
    };
  }, []);

  const checkAIStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/eyetracking/ai-status/29853704-6f54-4df2-bb40-6efa9a63cf53`);
      const aiStatus = response.data;

      if (aiStatus.should_trigger_ai_assistant && !showAIHelper) {
        setAiSuggestion({
          section: aiStatus.current_section || '분석 결과',
          explanation: aiStatus.ai_explanation || '추가 도움이 필요할 것 같습니다.',
          simpleExample: aiStatus.recommendation || '천천히 읽어보시거나 직원에게 문의하세요.'
        });
        setShowAIHelper(true);

        if (aiStatus.confused_sections && aiStatus.confused_sections.length > 0) {
          setConfusedSections(aiStatus.confused_sections);
        }
      }
    } catch (error) {
      console.error('AI 상태 확인 실패:', error);
    }
  }, [showAIHelper]);

  useEffect(() => {
    if (!isTracking) return;

    const timer = setInterval(() => {
      if (gazeDataBufferRef.current.length > 0 && pdfTextRegions.length > 0) {
        // PDF에서 샘플 텍스트 추출 (시선 위치 기반으로 개선 필요)
        const sampleText = pdfTextRegions.length > 0 
          ? pdfTextRegions.slice(0, 3).map(r => r.text).join(' ').substring(0, 100)
          : "계약기간 동안 약정이율로 계산하여 만기에 일시지급";
        
        // 5초마다 분석 요청 전송
        sendAnalysisData(
          'PDF 문서',
          sampleText,  // 실제 PDF 텍스트 전송
          5000
        );
      }
    }, 5000);

    return () => clearInterval(timer);
  }, [isTracking, pdfTextRegions.length, sendAnalysisData]);

  const handleAIHelperDismiss = useCallback(() => {
    setShowAIHelper(false);
    setAiSuggestion(null);
  }, []);

  const handleRequestMoreInfo = (topic: string) => {
    console.log('추가 설명 요청:', topic);
  };

  const setSpecificMockData = () => {
    const mockDifficultSentences: DifficultSentence[] = [
      {
        sentence: '계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한',
        sentence_id: 'sentence_001',
        difficulty_score: 0.8,
        simplified_explanation: '법원에서 계좌를 막거나, 다른 사람이 그 돈에 대한 권리를 주장하면, 예금을 찾을 수 없게 됩니다.',
        original_position: 1,
        location: {
          page_number: 1,
          page_width: 595,
          page_height: 842,
          x: 100,
          y: 700,
          width: 400,
          height: 25
        }
      }
    ];

    setDifficultSentences(mockDifficultSentences);

    const mockHighlights = [
      { text: '압류', explanation: '법원이 돈이나 재산을 못 쓰게 막는 것' },
      { text: '가압류', explanation: '임시로 재산을 못 쓰게 막는 것' },
      { text: '질권설정', explanation: '빚 담보로 예금을 잡히는 것' }
    ];

    setHighlightedTexts(mockHighlights);
    setMainTerms([
      { term: '압류', definition: '법원의 재산 동결 조치' },
      { term: '가압류', definition: '임시 재산 동결' },
      { term: '질권설정', definition: '담보 목적 예금 잠금' }
    ]);

    setAiSuggestion({
      section: '압류 관련 제한 사항',
      explanation: '계좌에 법적 조치가 취해지면 예금을 찾을 수 없게 됩니다.',
      simpleExample: '법원에서 계좌를 막거나, 빚 담보로 예금이 잡히면 돈을 찾을 수 없습니다.'
    });
    setShowAIHelper(true);
  };

  const setFallbackData = (sectionName: string) => {
    const mockConfusedSection = {
      id: 'section3',
      title: '중도해지 시 불이익',
      content: '만기 전 중도해지 시 약정한 우대이율은 적용되지 않습니다',
      timestamp: new Date()
    };

    setConfusedSections([mockConfusedSection]);

    const mockHighlights = [
      { text: '중도해지', explanation: '정기예금 만기일 전에 예금을 찾는 것을 의미합니다.' },
      { text: '우대이율', explanation: '은행에서 특정 조건을 충족할 때 제공하는 추가 이자율입니다.' }
    ];

    setHighlightedTexts(mockHighlights);
    setMainTerms([
      { term: '중도해지', definition: '만기 전 예금 인출' },
      { term: '우대이율', definition: '조건 충족시 추가 이자' }
    ]);
  };

  const handleSentenceClick = useCallback((sentence: DifficultSentence) => {
    console.log('선택된 문장:', sentence.sentence);
    setAiSuggestion({
      section: sentence.sentence.substring(0, 20) + '...',
      explanation: sentence.simplified_explanation,
      simpleExample: '구체적인 예시나 추가 설명이 필요하시면 직원에게 문의해 주세요.'
    });
    setShowAIHelper(true);
  }, []);

  const sendRawEmotionData = useCallback(async (emotions: any) => {
    try {
      await axios.post(`${API_BASE_URL}/eyetracking/submit-emotion-data`, {
        consultation_id: '29853704-6f54-4df2-bb40-6efa9a63cf53',
        customer_id: '069efa8e-8d80-4700-9355-ec57caca3fe0',  // 올바른 UUID 형식
        raw_emotion_scores: {
          confusion: emotions.confusion,
          engagement: emotions.engagement,
          frustration: emotions.frustration,
          boredom: emotions.boredom
        },
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('얼굴 감정 데이터 전송 실패:', error);
    }
  }, []);

  const handleFaceAnalysis = (data: FaceDetectionData) => {
    if (data.hasDetection && data.emotions) {
      const emotions = data.emotions;
      setFaceAnalysisBuffer(prev => [...prev, {
        confusion_probability: emotions.confusion,
        emotions: emotions,
        timestamp: Date.now()
      }].slice(-50));
      
      // sendRawEmotionData(emotions);  // 테이블이 없으므로 주석 처리
    }
  };

  const handleGazeData = useCallback((gazeData: any) => {
    const newData = {
      screen_x: gazeData.x,
      screen_y: gazeData.y,
      timestamp: gazeData.timestamp || Date.now(),
      confidence: gazeData.confidence || 0.8,
      duration: 200
    };
    setGazeDataBuffer(prev => [...prev, newData].slice(-100));
    gazeDataBufferRef.current = [...gazeDataBufferRef.current, newData].slice(-100);
    
    // 시선 위치 업데이트
    setCurrentGazePosition({ x: gazeData.x, y: gazeData.y });
    
    // PDF 영역 내에 있는지 확인
    if (pdfViewerRef.current) {
      const pdfRect = pdfViewerRef.current.getBoundingClientRect();
      const isInPDF = gazeData.x >= pdfRect.left && 
                      gazeData.x <= pdfRect.right && 
                      gazeData.y >= pdfRect.top && 
                      gazeData.y <= pdfRect.bottom;
      
      // PDF 내 시선 위치 로그 제거 (너무 자주 출력)
    }

    // 시선 추적 상태 로그 제거 (너무 자주 출력)
  }, []);

  return (
    <div className="app-container">
      {/* 공유 비디오 요소 (숨김) */}
      <video 
        ref={sharedVideoRef}
        autoPlay
        muted
        playsInline
        style={{ display: 'none' }}
      />
      
      {/* EyeTracker가 시선 추적과 얼굴 분석을 모두 처리 */}
      <EyeTracker
        isTracking={isTracking}
        onGazeData={handleGazeData}
        onFaceAnalysis={handleFaceAnalysis}
      />


      <header className="app-header">
        <div className="header-left">
          <div className="logo">
            <span className="logo-nh">NH</span>
            <span className="logo-bank">Bank</span>
          </div>
          <div className="customer-info">
            <span className="customer-name">{customerName} 고객님</span>
            <span className="product-badge">{productType} 상담</span>
          </div>
        </div>
        <div className="header-right">
          {/*<div className="tracking-status">*/}
          {/*  <span className="status-indicator camera">*/}
          {/*    <span className="status-dot"></span>*/}
          {/*    카메라 {isTracking ? '활성' : '비활성'}*/}
          {/*  </span>*/}
          {/*  <span className="status-indicator eye-track">*/}
          {/*    <span className="status-dot"></span>*/}
          {/*    시선추적 {isTracking ? '실행중' : '정지'}*/}
          {/*  </span>*/}
          {/*</div>*/}
          {/*<div className="ai-status">*/}
          {/*  <span className={`ai-indicator ${showAIHelper ? 'active' : ''}`}>*/}
          {/*    <span className="ai-dot"></span>*/}
          {/*    AI 도우미 {showAIHelper ? '활성' : '대기'}*/}
          {/*  </span>*/}
          {/*</div>*/}
          <div className="time">{new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      </header>

      <main className="app-main">
        <div className="main-grid simplified">
          <aside className="sidebar-left">
            <div className="progress-card">
              <h3 className="card-title">상담 진행도</h3>
              <div className="progress-steps">
                <div className="step completed">
                  <span className="step-number">1</span>
                  <span className="step-label">상품소개</span>
                </div>
                <div className="step active">
                  <span className="step-number">2</span>
                  <span className="step-label">약관확인</span>
                </div>
                <div className="step">
                  <span className="step-number">3</span>
                  <span className="step-label">가입신청</span>
                </div>
              </div>
            </div>
          </aside>

          <div className="main-content" ref={pdfViewerRef}>
            <div className="status-bar">
              <div className="status-item">
                <span className="status-label">상담 상품</span>
              </div>
            </div>
            <PDFViewer
              fileUrl="/NH내가Green초록세상예금.pdf"
              onPdfLoaded={(textRegions) => {
                setPdfTextRegions(textRegions);
                console.log(`📚 PDF 텍스트 영역 로드 완료: ${textRegions.length}개`);
              }}
            />
          </div>

          <aside className="sidebar-right">
            {confusedSections.length > 0 && (
              <div className="ai-insights-card">
                <div className="card-header-with-icon">
                  <span className="card-icon"></span>
                  <h3 className="card-title">NH AI 도우미</h3>
                </div>
                <div className="insights-content">
                  <p className="insight-intro">
                    어려워하시는 부분을 감지했습니다
                  </p>
                </div>
              </div>
            )}
            <div className="terms-card">
              <h3 className="card-title">주요 용어</h3>
              <div className="terms-list">
                {mainTerms.length > 0 ? (
                  mainTerms.map((term, index) => (
                    <div key={index} className="term-item">
                      <strong>{term.term}</strong>
                      <p>{term.definition}</p>
                    </div>
                  ))
                ) : (
                  <>
                    <div className="term-item">
                      <strong>중도해지</strong>
                      <p>만기 전 예금 인출</p>
                    </div>
                    <div className="term-item">
                      <strong>우대금리</strong>
                      <p>조건 충족 시 추가 이자</p>
                    </div>
                    <div className="term-item">
                      <strong>예금자보호</strong>
                      <p>5천만원까지 보장</p>
                    </div>
                  </>
                )}
              </div>
            </div>
          </aside>
        </div>
      </main>

      {/* 시선 포인터 표시 */}
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
      
      {/* 디버그 정보 표시 */}
      {showDebugInfo && (
        <div
          style={{
            position: 'fixed',
            top: '10px',
            right: '10px',
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            color: 'white',
            padding: '10px',
            borderRadius: '5px',
            fontSize: '12px',
            fontFamily: 'monospace',
            zIndex: 10000,
            maxWidth: '300px'
          }}
        >
          <div>👁️ 아이트래킹 디버그</div>
          <div>━━━━━━━━━━━━━━━━━━</div>
          <div>상태: {isTracking ? '✅ 활성' : '❌ 비활성'}</div>
          <div>시선 X: {currentGazePosition?.x.toFixed(0) || 'N/A'}</div>
          <div>시선 Y: {currentGazePosition?.y.toFixed(0) || 'N/A'}</div>
          <div>버퍼 크기: {gazeDataBuffer.length}</div>
          <div>PDF 영역: {pdfTextRegions.length}개</div>
          <div>얼굴 분석: {faceAnalysisBuffer.length}개</div>
          <div>━━━━━━━━━━━━━━━━━━</div>
          <button
            onClick={() => setShowDebugInfo(false)}
            style={{
              marginTop: '5px',
              fontSize: '10px',
              padding: '2px 5px'
            }}
          >
            닫기
          </button>
        </div>
      )}

      <footer className="app-footer">
        <div className="footer-left">
          <span className="footer-text">NH농협은행 디지털 상담 시스템</span>
        </div>
        <div className="footer-center">
          {showAIHelper && (
            <span className="ai-active-notice">
              <span className="notice-icon">c</span>
              AI 도우미가 도움을 드리고 있습니다
            </span>
          )}
        </div>
        <div className="footer-actions">
          <button className="action-btn secondary">이전</button>
          <button className="action-btn primary">다음 단계</button>
        </div>
      </footer>
    </div>
  );
}

export default App;
