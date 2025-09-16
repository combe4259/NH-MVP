import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import './App.css';
import AIAssistant from './components/AIAssistant';
import PDFViewer from './components/PDFViewer';
import WebcamFaceDetection from './components/WebcamFaceDetection';

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
  const [showAIHelper, setShowAIHelper] = useState(false);
  const [confusedSections, setConfusedSections] = useState<ConfusedSection[]>([]);
  const [aiSuggestion, setAiSuggestion] = useState<{
    section: string;
    explanation: string;
    simpleExample?: string;
  } | null>(null);
  const [highlightedTexts, setHighlightedTexts] = useState<HighlightedText[]>([]);
  const [difficultSentences, setDifficultSentences] = useState<DifficultSentence[]>([]);
  const [mainTerms, setMainTerms] = useState<{term: string, definition: string}[]>([]);

  // Use useRef instead of state to avoid re-renders
  const lastAnalyzedSectionRef = useRef<string | null>(null);

  const analyzeTextContent = useCallback(async (sectionName: string, sectionText: string) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/text/analyze-text`, {
        section_text: sectionText,
        consultation_id: '29853704-6f54-4df2-bb40-6efa9a63cf53',
        current_section: sectionName
      });

      const analysisData = response.data;

      // API 응답 대신 우리 목업데이터 사용 (테스트용)
      const mockDifficultSentences: DifficultSentence[] = [
        {
          sentence: '계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한',
          sentence_id: 'sentence_001',
          difficulty_score: 0.8,
          simplified_explanation: '법원에서 계좌를 막거나, 다른 사람이 그 돈에 대한 권리를 주장하면, 예금을 찾을 수 없게 됩니다.',
          original_position: 1,
          location: {
            page_number: 1,
            page_width: 595,  // A4 페이지 너비 (pt)
            page_height: 842, // A4 페이지 높이 (pt)
            x: 100,           // 실제 PDF에서 찾을 위치 (pt)
            y: 400,           // 실제 PDF에서 찾을 위치 (pt)
            width: 400,
            height: 25
          }
        }
      ];

      setDifficultSentences(mockDifficultSentences);

      // 우측 사이드바 주요 용어 설정
      setMainTerms([
        { term: '압류', definition: '법원의 재산 동결 조치' },
        { term: '가압류', definition: '임시 재산 동결' },
        { term: '질권설정', definition: '담보 목적 예금 잠금' }
      ]);

      // 전체 이해도가 낮으면 AI 도우미 표시 (원본 코드)
      // if (analysisData.overall_difficulty > 0.6) {
      //   setAiSuggestion({
      //     section: sectionName,
      //     explanation: `이 섹션의 이해도가 낮게 측정되었습니다. 전체적인 난이도: ${(analysisData.overall_difficulty * 100).toFixed(0)}%`,
      //     simpleExample: analysisData.difficult_sentences.length > 0 ?
      //       `특히 "${analysisData.difficult_sentences[0].sentence.substring(0, 30)}..." 부분이 어려울 수 있습니다.` :
      //       '어려운 부분이 있으면 밑줄 친 문장을 클릭해 보세요.'
      //   });
      //   setShowAIHelper(true);
      // }

      // setSpecificMockData(); // 좌표 데이터를 덮어쓰지 않도록 주석 처리

      console.log('텍스트 분석 완료:', analysisData);

    } catch (error) {
      console.error('텍스트 분석 실패:', error);
      // 폴백으로 특정 문장 목업데이터 사용
      setSpecificMockData();
    }
  }, []);

  const sendAnalysisData = useCallback(async (sectionName: string, sectionText: string, readingTime: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/eyetracking/analyze`, {
        consultation_id: '29853704-6f54-4df2-bb40-6efa9a63cf53',
        customer_id: '12345678-1234-5678-9012-123456789012',
        current_section: sectionName,
        section_text: sectionText,
        reading_time: readingTime,
        gaze_data: {
          fixation_count: Math.floor(Math.random() * 20) + 5,
          fixation_duration: Math.floor(Math.random() * 3000) + 1000,
          saccade_count: Math.floor(Math.random() * 15) + 5,
          regression_count: Math.floor(Math.random() * 5)
        }
      });

      const analysis = response.data;

      if (analysis.confusion_probability > 0.6) {
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

        if (analysis.difficult_terms && analysis.detailed_explanations) {
          const newHighlights: HighlightedText[] = analysis.difficult_terms.map((term: string) => ({
            text: term,
            explanation: analysis.detailed_explanations[term] || '이 용어에 대한 설명이 필요합니다.'
          }));

          // 하이라이트가 실제로 변경된 경우에만 업데이트
          setHighlightedTexts(prev => {
            const prevTexts = prev.map(h => h.text).join(',');
            const newTexts = newHighlights.map(h => h.text).join(',');
            return prevTexts !== newTexts ? newHighlights : prev;
          });
        }
        setShowAIHelper(true);
      }
    } catch (error) {
      console.error('분석 데이터 전송 실패:', error);
      // 폴백으로 특정 문장 목업데이터 사용
      setSpecificMockData();
    }
  }, []);

  useEffect(() => {
    console.log('컴포넌트 마운트됨 - 시선 추적 시작');
    setIsTracking(true);
    return () => {
      console.log('컴포넌트 언마운트됨 - 시선 추적 중지');
      setIsTracking(false);
    };
  }, []);

  // AI 상태 폴링 함수 추가
  const checkAIStatus = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/eyetracking/ai-status/29853704-6f54-4df2-bb40-6efa9a63cf53`);
      const aiStatus = response.data;

      // AI 서버가 "도우미를 띄워라"고 결정한 경우에만 팝업
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

  // 주기적 AI 분석 및 상태 확인
  useEffect(() => {
    if (!isTracking) return;

    if (currentSection && currentSection !== lastAnalyzedSectionRef.current) {
      console.log('Analyzing new section:', currentSection);
      const timer = setTimeout(() => {
        // 기존 아이트래킹 분석
        sendAnalysisData(currentSection, '상품의 주요 내용에 대한 설명입니다.', 5000);
        // 텍스트 분석
        analyzeTextContent(currentSection, '만기 전 중도해지 시 약정한 우대이율은 적용되지 않습니다. 예금자보호법에 따른 보호 한도는 5천만원입니다.');
        lastAnalyzedSectionRef.current = currentSection;
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [isTracking, currentSection, sendAnalysisData, analyzeTextContent]);

  // AI 상태 주기적 확인 (3초마다)
  useEffect(() => {
    if (!isTracking) return;

    const statusInterval = setInterval(checkAIStatus, 3000);
    return () => clearInterval(statusInterval);
  }, [isTracking, checkAIStatus]);

  const handleAIHelperDismiss = () => {
    setShowAIHelper(false);
    setAiSuggestion(null);
  };

  const handleRequestMoreInfo = (topic: string) => {
    console.log('추가 설명 요청:', topic);
  };

  const setSpecificMockData = () => {
    // 사용자가 요청한 특정 문장에 대한 목업데이터
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

    // AI 도우미도 설정
    setAiSuggestion({
      section: '압류 관련 제한 사항',
      explanation: '계좌에 법적 조치가 취해지면 예금을 찾을 수 없게 됩니다.',
      simpleExample: '법원에서 계좌를 막거나, 빚 담보로 예금이 잡히면 돈을 찾을 수 없습니다.'
    });
    setShowAIHelper(true);
  };

  const setFallbackData = (sectionName: string) => {
    // 기존 하드코딩 데이터 사용
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

  const handleSentenceClick = (sentence: DifficultSentence) => {
    setAiSuggestion({
      section: sentence.sentence.substring(0, 20) + '...',
      explanation: sentence.simplified_explanation,
      simpleExample: '구체적인 예시나 추가 설명이 필요하시면 직원에게 문의해 주세요.'
    });
    setShowAIHelper(true);
  };

  // Raw 얼굴 감정 데이터만 전송 (판단은 AI 서버에서)
  const sendRawEmotionData = useCallback(async (emotions: any) => {
    try {
      await axios.post(`${API_BASE_URL}/eyetracking/submit-emotion-data`, {
        consultation_id: '29853704-6f54-4df2-bb40-6efa9a63cf53',
        customer_id: '12345678-1234-5678-9012-123456789012',
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
    // Raw 데이터만 전송, 분석과 판단은 AI 서버에서
    if (data.hasDetection && data.emotions) {
      // Raw 감정 점수만 전송
      sendRawEmotionData(data.emotions);
    }
  };

  return (
    <div className="app-container">
      {/* 숨겨진 웹캠 (백그라운드 얼굴 분석용) */}
      <div style={{ display: 'none' }}>
        <WebcamFaceDetection
          isActive={isTracking}
          onFaceAnalysis={handleFaceAnalysis}
        />
      </div>

      {/* 상단 헤더 */}
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
          <div className="ai-status">
            <span className={`ai-indicator ${showAIHelper ? 'active' : ''}`}>
              <span className="ai-dot"></span>
              AI 도우미 {showAIHelper ? '활성' : '대기'}
            </span>
          </div>
          <div className="time">{new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="app-main">
        <div className="main-grid simplified">
          {/* 왼쪽 사이드바 */}
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

          {/* 중앙 메인 콘텐츠 */}
          <div className="main-content">
            <div className="status-bar">
              <div className="status-item">
                <span className="status-label">상담 상품</span>
                <span className="status-value">{currentSection || '정기 예금'}</span>
              </div>
            </div>
            <div className="document-container">
              <PDFViewer
                fileUrl="/NH내가Green초록세상예금.pdf"
                highlightedTexts={highlightedTexts}
                difficultSentences={difficultSentences}
                onTextSelect={(text) => {
                  console.log('선택된 텍스트:', text);
                }}
                onSentenceClick={handleSentenceClick}
              />
              {/* AI 도우미 우측 하단 팝업 제거 */}
            </div>
          </div>

          {/* 오른쪽 사이드바 */}
          <aside className="sidebar-right">
            {confusedSections.length > 0 && (
              <div className="ai-insights-card">
                <div className="card-header-with-icon">
                  <span className="card-icon">🤖</span>
                  <h3 className="card-title">AI 도우미</h3>
                </div>
                <div className="insights-content">
                  <p className="insight-intro">
                    어려워하시는 부분을 감지했습니다
                  </p>
                  <div className="confused-sections">
                    {confusedSections.map(section => (
                      <div key={section.id} className="confused-item">
                        <strong>{section.title}</strong>
                        <p>{section.content}</p>
                        <button
                          className="explain-btn"
                          onClick={() => setShowAIHelper(true)}
                        >
                          쉽게 설명 듣기
                        </button>
                      </div>
                    ))}
                  </div>
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
                  // 분석 결과 없을 때 기본값
                  <>
                    <div className="term-item">
                      <strong>중도해지</strong>
                      <p>만기 전 예금을 찾는 것</p>
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

      {/* 하단 액션 바 */}
      <footer className="app-footer">
        <div className="footer-left">
          <span className="footer-text">NH농협은행 디지털 상담 시스템</span>
        </div>
        <div className="footer-center">
          {showAIHelper && (
            <span className="ai-active-notice">
              <span className="notice-icon">💡</span>
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