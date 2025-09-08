import React, { useState } from 'react';
import './App.css';
import DocumentViewer from './components/DocumentViewer';
import EyeTracker from './components/EyeTracker';
import EmotionRecognition from './components/EmotionRecognition';

function App() {
  const [isTracking, setIsTracking] = useState(false);
  const [currentSection, setCurrentSection] = useState('');
  const [customerName] = useState('김민수');
  const [productType] = useState('정기예금');

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
          <div className="time">{new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}</div>
          <button className="help-btn">도움말</button>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="app-main">
        <div className="main-grid">
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
          </aside>

          {/* 중앙 메인 콘텐츠 */}
          <div className="main-content">
            {/* 상태 바 */}
            <div className="status-bar">
              <div className="status-item">
                <span className="status-label">현재 섹션</span>
                <span className="status-value">{currentSection || '대기 중'}</span>
              </div>
              <div className="status-divider"></div>
              <div className="status-item">
                <span className="status-label">분석 상태</span>
                <div className={`status-indicator ${isTracking ? 'active' : ''}`}>
                  <span className="indicator-dot"></span>
                  <span className="indicator-text">{isTracking ? '분석 중' : '대기'}</span>
                </div>
              </div>
              <button 
                className={`tracking-toggle ${isTracking ? 'active' : ''}`}
                onClick={() => setIsTracking(!isTracking)}
              >
                {isTracking ? '분석 중지' : '분석 시작'}
              </button>
            </div>

            {/* 문서 뷰어 */}
            <div className="document-container">
              <DocumentViewer 
                onSectionChange={setCurrentSection}
                isTracking={isTracking}
              />
            </div>
          </div>

          {/* 오른쪽 사이드바 */}
          <aside className="sidebar-right">
            {/* 실시간 분석 카드 */}
            <div className="analysis-cards">
              <div className="analysis-card">
                <div className="card-header">
                  <h3 className="card-title">시선 추적</h3>
                  <span className={`card-badge ${isTracking ? 'active' : ''}`}>
                    {isTracking ? 'ON' : 'OFF'}
                  </span>
                </div>
                <div className="mini-tracker">
                  <EyeTracker isTracking={isTracking} />
                </div>
              </div>

              <div className="analysis-card">
                <div className="card-header">
                  <h3 className="card-title">감정 분석</h3>
                  <span className={`card-badge ${isTracking ? 'active' : ''}`}>
                    {isTracking ? 'ON' : 'OFF'}
                  </span>
                </div>
                <div className="mini-emotion">
                  <EmotionRecognition isTracking={isTracking} />
                </div>
              </div>

              {/* 도움 카드 */}
              <div className="help-card">
                <h3 className="card-title">도움이 필요하신가요?</h3>
                <p className="help-text">언제든지 직원을 호출하실 수 있습니다</p>
                <button className="call-staff-btn">
                  <span className="btn-icon">🔔</span>
                  직원 호출
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
        <div className="footer-actions">
          <button className="action-btn secondary">이전</button>
          <button className="action-btn primary">다음 단계</button>
        </div>
      </footer>
    </div>
  );
}

export default App;