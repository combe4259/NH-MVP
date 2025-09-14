import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';
import './App.css';
import AIAssistant from './components/AIAssistant';
import PDFViewer from './components/PDFViewer';

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

  // Use useRef instead of state to avoid re-renders
  const lastAnalyzedSectionRef = useRef<string | null>(null);

  const sendAnalysisData = useCallback(async (sectionName: string, sectionText: string, readingTime: number) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/eyetracking/analyze`, {
        consultation_id: '29853704-6f54-4df2-bb40-6efa9a63cf53',
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
          setHighlightedTexts(newHighlights);
        }
        setShowAIHelper(true);
      }
    } catch (error) {
      console.error('분석 데이터 전송 실패:', error);

      const mockConfusedSection = {
        id: 'section3',
        title: '중도해지 시 불이익',
        content: '만기 전 중도해지 시 약정한 우대이율은 적용되지 않습니다',
        timestamp: new Date()
      };

      setConfusedSections([mockConfusedSection]);
      setAiSuggestion({
        section: '중도해지 시 불이익',
        explanation: '중도해지란 정기예금 만기일 전에 예금을 찾는 것을 말합니다. 이 경우 약속했던 높은 이자율 대신 낮은 이자율이 적용됩니다.',
        simpleExample: '예를 들어, 1년 만기 연 4% 예금을 6개월 만에 해지하면 연 0.5% 정도의 낮은 이자만 받게 됩니다.'
      });

      setHighlightedTexts([
        { text: '중도해지', explanation: '정기예금 만기일 전에 예금을 찾는 것을 의미합니다.' },
        { text: '우대이율', explanation: '은행에서 특정 조건을 충족할 때 제공하는 추가 이자율입니다.' }
      ]);
      setShowAIHelper(true);
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

  // 주기적 AI 분석 (fixed with useRef)
  useEffect(() => {
    if (!isTracking) return;

    if (currentSection && currentSection !== lastAnalyzedSectionRef.current) {
      console.log('Analyzing new section:', currentSection); // Debug log
      const timer = setTimeout(() => {
        sendAnalysisData(currentSection, '상품의 주요 내용에 대한 설명입니다.', 5000);
        lastAnalyzedSectionRef.current = currentSection; // Update ref (no re-render)
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [isTracking, currentSection, sendAnalysisData]); // Removed lastAnalyzedSection from deps

  const handleAIHelperDismiss = () => {
    setShowAIHelper(false);
    setAiSuggestion(null);
  };

  const handleRequestMoreInfo = (topic: string) => {
    console.log('추가 설명 요청:', topic);
  };

  return (
    <div className="app-container">
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
                onTextSelect={(text) => {
                  console.log('선택된 텍스트:', text);
                }}
              />
              {showAIHelper && aiSuggestion && (
                <div className="ai-helper-overlay">
                  <AIAssistant
                    suggestion={aiSuggestion}
                    onDismiss={handleAIHelperDismiss}
                    onRequestMore={handleRequestMoreInfo}
                  />
                </div>
              )}
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