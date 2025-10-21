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
  confusedSections: string[];  // 백엔드에서 온 confused_sections (문자열 배열)
  readingSpeed: number;
  attentionScore: number;
  riskFactors: string[];
  recommendations: string[];  // 백엔드에서 온 recommendations (문자열 배열)
  aiSimplifiedSections?: Array<{  // 백엔드에서 온 AI 간소화 섹션들
    section_name: string;
    ai_explanation: string;
    confusion_probability: number;
  }>;
}


function App() {
  const [customers, setCustomers] = useState<CustomerData[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<CustomerData | null>(null);
  const [consultationId, setConsultationId] = useState<string>('');  // 백엔드에서 받아올 consultation_id
  

  // 백엔드에서 상담 목록 가져오기
  const fetchConsultations = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/consultations?status=active&limit=20`);
      const consultations = response.data.consultations;

      if (consultations && consultations.length > 0) {
        // 첫 번째 상담의 ID 저장
        const firstConsultationId = consultations[0].consultation_id;
        setConsultationId(firstConsultationId);

        // 각 상담에 대한 리포트 가져오기
        const customersData = await Promise.all(
          consultations.map(async (consultation: any) => {
            try {
              const reportResponse = await axios.get(
                `${API_BASE_URL}/consultations/${consultation.consultation_id}/report`
              );
              const report = reportResponse.data;

              return {
                id: consultation.consultation_id,
                name: consultation.customer_name,
                productType: consultation.product_type,
                productDetails: {
                  name: consultation.product_details?.name || consultation.product_type,
                  type: consultation.product_type,
                  amount: consultation.product_details?.amount || '',
                  period: consultation.product_details?.period || '',
                  interestRate: consultation.product_details?.interest_rate || ''
                },
                consultationPhase: consultation.consultation_phase || 'terms_reading',
                currentSection: consultation.product_details?.current_section || '약관 확인',
                emotionState: 'neutral',
                comprehensionLevel: report.comprehension_summary?.low
                  ? (100 - (report.comprehension_summary.low / report.total_sections_analyzed * 100))
                  : 70,
                startTime: new Date(consultation.start_time),
                focusAreas: [],
                confusedSections: report.confused_sections || [],
                readingSpeed: 180,
                attentionScore: 75,
                riskFactors: [],
                recommendations: report.recommendations || [],
                aiSimplifiedSections: report.detailed_info?.ai_simplified_sections || []
              };
            } catch (err) {
              console.error(`리포트 가져오기 실패 (${consultation.consultation_id}):`, err);
              return null;
            }
          })
        );

        const validCustomers = customersData.filter(c => c !== null) as CustomerData[];
        setCustomers(validCustomers);

        if (validCustomers.length > 0 && !selectedCustomer) {
          setSelectedCustomer(validCustomers[0]);
        }
      }
    } catch (error) {
      console.error('상담 목록 가져오기 실패:', error);
    }
  }, [selectedCustomer]);

  // 컴포넌트 마운트 시 데이터 가져오기
  useEffect(() => {
    fetchConsultations();

    // 5초마다 데이터 갱신
    const interval = setInterval(() => {
      fetchConsultations();
    }, 5000);

    return () => clearInterval(interval);
  }, []);  // 빈 배열로 변경 - 마운트 시 한 번만 실행

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

                {/* 집중 필요 구역 - 백엔드 연결 */}
                {selectedCustomer.confusedSections && selectedCustomer.confusedSections.length > 0 && (
                  <div className="confused-sections-card">
                    <h3 className="section-title">
                      집중 필요 구역
                    </h3>
                    <div className="confused-list">
                      {selectedCustomer.confusedSections.map((section, index) => (
                        <div key={index} className="confused-item-detail">
                          <div className="confused-header">
                            <span className="confused-title">{section}</span>
                          </div>
                          <div className="confused-stats">
                            <span className="stat">
                              고객이 이해하지 못한 섹션입니다. 추가 설명이 필요합니다.
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* AI 상담 가이드 - 백엔드 연결 */}
                <div className="ai-guide-card">
                  <h3 className="section-title">
                    AI 상담 가이드
                  </h3>
                  <div className="ai-guide-list">
                    {/* AI 간소화 섹션 표시 */}
                    {selectedCustomer.aiSimplifiedSections && selectedCustomer.aiSimplifiedSections.length > 0 ? (
                      selectedCustomer.aiSimplifiedSections.map((section, index) => {
                        const priority = section.confusion_probability > 0.7 ? 'high' : section.confusion_probability > 0.4 ? 'medium' : 'low';
                        const priorityLabel = priority === 'high' ? '긴급' : priority === 'medium' ? '권장' : '참고';
                        const priorityColor = priority === 'high' ? '#ff4444' : priority === 'medium' ? '#ff9800' : '#4caf50';

                        return (
                          <div key={index} className="ai-guide-item">
                            <span className="guide-priority" style={{ backgroundColor: priorityColor, color: 'white' }}>
                              {priorityLabel}
                            </span>
                            <div className="guide-content">
                              <div className="guide-title">{section.section_name}</div>
                              <div className="guide-reason" style={{ whiteSpace: 'pre-line', marginTop: '8px' }}>
                                {section.ai_explanation}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      /* 추천사항 표시 (AI 간소화가 없을 때) */
                      selectedCustomer.recommendations && selectedCustomer.recommendations.length > 0 ? (
                        selectedCustomer.recommendations.map((recommendation, index) => (
                          <div key={index} className="ai-guide-item">
                            <span className="guide-priority" style={{ backgroundColor: '#00A651', color: 'white' }}>추천</span>
                            <div className="guide-content">
                              <div className="guide-reason">{recommendation}</div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="ai-guide-item">
                          <span className="guide-priority" style={{ backgroundColor: '#4caf50', color: 'white' }}>정상</span>
                          <div className="guide-content">
                            <div className="guide-reason">상담이 원활하게 진행되고 있습니다.</div>
                          </div>
                        </div>
                      )
                    )}
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
                        <div className="stat-value">{selectedCustomer.confusedSections?.length || 0}</div>
                        <div className="stat-label">혼란 섹션 수</div>
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