import React, { useState, useEffect } from 'react';
import './App.css';

interface CustomerData {
  id: string;
  name: string;
  productType: string;
  productDetails: {
    name: string;
    type: string;
    amount?: string;
    period?: string;
    interestRate?: string;
  };
  consultationPhase: 'product_intro' | 'terms_reading' | 'application' | 'completed';
  currentSection: string;
  emotionState: string;
  comprehensionLevel: number;
  startTime: Date;
  focusAreas: string[];
  confusedSections: Array<{
    section: string;
    duration: number;
    returnCount: number;
  }>;
  readingSpeed: number;
  attentionScore: number;
  riskFactors: string[];
  recommendations: Array<{
    priority: 'high' | 'medium' | 'low';
    action: string;
    reason: string;
  }>;
}

interface MetricData {
  label: string;
  value: number;
  change: number;
  trend: 'up' | 'down' | 'stable';
}

function App() {
  const [customers, setCustomers] = useState<CustomerData[]>([
    {
      id: '1',
      name: '김민수',
      productType: '정기예금',
      productDetails: {
        name: 'NH 행복드림 정기예금',
        type: '정기예금',
        amount: '10,000,000원',
        period: '12개월',
        interestRate: '연 4.0%'
      },
      consultationPhase: 'terms_reading',
      currentSection: '중도해지 시 불이익',
      emotionState: 'confused',
      comprehensionLevel: 65,
      startTime: new Date(Date.now() - 300000),
      focusAreas: ['상품 개요', '이자율'],
      confusedSections: [
        { section: '중도해지 불이익', duration: 45, returnCount: 3 },
        { section: '우대금리 조건', duration: 30, returnCount: 2 }
      ],
      readingSpeed: 180,
      attentionScore: 78,
      riskFactors: ['중도해지 조항 미이해', '우대조건 복잡성'],
      recommendations: [
        { priority: 'high', action: '중도해지 수수료 계산 예시 제공', reason: '해당 부분을 3번 이상 반복 읽음' },
        { priority: 'medium', action: '우대금리 조건 체크리스트 제공', reason: '우대조건 부분에서 혼란 감지' },
        { priority: 'low', action: '유사 상품 비교표 준비', reason: '상품 비교에 관심 표현' }
      ]
    },
    {
      id: '2',
      name: '이서연',
      productType: '적금',
      productDetails: {
        name: 'NH 올원 적금',
        type: '적금',
        amount: '500,000원/월',
        period: '24개월',
        interestRate: '연 4.5%'
      },
      consultationPhase: 'application',
      currentSection: '가입 신청서 작성',
      emotionState: 'focused',
      comprehensionLevel: 88,
      startTime: new Date(Date.now() - 180000),
      focusAreas: ['상품 개요', '세제 혜택'],
      confusedSections: [],
      readingSpeed: 220,
      attentionScore: 92,
      riskFactors: [],
      recommendations: [
        { priority: 'low', action: '자동이체 설정 안내', reason: '신청서 작성 단계 진입' },
        { priority: 'low', action: '세제혜택 추가 설명 준비', reason: '세제 부분 높은 관심' }
      ]
    },
    {
      id: '3',
      name: '박정호',
      productType: '펀드',
      productDetails: {
        name: 'NH-Amundi 글로벌 펀드',
        type: '펀드',
        amount: '5,000,000원',
        period: '자유',
        interestRate: '변동금리'
      },
      consultationPhase: 'product_intro',
      currentSection: '투자 위험 고지',
      emotionState: 'stressed',
      comprehensionLevel: 45,
      startTime: new Date(Date.now() - 600000),
      focusAreas: [],
      confusedSections: [
        { section: '투자 위험 등급', duration: 60, returnCount: 5 },
        { section: '환매 수수료', duration: 50, returnCount: 4 },
        { section: '과세 체계', duration: 40, returnCount: 3 }
      ],
      readingSpeed: 120,
      attentionScore: 55,
      riskFactors: ['투자 경험 부족', '위험 이해도 낮음', '복잡한 수수료 체계'],
      recommendations: [
        { priority: 'high', action: '투자 시뮬레이션 도구 활용', reason: '투자 위험 이해 어려움' },
        { priority: 'high', action: '단계별 설명으로 전환', reason: '전반적 이해도 50% 미만' },
        { priority: 'medium', action: '더 안전한 상품 소개 준비', reason: '스트레스 수준 높음' }
      ]
    }
  ]);
  
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerData | null>(customers[0]);
  const [alerts, setAlerts] = useState<Array<{ id: string; message: string; type: string; time: Date; customerId: string }>>([]);
  
  const [metrics] = useState<MetricData[]>([
    { label: '활성 상담', value: 3, change: 1, trend: 'up' },
    { label: '평균 이해도', value: 66, change: -5, trend: 'down' },
    { label: '위험 고객', value: 1, change: 1, trend: 'up' },
    { label: '완료 예정', value: 1, change: 0, trend: 'stable' }
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCustomers(prev => prev.map(customer => ({
        ...customer,
        comprehensionLevel: Math.max(0, Math.min(100, customer.comprehensionLevel + (Math.random() - 0.5) * 10)),
        emotionState: ['neutral', 'focused', 'confused', 'stressed'][Math.floor(Math.random() * 4)],
        attentionScore: Math.max(0, Math.min(100, customer.attentionScore + (Math.random() - 0.5) * 8))
      })));
      
      if (Math.random() > 0.6) {
        const customerAlerts = [
          { customer: '김민수', message: '중도해지 조항을 5번째 읽고 있습니다. 즉시 개입 필요', type: 'critical' },
          { customer: '박정호', message: '이해도 50% 미만 - 상담 방식 변경 권장', type: 'warning' },
          { customer: '이서연', message: '신청서 작성 단계 진입 - 마무리 지원 필요', type: 'info' }
        ];
        const alert = customerAlerts[Math.floor(Math.random() * customerAlerts.length)];
        const newAlert = {
          id: Date.now().toString(),
          message: alert.message,
          type: alert.type,
          time: new Date(),
          customerId: alert.customer
        };
        setAlerts(prev => [newAlert, ...prev].slice(0, 8));
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getPhaseLabel = (phase: string) => {
    const labels: { [key: string]: string } = {
      'product_intro': '상품 소개',
      'terms_reading': '약관 확인',
      'application': '가입 신청',
      'completed': '상담 완료'
    };
    return labels[phase] || phase;
  };

  const getPhaseProgress = (phase: string) => {
    const progress: { [key: string]: number } = {
      'product_intro': 25,
      'terms_reading': 50,
      'application': 75,
      'completed': 100
    };
    return progress[phase] || 0;
  };

  const getEmotionIcon = (emotion: string) => {
    const icons: { [key: string]: string } = {
      neutral: '😐',
      focused: '🧐',
      confused: '😕',
      stressed: '😰'
    };
    return icons[emotion] || '😐';
  };

  const getEmotionLabel = (emotion: string) => {
    const labels: { [key: string]: string } = {
      neutral: '평온',
      focused: '집중',
      confused: '혼란',
      stressed: '스트레스'
    };
    return labels[emotion] || '평온';
  };

  const formatTime = (date: Date) => {
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (diff < 60) return `${diff}초 전`;
    if (diff < 3600) return `${Math.floor(diff / 60)}분 전`;
    return `${Math.floor(diff / 3600)}시간 전`;
  };

  const getDuration = (startTime: Date) => {
    const diff = Math.floor((new Date().getTime() - startTime.getTime()) / 1000);
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getPriorityColor = (priority: string) => {
    const colors: { [key: string]: string } = {
      high: '#f44336',
      medium: '#ff9800',
      low: '#4caf50'
    };
    return colors[priority] || '#999';
  };

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-brand">
          <div className="logo">
            <span className="logo-nh">NH</span>
            <span className="logo-bank">Bank</span>
          </div>
          <h1 className="dashboard-title">스마트 상담 관리 시스템</h1>
        </div>
        
        <div className="header-nav">
          <button className="nav-item active">실시간 모니터링</button>
          <button className="nav-item">상담 이력</button>
          <button className="nav-item">성과 분석</button>
          <button className="nav-item">설정</button>
        </div>
        
        <div className="header-user">
          <span className="notifications">
            <span className="notification-icon">🔔</span>
            <span className="notification-count">{alerts.filter(a => a.type === 'critical').length}</span>
          </span>
          <div className="user-info">
            <span className="user-name">김상담 매니저</span>
            <span className="user-role">디지털혁신점</span>
          </div>
          <div className="user-avatar">KS</div>
        </div>
      </header>

      {/* Main Content */}
      <main className="dashboard-main">
        {/* Metrics Row */}
        <div className="metrics-row">
          {metrics.map((metric, index) => (
            <div key={index} className="metric-card">
              <div className="metric-header">
                <span className="metric-label">{metric.label}</span>
                <span className={`metric-change ${metric.trend}`}>
                  {metric.trend === 'up' ? '↑' : metric.trend === 'down' ? '↓' : '→'}
                  {Math.abs(metric.change)}
                </span>
              </div>
              <div className="metric-value">{metric.value}</div>
              <div className="metric-subtext">
                {metric.label === '위험 고객' && metric.value > 0 && (
                  <span className="warning-text">즉시 개입 필요</span>
                )}
              </div>
            </div>
          ))}
        </div>

        <div className="dashboard-grid">
          {/* Customer List */}
          <div className="panel customer-panel">
            <div className="panel-header">
              <h2 className="panel-title">진행 중인 상담</h2>
              <div className="panel-controls">
                <select className="filter-select">
                  <option>전체 상담</option>
                  <option>위험 고객</option>
                  <option>신규 가입</option>
                </select>
              </div>
            </div>
            
            <div className="customer-list">
              {customers.map(customer => (
                <div 
                  key={customer.id}
                  className={`customer-item ${selectedCustomer?.id === customer.id ? 'selected' : ''} ${customer.comprehensionLevel < 50 ? 'risk' : ''}`}
                  onClick={() => setSelectedCustomer(customer)}
                >
                  <div className="customer-avatar">
                    {customer.name.substring(0, 2)}
                  </div>
                  
                  <div className="customer-details">
                    <div className="customer-header-info">
                      <span className="customer-name">{customer.name}</span>
                      <span className="product-type">{customer.productType}</span>
                    </div>
                    <div className="consultation-progress">
                      <span className="phase-label">{getPhaseLabel(customer.consultationPhase)}</span>
                      <div className="progress-bar-mini">
                        <div className="progress-fill-mini" style={{ width: `${getPhaseProgress(customer.consultationPhase)}%` }}></div>
                      </div>
                    </div>
                    <div className="customer-meta">
                      <span className="meta-item">{customer.currentSection}</span>
                      <span className="meta-divider">•</span>
                      <span className="meta-item">{getDuration(customer.startTime)}</span>
                    </div>
                  </div>
                  
                  <div className="customer-indicators">
                    <div className="emotion-badge">
                      {getEmotionIcon(customer.emotionState)}
                    </div>
                    <div className={`comprehension-indicator level-${Math.floor(customer.comprehensionLevel / 20)}`}>
                      {customer.comprehensionLevel}%
                    </div>
                    {customer.riskFactors.length > 0 && (
                      <div className="risk-badge">
                        <span className="risk-icon">⚠️</span>
                        <span className="risk-count">{customer.riskFactors.length}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Customer Detail */}
          {selectedCustomer && (
            <div className="panel detail-panel">
              <div className="panel-header">
                <h2 className="panel-title">{selectedCustomer.name} 고객 상담 현황</h2>
                <div className="panel-actions">
                  <button className="action-button primary">화상 상담 연결</button>
                  <button className="action-button">메모 작성</button>
                </div>
              </div>
              
              <div className="detail-content">
                {/* 상품 정보 */}
                <div className="product-info-card">
                  <h3 className="section-title">진행 중인 상품</h3>
                  <div className="product-details">
                    <div className="product-name">{selectedCustomer.productDetails.name}</div>
                    <div className="product-specs">
                      <div className="spec-item">
                        <span className="spec-label">상품 유형</span>
                        <span className="spec-value">{selectedCustomer.productDetails.type}</span>
                      </div>
                      <div className="spec-item">
                        <span className="spec-label">가입 금액</span>
                        <span className="spec-value">{selectedCustomer.productDetails.amount}</span>
                      </div>
                      <div className="spec-item">
                        <span className="spec-label">가입 기간</span>
                        <span className="spec-value">{selectedCustomer.productDetails.period}</span>
                      </div>
                      <div className="spec-item">
                        <span className="spec-label">적용 금리</span>
                        <span className="spec-value highlight">{selectedCustomer.productDetails.interestRate}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 이해도 분석 */}
                <div className="comprehension-analysis">
                  <h3 className="section-title">실시간 이해도 분석</h3>
                  <div className="analysis-grid">
                    <div className="analysis-item">
                      <div className="analysis-header">
                        <span className="analysis-label">전체 이해도</span>
                        <span className={`analysis-value ${selectedCustomer.comprehensionLevel < 50 ? 'danger' : selectedCustomer.comprehensionLevel < 70 ? 'warning' : 'success'}`}>
                          {selectedCustomer.comprehensionLevel}%
                        </span>
                      </div>
                      <div className="progress-bar-large">
                        <div 
                          className="progress-fill-large" 
                          style={{ 
                            width: `${selectedCustomer.comprehensionLevel}%`,
                            backgroundColor: selectedCustomer.comprehensionLevel < 50 ? '#f44336' : selectedCustomer.comprehensionLevel < 70 ? '#ff9800' : '#4caf50'
                          }}
                        />
                      </div>
                    </div>

                    <div className="analysis-stats">
                      <div className="stat-item">
                        <span className="stat-icon">📖</span>
                        <span className="stat-value">{selectedCustomer.readingSpeed}</span>
                        <span className="stat-label">단어/분</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-icon">👁️</span>
                        <span className="stat-value">{selectedCustomer.attentionScore}%</span>
                        <span className="stat-label">집중도</span>
                      </div>
                      <div className="stat-item">
                        <span className="stat-icon">{getEmotionIcon(selectedCustomer.emotionState)}</span>
                        <span className="stat-value">{getEmotionLabel(selectedCustomer.emotionState)}</span>
                        <span className="stat-label">감정상태</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 어려워하는 부분 */}
                {selectedCustomer.confusedSections.length > 0 && (
                  <div className="confused-sections-card">
                    <h3 className="section-title">
                      <span className="title-icon">🚨</span>
                      집중 필요 구역
                    </h3>
                    <div className="confused-list">
                      {selectedCustomer.confusedSections.map((section, index) => (
                        <div key={index} className="confused-item-detail">
                          <div className="confused-header">
                            <span className="confused-title">{section.section}</span>
                            <span className="return-badge">{section.returnCount}회 반복</span>
                          </div>
                          <div className="confused-stats">
                            <span className="stat">체류 시간: {section.duration}초</span>
                            <span className="stat">이해도 하락 구간</span>
                          </div>
                          <button className="explain-action">AI 설명 지원</button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI 추천 액션 */}
                <div className="recommendations-card">
                  <h3 className="section-title">
                    <span className="title-icon">🤖</span>
                    AI 상담 가이드
                  </h3>
                  <div className="recommendations-list">
                    {selectedCustomer.recommendations.map((rec, index) => (
                      <div key={index} className="recommendation-item">
                        <div className="rec-priority" style={{ backgroundColor: getPriorityColor(rec.priority) }}>
                          {rec.priority === 'high' ? '긴급' : rec.priority === 'medium' ? '권장' : '참고'}
                        </div>
                        <div className="rec-content">
                          <div className="rec-action">{rec.action}</div>
                          <div className="rec-reason">{rec.reason}</div>
                        </div>
                        <button className="rec-apply">적용</button>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 리스크 요인 */}
                {selectedCustomer.riskFactors.length > 0 && (
                  <div className="risk-factors-card">
                    <h3 className="section-title">
                      <span className="title-icon">⚠️</span>
                      주의 사항
                    </h3>
                    <div className="risk-list">
                      {selectedCustomer.riskFactors.map((risk, index) => (
                        <div key={index} className="risk-item">
                          <span className="risk-bullet">•</span>
                          <span className="risk-text">{risk}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Alerts Sidebar */}
          <div className="panel alerts-panel">
            <div className="panel-header">
              <h2 className="panel-title">실시간 알림</h2>
              <div className="alert-filters">
                <button className="filter-btn active">전체</button>
                <button className="filter-btn critical">긴급</button>
                <button className="filter-btn">일반</button>
              </div>
            </div>
            
            <div className="alerts-list">
              {alerts.map(alert => (
                <div key={alert.id} className={`alert-item ${alert.type}`}>
                  <div className="alert-header">
                    <span className="alert-icon">
                      {alert.type === 'critical' ? '🚨' : alert.type === 'warning' ? '⚠️' : 'ℹ️'}
                    </span>
                    <span className="alert-customer">{alert.customerId}</span>
                    <span className="alert-time">{formatTime(alert.time)}</span>
                  </div>
                  <div className="alert-message">{alert.message}</div>
                  {alert.type === 'critical' && (
                    <button className="alert-action">즉시 대응</button>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;