import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api';

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
  

  // 백엔드에서 데이터 가져오기
  const fetchCustomersData = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/staff/dashboard/overview`);
      const consultations = response.data.active_consultations;

      // 백엔드 데이터를 프론트엔드 형식에 맞게 변환
      const updatedCustomers = customers.map(customer => {
        const backendData = consultations.find((c: any) => c.customer_name === customer.name);
        if (backendData) {
          return {
            ...customer,
            comprehensionLevel: backendData.comprehension_level,
            currentSection: backendData.current_section,
            consultationPhase: backendData.consultation_phase || customer.consultationPhase,
            emotionState: backendData.emotion_state || customer.emotionState,
            attentionScore: backendData.attention_score || customer.attentionScore
          };
        }
        return customer;
      });

      setCustomers(updatedCustomers);
    } catch (error) {
      console.error('백엔드 데이터 가져오기 실패:', error);
      // 실패시 기존 랜덤 업데이트 로직 실행
      setCustomers(prev => prev.map(customer => ({
        ...customer,
        comprehensionLevel: Math.max(0, Math.min(100, customer.comprehensionLevel + (Math.random() - 0.5) * 10)),
        emotionState: ['neutral', 'focused', 'confused', 'stressed'][Math.floor(Math.random() * 4)] as any,
        attentionScore: Math.max(0, Math.min(100, customer.attentionScore + (Math.random() - 0.5) * 8))
      })));
    }
  };

  useEffect(() => {
    // 초기 데이터 로드
    fetchCustomersData();

    // 3초마다 업데이트
    const interval = setInterval(fetchCustomersData, 3000);

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
        
        
        <div className="header-user">
          <div className="user-info">
            <span className="user-name">김상담 매니저</span>
            <span className="user-role">디지털혁신점</span>
          </div>
          <div className="user-avatar">KS</div>
        </div>
      </header>

      {/* Main Content */}
      <main className="dashboard-main">

        <div className="dashboard-grid">
          {/* Product Information Panel */}
          {selectedCustomer && (
            <div className="panel product-panel">
              <div className="panel-header">
                <h2 className="panel-title">진행 중인 상품</h2>
              </div>
              
              <div className="product-detail-content">
                <div className="customer-info-header">
                  <div className="customer-avatar-large">
                    {selectedCustomer.name.substring(0, 2)}
                  </div>
                  <div className="customer-basic-info">
                    <h3 className="customer-name-large">{selectedCustomer.name}</h3>
                    <span className="customer-product-type">{selectedCustomer.productType}</span>
                  </div>
                </div>
                
                <div className="product-details-full">
                  <div className="product-name-full">{selectedCustomer.productDetails.name}</div>
                  <div className="product-specs-full">
                    <div className="spec-row">
                      <span className="spec-label">상품 유형</span>
                      <span className="spec-value">{selectedCustomer.productDetails.type}</span>
                    </div>
                    <div className="spec-row">
                      <span className="spec-label">가입 금액</span>
                      <span className="spec-value">{selectedCustomer.productDetails.amount}</span>
                    </div>
                    <div className="spec-row">
                      <span className="spec-label">가입 기간</span>
                      <span className="spec-value">{selectedCustomer.productDetails.period}</span>
                    </div>
                    <div className="spec-row">
                      <span className="spec-label">적용 금리</span>
                      <span className="spec-value highlight">{selectedCustomer.productDetails.interestRate}</span>
                    </div>
                  </div>
                </div>
                
                <div className="consultation-status">
                  <div className="status-header">
                    <span className="status-label">상담 단계</span>
                    <span className="status-phase">{getPhaseLabel(selectedCustomer.consultationPhase)}</span>
                  </div>
                  <div className="progress-bar-full">
                    <div className="progress-fill-full" style={{ width: `${getPhaseProgress(selectedCustomer.consultationPhase)}%` }}></div>
                  </div>
                  <div className="current-section">
                    <span className="section-label">현재 읽는 부분</span>
                    <span className="section-value">{selectedCustomer.currentSection}</span>
                  </div>
                </div>
              </div>
            </div>
          )}


          {/* Customer Detail - Center Panel */}
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
                {/* 이해도 분석 */}
                <div className="comprehension-analysis">
                  <h3 className="section-title">실시간 이해도 분석</h3>
                  <div className="circular-analysis">
                    <div className="circular-chart">
                      <svg className="progress-ring" width="200" height="200">
                        <circle
                          className="progress-ring-circle-bg"
                          stroke="#e0e0e0"
                          strokeWidth="12"
                          fill="transparent"
                          r="90"
                          cx="100"
                          cy="100"
                        />
                        <circle
                          className="progress-ring-circle"
                          stroke={selectedCustomer.comprehensionLevel < 50 ? '#f44336' : selectedCustomer.comprehensionLevel < 70 ? '#ff9800' : '#4caf50'}
                          strokeWidth="12"
                          fill="transparent"
                          r="90"
                          cx="100"
                          cy="100"
                          strokeDasharray={`${2 * Math.PI * 90}`}
                          strokeDashoffset={`${2 * Math.PI * 90 * (1 - selectedCustomer.comprehensionLevel / 100)}`}
                          strokeLinecap="round"
                          transform="rotate(-90 100 100)"
                        />
                      </svg>
                      <div className="chart-center">
                        <div className="emotion-display">
                          <div className="emotion-icon">{getEmotionIcon(selectedCustomer.emotionState)}</div>
                          <div className="emotion-label">{getEmotionLabel(selectedCustomer.emotionState)}</div>
                        </div>
                        <div className="comprehension-percentage">
                          {selectedCustomer.comprehensionLevel.toFixed(1)}%
                        </div>
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

                {/* 상담 진행 통계 */}
                <div className="consultation-stats-card">
                  <h3 className="section-title">
                    <span className="title-icon">📊</span>
                    상담 진행 통계
                  </h3>
                  <div className="stats-grid">
                    <div className="stat-card">
                      <div className="stat-icon">⏱️</div>
                      <div className="stat-content">
                        <div className="stat-value">{getDuration(selectedCustomer.startTime)}</div>
                        <div className="stat-label">상담 시간</div>
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-icon">📖</div>
                      <div className="stat-content">
                        <div className="stat-value">{selectedCustomer.readingSpeed}</div>
                        <div className="stat-label">읽기 속도 (단어/분)</div>
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-icon">👁️</div>
                      <div className="stat-content">
                        <div className="stat-value">{selectedCustomer.attentionScore.toFixed(1)}%</div>
                        <div className="stat-label">집중도</div>
                      </div>
                    </div>
                    <div className="stat-card">
                      <div className="stat-icon">🔄</div>
                      <div className="stat-content">
                        <div className="stat-value">{selectedCustomer.confusedSections.reduce((total, section) => total + section.returnCount, 0)}</div>
                        <div className="stat-label">반복 읽기 횟수</div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 상담 히스토리 */}
                <div className="consultation-history-card">
                  <h3 className="section-title">
                    <span className="title-icon">📝</span>
                    상담 히스토리
                  </h3>
                  <div className="history-timeline">
                    <div className="timeline-item completed">
                      <div className="timeline-marker"></div>
                      <div className="timeline-content">
                        <div className="timeline-title">상품 소개 시작</div>
                        <div className="timeline-time">상담 시작</div>
                      </div>
                    </div>
                    <div className="timeline-item completed">
                      <div className="timeline-marker"></div>
                      <div className="timeline-content">
                        <div className="timeline-title">약관 확인 단계</div>
                        <div className="timeline-time">5분 후</div>
                      </div>
                    </div>
                    <div className="timeline-item active">
                      <div className="timeline-marker"></div>
                      <div className="timeline-content">
                        <div className="timeline-title">{selectedCustomer.currentSection}</div>
                        <div className="timeline-time">현재 진행 중</div>
                      </div>
                    </div>
                    <div className="timeline-item">
                      <div className="timeline-marker"></div>
                      <div className="timeline-content">
                        <div className="timeline-title">가입 신청</div>
                        <div className="timeline-time">예정</div>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* Related Products Panel - Right Side */}
          <div className="panel products-panel">
            <div className="panel-header">
              <h2 className="panel-title">관련 상품</h2>
              <div className="panel-controls">
                <select className="filter-select">
                  <option>전체 상품</option>
                  <option>정기예금</option>
                  <option>적금</option>
                  <option>펀드</option>
                </select>
              </div>
            </div>
            
            <div className="products-list">
              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">NH 행복드림 정기예금</h3>
                  <span className="product-type">정기예금</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">금리</span>
                    <span className="spec-value">연 4.0%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">기간</span>
                    <span className="spec-value">12개월</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">최소금액</span>
                    <span className="spec-value">100만원</span>
                  </div>
                </div>
                <div className="product-actions">
                  <button className="product-btn primary">상세보기</button>
                  <button className="product-btn">비교하기</button>
                </div>
              </div>

              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">NH 올원 적금</h3>
                  <span className="product-type">적금</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">금리</span>
                    <span className="spec-value">연 4.5%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">기간</span>
                    <span className="spec-value">24개월</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">월납입</span>
                    <span className="spec-value">50만원</span>
                  </div>
                </div>
                <div className="product-actions">
                  <button className="product-btn primary">상세보기</button>
                  <button className="product-btn">비교하기</button>
                </div>
              </div>

              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">NH-Amundi 글로벌 펀드</h3>
                  <span className="product-type">펀드</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">수익률</span>
                    <span className="spec-value">연 6.2%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">위험도</span>
                    <span className="spec-value">중간</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">최소투자</span>
                    <span className="spec-value">100만원</span>
                  </div>
                </div>
                <div className="product-actions">
                  <button className="product-btn primary">상세보기</button>
                  <button className="product-btn">비교하기</button>
                </div>
              </div>

              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">NH 스마트 적금</h3>
                  <span className="product-type">적금</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">금리</span>
                    <span className="spec-value">연 3.8%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">기간</span>
                    <span className="spec-value">12개월</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">월납입</span>
                    <span className="spec-value">30만원</span>
                  </div>
                </div>
                <div className="product-actions">
                  <button className="product-btn primary">상세보기</button>
                  <button className="product-btn">비교하기</button>
                </div>
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

export default App;