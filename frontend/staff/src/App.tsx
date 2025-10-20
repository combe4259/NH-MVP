import { useState, useEffect, useCallback } from 'react';
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
      productType: 'ELS(주가연계증권)',
      productDetails: {
        name: 'N2 ELS 제44회 파생결합증권(주가연계증권)',
        type: 'ELS',
        amount: '10,000,000원',
        period: '3년',
        interestRate: '변동수익'
      },
      consultationPhase: 'terms_reading',
      currentSection: '원금손실 조건',
      emotionState: 'confused',
      comprehensionLevel: 65,
      startTime: new Date(Date.now() - 300000),
      focusAreas: ['기초자산', '수익률'],
      confusedSections: [
        { section: '원금손실(손실률)은 만기평가가격이 최초기준가격 대비 가장 낮은 기초자산의 하락률만큼 발생합니다.', duration: 45, returnCount: 3 },
        { section: '세 개의 기초자산 중 어느 하나라도 최초기준가격의 50% 미만인 경우 원금손실이 발생합니다.', duration: 30, returnCount: 2 }
      ],
      readingSpeed: 180,
      attentionScore: 78,
      riskFactors: ['원금손실 조건 미이해', '기초자산 변동성'],
      recommendations: [
        { priority: 'high', action: '원금 손실 조건 명확히 설명', reason: '가장 실적이 저조한 기초자산 하나로 손실이 결정됨을 강조' },
        { priority: 'medium', action: '기초자산 예시(KOSPI, HSCEI 등)를 들어 시나리오 설명', reason: '두 개가 올라도 하나가 크게 하락 시 손실 발생 가능성 안내' },
        { priority: 'low', action: '기초자산, 최초기준가격 등 용어 설명 준비', reason: '고객이 관련 용어에 생소함을 보임' }
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
  const fetchCustomersData = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/staff/dashboard/overview`);
      const consultations = response.data.active_consultations;

      // 백엔드 데이터를 프론트엔드 형식에 맞게 변환
      setCustomers(currentCustomers => currentCustomers.map(customer => {
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
      }));
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
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setCustomers(prevCustomers => {
        const updatedCustomers = prevCustomers.map(customer => {
          if (customer.id === '1') { // 김민수 고객만 업데이트
            let newComprehensionLevel = customer.comprehensionLevel + (Math.random() - 0.5) * 4;
            newComprehensionLevel = Math.max(5, Math.min(25, newComprehensionLevel));

            let newEmotionState: 'focused' | 'confused' | 'stressed' | 'neutral';
            if (newComprehensionLevel < 40) {
              newEmotionState = 'confused';
            } else if (newComprehensionLevel < 60) {
              newEmotionState = 'confused';
            } else if (newComprehensionLevel < 80) {
              newEmotionState = 'neutral';
            } else {
              newEmotionState = 'focused';
            }
            
            return {
              ...customer,
              comprehensionLevel: newComprehensionLevel,
              emotionState: newEmotionState,
              attentionScore: 75 + Math.cos(Date.now() / 2500) * 20, // 55% ~ 95%
              readingSpeed: 200 + Math.sin(Date.now() / 3000) * 50, // 150 ~ 250
            };
          }
          return customer;
        });

        // selectedCustomer도 업데이트
        const updatedSelectedCustomer = updatedCustomers.find(c => c.id === selectedCustomer?.id);
        if (updatedSelectedCustomer) {
          setSelectedCustomer(updatedSelectedCustomer);
        }

        return updatedCustomers;
      });
    }, 500); // 0.5초마다 업데이트

    return () => clearInterval(interval);
  }, [selectedCustomer?.id]);

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
                  <div className="customer-avatar-large" style={{ backgroundColor: '#00A651' }}>
                    {selectedCustomer.name}
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
                      <svg className="progress-ring" width="180" height="180">
                        <circle
                          className="progress-ring-circle-bg"
                          stroke="#e0e0e0"
                          strokeWidth="10"
                          fill="transparent"
                          r="80"
                          cx="90"
                          cy="90"
                        />
                        <circle
                          className="progress-ring-circle"
                          stroke={selectedCustomer.comprehensionLevel < 50 ? '#f44336' : selectedCustomer.comprehensionLevel < 70 ? '#ff9800' : '#4caf50'}
                          strokeWidth="10"
                          fill="transparent"
                          r="80"
                          cx="90"
                          cy="90"
                          strokeDasharray={`${2 * Math.PI * 80}`}
                          strokeDashoffset={`${2 * Math.PI * 80 * (1 - selectedCustomer.comprehensionLevel / 100)}`}
                          strokeLinecap="round"
                          transform="rotate(-90 90 90)"
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
                      집중 필요 구역
                    </h3>
                    <div className="confused-list">
                      {selectedCustomer.confusedSections.map((section, index) => (
                        <div key={index} className="confused-item-detail">
                          <div className="confused-header">
                            <span className="confused-title">{section.section}</span>
                          </div>
                          <div className="confused-stats">
                            <span className="stat">
                              {index === 0 
                                ? `해당 문장 10초 이상 체류, ${section.returnCount}회 반복 읽음`
                                : `표정 분석 시 이해도 하락 보임, 15초 이상 체류`
                              }
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI 상담 가이드 */}
                <div className="ai-guide-card">
                  <h3 className="section-title">
                    AI 상담 가이드
                  </h3>
                  <div className="ai-guide-list">
                    <div className="ai-guide-item">
                      <span className="guide-priority" style={{ backgroundColor: '#ff4444', color: 'white' }}>긴급</span>
                      <div className="guide-content">
                        <div className="guide-title">원금 손실 조건 명확히 설명</div>
                        <div className="guide-reason">가장 실적이 저조한 기초자산 하나로 손실이 결정됨을 강조</div>
                      </div>
                    </div>
                    <div className="ai-guide-item">
                      <span className="guide-priority" style={{ backgroundColor: '#ff9800', color: 'white' }}>권장</span>
                      <div className="guide-content">
                        <div className="guide-title">기초자산 예시(KOSPI, HSCEI 등)를 들어 시나리오 설명</div>
                        <div className="guide-reason">두 개가 올라도 하나가 크게 하락 시 손실 발생 가능성 안내</div>
                      </div>
                    </div>
                    <div className="ai-guide-item">
                      <span className="guide-priority" style={{ backgroundColor: '#4caf50', color: 'white' }}>참고</span>
                      <div className="guide-content">
                        <div className="guide-title">기초자산, 최초기준가격 등 용어 설명 준비</div>
                        <div className="guide-reason">고객이 관련 용어에 생소함을 보임</div>
                      </div>
                    </div>
                  </div>
                </div>



                {/* 상담 진행 통계 */}
                <div className="consultation-stats-card">
                  <h3 className="section-title">
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
                  <option>ELS</option>
                  <option>ELB</option>
                  <option>기타</option>
                </select>
              </div>
            </div>
            
            <div className="products-list">
              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">N2 ELS 제58회</h3>
                  <span className="product-type">ELS (Step-Down)</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">기초자산</span>
                    <span className="spec-value">Tesla, Palantir</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">최대수익률</span>
                    <span className="spec-value highlight">연 23.80%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">상환조건</span>
                    <span className="spec-value">80-80-75-75-70-65 / KI 35</span>
                  </div>
                </div>
                <div className="product-actions">
                  <button className="product-btn primary">상세보기</button>
                  <button className="product-btn">비교하기</button>
                </div>
              </div>

              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">N2 ELS 제51회</h3>
                  <span className="product-type">ELS (월지급식)</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">기초자산</span>
                    <span className="spec-value">SK이노베이션, 삼성SDI</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">최대수익률</span>
                    <span className="spec-value highlight">연 14.31%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">상환조건</span>
                    <span className="spec-value">90-90-85-80-75-65 / KI 40</span>
                  </div>
                </div>
                <div className="product-actions">
                  <button className="product-btn primary">상세보기</button>
                  <button className="product-btn">비교하기</button>
                </div>
              </div>

              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">N2 ELS 제55회</h3>
                  <span className="product-type">ELS (Step-Down)</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">기초자산</span>
                    <span className="spec-value">한화에어로, KOSPI200</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">최대수익률</span>
                    <span className="spec-value highlight">연 16.60%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">상환조건</span>
                    <span className="spec-value">85-85-80-80-75-70 / KI 35</span>
                  </div>
                </div>
                <div className="product-actions">
                  <button className="product-btn primary">상세보기</button>
                  <button className="product-btn">비교하기</button>
                </div>
              </div>

              <div className="product-item">
                <div className="product-header">
                  <h3 className="product-name">N2 ELS 제57회</h3>
                  <span className="product-type">ELS (Step-Down)</span>
                </div>
                <div className="product-details">
                  <div className="product-spec">
                    <span className="spec-label">기초자산</span>
                    <span className="spec-value">Shopify, S&P500</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">최대수익률</span>
                    <span className="spec-value highlight">연 13.30%</span>
                  </div>
                  <div className="product-spec">
                    <span className="spec-label">상환조건</span>
                    <span className="spec-value">85-85-80-80-75-70 / KI 35</span>
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