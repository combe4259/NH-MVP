import React, { useState, useEffect } from 'react';
import './App.css';
import DocumentViewer from './components/DocumentViewer';
import AIAssistant from './components/AIAssistant';

interface ConfusedSection {
  id: string;
  title: string;
  content: string;
  timestamp: Date;
}

function App() {
  const [isTracking, setIsTracking] = useState(false);
  const [currentSection, setCurrentSection] = useState('');
  const [customerName] = useState('김민수');
  const [productType] = useState('정기예금');
  const [readingProgress, setReadingProgress] = useState(0);
  const [showAIHelper, setShowAIHelper] = useState(false);
  const [confusedSections, setConfusedSections] = useState<ConfusedSection[]>([]);
  const [aiSuggestion, setAiSuggestion] = useState<{
    section: string;
    explanation: string;
    simpleExample?: string;
  } | null>(null);

  useEffect(() => {
    // 시선 추적 시뮬레이션
    if (isTracking) {
      console.log('시선 추적 시작...');
      
      // 시뮬레이션: 5초 후 어려운 부분 감지
      setTimeout(() => {
        const mockConfusedSection = {
          id: 'section3',
          title: '중도해지 시 불이익',
          content: '만기 전 중도해지 시 약정한 우대이율은 적용되지 않습니다',
          timestamp: new Date()
        };
        
        setConfusedSections([mockConfusedSection]);
        
        // AI 도우미 자동 활성화
        setAiSuggestion({
          section: '중도해지 시 불이익',
          explanation: '중도해지란 정기예금 만기일 전에 예금을 찾는 것을 말합니다. 이 경우 약속했던 높은 이자율 대신 낮은 이자율이 적용됩니다.',
          simpleExample: '예를 들어, 1년 만기 연 4% 예금을 6개월 만에 해지하면 연 0.5% 정도의 낮은 이자만 받게 됩니다.'
        });
        
        setShowAIHelper(true);
      }, 5000);
      
      // 읽기 진행률 업데이트
      const progressInterval = setInterval(() => {
        setReadingProgress(prev => Math.min(prev + 5, 100));
      }, 1000);
      
      return () => clearInterval(progressInterval);
    }
  }, [isTracking]);

  const handleAIHelperDismiss = () => {
    setShowAIHelper(false);
    setAiSuggestion(null);
  };

  const handleRequestMoreInfo = (topic: string) => {
    // 추가 설명 요청 처리
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
            <div className="quick-menu">
              <button className="menu-item active">
                <span className="menu-icon">📄</span>
                <span className="menu-label">상품약관</span>
              </button>
              <button className="menu-item">
                <span className="menu-icon">💰</span>
                <span className="menu-label">이자계산</span>
              </button>
              <button className="menu-item">
                <span className="menu-icon">📊</span>
                <span className="menu-label">비교분석</span>
              </button>
              <button className="menu-item">
                <span className="menu-icon">❓</span>
                <span className="menu-label">FAQ</span>
              </button>
            </div>

            {/* 진행 상태 카드 */}
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

            {/* 읽기 진행률 */}
            <div className="reading-progress-card">
              <h3 className="card-title">읽기 진행률</h3>
              <div className="progress-circle">
                <svg width="120" height="120">
                  <circle cx="60" cy="60" r="50" fill="none" stroke="#e0e0e0" strokeWidth="8" />
                  <circle 
                    cx="60" cy="60" r="50" 
                    fill="none" 
                    stroke="#00A651" 
                    strokeWidth="8"
                    strokeDasharray={`${readingProgress * 3.14} 314`}
                    strokeLinecap="round"
                    transform="rotate(-90 60 60)"
                  />
                </svg>
                <div className="progress-value">{readingProgress}%</div>
              </div>
            </div>
          </aside>

          {/* 중앙 메인 콘텐츠 */}
          <div className="main-content">
            {/* 상태 바 */}
            <div className="status-bar">
              <div className="status-item">
                <span className="status-label">현재 읽는 부분</span>
                <span className="status-value">{currentSection || '시작 전'}</span>
              </div>
              <div className="status-divider"></div>
              <div className="tracking-status">
                <span className="status-label">분석 상태</span>
                <div className={`status-indicator ${isTracking ? 'active' : ''}`}>
                  <span className="indicator-dot"></span>
                  <span className="indicator-text">{isTracking ? '분석 중' : '대기'}</span>
                </div>
              </div>
              {!isTracking && (
                <button 
                  className="tracking-toggle"
                  onClick={() => setIsTracking(true)}
                >
                  읽기 시작
                </button>
              )}
            </div>

            {/* 문서 뷰어 */}
            <div className="document-container">
              <DocumentViewer 
                onSectionChange={setCurrentSection}
                isTracking={isTracking}
              />
              
              {/* AI 도우미 오버레이 */}
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
            {/* AI 인사이트 카드 */}
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

            {/* 이해도 체크 카드 */}
            <div className="understanding-card">
              <h3 className="card-title">이해도 체크</h3>
              <div className="understanding-levels">
                <button className="level-btn level-good">
                  <span className="level-icon">😊</span>
                  <span>잘 이해했어요</span>
                </button>
                <button className="level-btn level-medium">
                  <span className="level-icon">🤔</span>
                  <span>조금 어려워요</span>
                </button>
                <button className="level-btn level-help">
                  <span className="level-icon">🙋</span>
                  <span>도움이 필요해요</span>
                </button>
              </div>
            </div>

            {/* 용어 설명 카드 */}
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

            {/* 도움 요청 카드 */}
            <div className="help-card">
              <h3 className="card-title">추가 도움</h3>
              <div className="help-options">
                <button className="help-option">
                  <span className="option-icon">👨‍💼</span>
                  <span>직원 호출</span>
                </button>
                <button className="help-option">
                  <span className="option-icon">💬</span>
                  <span>채팅 상담</span>
                </button>
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