import React, { useState, useEffect } from 'react';
import './App.css';

interface CustomerData {
  id: string;
  name: string;
  currentSection: string;
  emotionState: string;
  comprehensionLevel: number;
  startTime: Date;
  focusAreas: string[];
  confusedSections: string[];
  readingSpeed: number;
  attentionScore: number;
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
      currentSection: '이자율 및 우대조건',
      emotionState: 'confused',
      comprehensionLevel: 65,
      startTime: new Date(Date.now() - 300000),
      focusAreas: ['상품 개요', '이자율'],
      confusedSections: ['중도해지 불이익'],
      readingSpeed: 180,
      attentionScore: 78
    },
    {
      id: '2',
      name: '이서연',
      currentSection: '상품 개요',
      emotionState: 'focused',
      comprehensionLevel: 88,
      startTime: new Date(Date.now() - 180000),
      focusAreas: ['상품 개요'],
      confusedSections: [],
      readingSpeed: 220,
      attentionScore: 92
    }
  ]);
  
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerData | null>(customers[0]);
  const [alerts, setAlerts] = useState<Array<{ id: string; message: string; type: string; time: Date }>>([]);
  
  const [metrics] = useState<MetricData[]>([
    { label: '활성 고객', value: 12, change: 3, trend: 'up' },
    { label: '평균 이해도', value: 76, change: -2, trend: 'down' },
    { label: '상담 완료율', value: 89, change: 5, trend: 'up' },
    { label: '고객 만족도', value: 94, change: 0, trend: 'stable' }
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCustomers(prev => prev.map(customer => ({
        ...customer,
        comprehensionLevel: Math.max(0, Math.min(100, customer.comprehensionLevel + (Math.random() - 0.5) * 10)),
        emotionState: ['neutral', 'focused', 'confused', 'stressed'][Math.floor(Math.random() * 4)],
        attentionScore: Math.max(0, Math.min(100, customer.attentionScore + (Math.random() - 0.5) * 8))
      })));
      
      if (Math.random() > 0.7) {
        const messages = [
          '김민수 고객님이 중도해지 조항에서 어려움을 겪고 있습니다',
          '이서연 고객님이 우대이자율 조건을 꼼꼼히 읽고 있습니다',
          '새로운 고객이 상담을 시작했습니다'
        ];
        const newAlert = {
          id: Date.now().toString(),
          message: messages[Math.floor(Math.random() * messages.length)],
          type: Math.random() > 0.5 ? 'warning' : 'info',
          time: new Date()
        };
        setAlerts(prev => [newAlert, ...prev].slice(0, 5));
      }
    }, 3000);

    return () => clearInterval(interval);
  }, []);

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

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-brand">
          <div className="logo">
            <span className="logo-nh">NH</span>
            <span className="logo-bank">Bank</span>
          </div>
          <h1 className="dashboard-title">상담 관리 시스템</h1>
        </div>
        
        <div className="header-nav">
          <button className="nav-item active">대시보드</button>
          <button className="nav-item">고객 관리</button>
          <button className="nav-item">분석 리포트</button>
          <button className="nav-item">설정</button>
        </div>
        
        <div className="header-user">
          <span className="notifications">
            <span className="notification-icon">🔔</span>
            <span className="notification-count">{alerts.length}</span>
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
                  {Math.abs(metric.change)}%
                </span>
              </div>
              <div className="metric-value">{metric.value}</div>
              <div className="metric-bar">
                <div className="metric-fill" style={{ width: `${metric.value}%` }}></div>
              </div>
            </div>
          ))}
        </div>

        <div className="dashboard-grid">
          {/* Customer List */}
          <div className="panel customer-panel">
            <div className="panel-header">
              <h2 className="panel-title">실시간 상담 현황</h2>
              <span className="panel-badge">{customers.length}명 상담중</span>
            </div>
            
            <div className="customer-list">
              {customers.map(customer => (
                <div 
                  key={customer.id}
                  className={`customer-item ${selectedCustomer?.id === customer.id ? 'selected' : ''}`}
                  onClick={() => setSelectedCustomer(customer)}
                >
                  <div className="customer-avatar">
                    {customer.name.substring(0, 2)}
                  </div>
                  
                  <div className="customer-details">
                    <div className="customer-name">{customer.name}</div>
                    <div className="customer-meta">
                      <span className="meta-item">{customer.currentSection}</span>
                      <span className="meta-divider">•</span>
                      <span className="meta-item">{getDuration(customer.startTime)}</span>
                    </div>
                  </div>
                  
                  <div className="customer-status">
                    <div className="emotion-badge">
                      {getEmotionIcon(customer.emotionState)}
                    </div>
                    <div className={`comprehension-indicator level-${Math.floor(customer.comprehensionLevel / 20)}`}>
                      {customer.comprehensionLevel}%
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Customer Detail */}
          {selectedCustomer && (
            <div className="panel detail-panel">
              <div className="panel-header">
                <h2 className="panel-title">{selectedCustomer.name} 고객님 상세 분석</h2>
                <button className="action-button">상담 지원</button>
              </div>
              
              <div className="detail-grid">
                {/* Real-time Status */}
                <div className="detail-card">
                  <h3 className="detail-title">실시간 상태</h3>
                  <div className="status-grid">
                    <div className="status-item">
                      <span className="status-icon">{getEmotionIcon(selectedCustomer.emotionState)}</span>
                      <div className="status-info">
                        <span className="status-label">감정 상태</span>
                        <span className="status-value">{getEmotionLabel(selectedCustomer.emotionState)}</span>
                      </div>
                    </div>
                    
                    <div className="status-item">
                      <span className="status-icon">📖</span>
                      <div className="status-info">
                        <span className="status-label">읽기 속도</span>
                        <span className="status-value">{selectedCustomer.readingSpeed} 단어/분</span>
                      </div>
                    </div>
                    
                    <div className="status-item">
                      <span className="status-icon">👁️</span>
                      <div className="status-info">
                        <span className="status-label">주의 집중도</span>
                        <span className="status-value">{selectedCustomer.attentionScore}%</span>
                      </div>
                    </div>
                    
                    <div className="status-item">
                      <span className="status-icon">🎯</span>
                      <div className="status-info">
                        <span className="status-label">이해도</span>
                        <span className="status-value">{selectedCustomer.comprehensionLevel}%</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Comprehension Chart */}
                <div className="detail-card">
                  <h3 className="detail-title">이해도 분석</h3>
                  <div className="comprehension-chart">
                    <div className="chart-circle">
                      <svg width="120" height="120">
                        <circle cx="60" cy="60" r="50" fill="none" stroke="#e0e0e0" strokeWidth="10" />
                        <circle 
                          cx="60" cy="60" r="50" 
                          fill="none" 
                          stroke="#00A651" 
                          strokeWidth="10"
                          strokeDasharray={`${selectedCustomer.comprehensionLevel * 3.14} 314`}
                          strokeLinecap="round"
                          transform="rotate(-90 60 60)"
                        />
                      </svg>
                      <div className="chart-value">{selectedCustomer.comprehensionLevel}%</div>
                    </div>
                    <div className="chart-legend">
                      <div className="legend-item">
                        <span className="legend-dot" style={{ background: '#00A651' }}></span>
                        <span>현재 이해도</span>
                      </div>
                      <div className="legend-item">
                        <span className="legend-dot" style={{ background: '#e0e0e0' }}></span>
                        <span>목표 이해도</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Focus Areas */}
                <div className="detail-card">
                  <h3 className="detail-title">집중 구역</h3>
                  <div className="tag-list">
                    {selectedCustomer.focusAreas.map((area, index) => (
                      <span key={index} className="tag tag-success">{area}</span>
                    ))}
                  </div>
                </div>

                {/* Confusion Areas */}
                <div className="detail-card">
                  <h3 className="detail-title">주의 필요 구역</h3>
                  <div className="tag-list">
                    {selectedCustomer.confusedSections.length > 0 ? (
                      selectedCustomer.confusedSections.map((section, index) => (
                        <span key={index} className="tag tag-warning">{section}</span>
                      ))
                    ) : (
                      <span className="empty-state">주의가 필요한 구역이 없습니다</span>
                    )}
                  </div>
                </div>

                {/* Recommendations */}
                <div className="detail-card full-width">
                  <h3 className="detail-title">AI 추천 상담 가이드</h3>
                  <div className="recommendations">
                    <div className="recommendation">
                      <span className="rec-icon">💡</span>
                      <div className="rec-content">
                        <strong>중도해지 수수료 설명 필요</strong>
                        <p>고객이 중도해지 관련 조항을 3번 이상 반복해서 읽고 있습니다. 구체적인 예시를 들어 설명해주세요.</p>
                      </div>
                    </div>
                    <div className="recommendation">
                      <span className="rec-icon">📊</span>
                      <div className="rec-content">
                        <strong>이자율 계산 시뮬레이션 제공</strong>
                        <p>우대이자율 조건에 대한 관심이 높습니다. 계산기를 활용한 시뮬레이션을 보여주세요.</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Alerts Sidebar */}
          <div className="panel alerts-panel">
            <div className="panel-header">
              <h2 className="panel-title">실시간 알림</h2>
              <button className="clear-btn">모두 지우기</button>
            </div>
            
            <div className="alerts-list">
              {alerts.length > 0 ? (
                alerts.map(alert => (
                  <div key={alert.id} className={`alert-item ${alert.type}`}>
                    <span className="alert-icon">
                      {alert.type === 'warning' ? '⚠️' : 'ℹ️'}
                    </span>
                    <div className="alert-content">
                      <p className="alert-message">{alert.message}</p>
                      <span className="alert-time">{formatTime(alert.time)}</span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="empty-state">새로운 알림이 없습니다</div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;