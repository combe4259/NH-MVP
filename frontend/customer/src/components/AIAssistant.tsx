import React, { useState, useEffect } from 'react';
import './AIAssistant.css';

interface AIAssistantProps {
  suggestion: {
    section: string;
    explanation: string;
    simpleExample?: string;
  };
  onDismiss: () => void;
  onRequestMore: (topic: string) => void;
}

const AIAssistant: React.FC<AIAssistantProps> = ({ suggestion, onDismiss, onRequestMore }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showAnimation, setShowAnimation] = useState(false);
  const [userFeedback, setUserFeedback] = useState<'helpful' | 'not-helpful' | null>(null);

  useEffect(() => {
    // 부드러운 등장 애니메이션
    setTimeout(() => setShowAnimation(true), 100);
  }, []);

  const handleFeedback = (feedback: 'helpful' | 'not-helpful') => {
    setUserFeedback(feedback);
    if (feedback === 'helpful') {
      setTimeout(() => onDismiss(), 1500);
    }
  };

  const quickQuestions = [
    "예시를 더 보여주세요",
    "다른 상품과 비교해주세요",
    "내 경우는 어떻게 되나요?",
    "더 간단히 설명해주세요"
  ];

  return (
    <div className={`ai-assistant ${showAnimation ? 'show' : ''}`}>
      {/* 미니 플로팅 버튼 형태 */}
      {!isExpanded && (
        <div className="ai-bubble" onClick={() => setIsExpanded(true)}>
          <div className="ai-avatar">
            <span className="ai-icon">🤖</span>
          </div>
          <div className="ai-message">
            <p className="ai-greeting">이 부분이 어려우신가요?</p>
            <p className="ai-section">{suggestion.section}</p>
          </div>
          <button className="expand-btn">
            자세히 보기
          </button>
        </div>
      )}

      {/* 확장된 설명 패널 */}
      {isExpanded && (
        <div className="ai-panel">
          <div className="panel-header">
            <div className="ai-identity">
              <span className="ai-avatar-small">🤖</span>
              <span className="ai-name">NH AI 도우미</span>
            </div>
            <button className="close-btn" onClick={onDismiss}>✕</button>
          </div>

          <div className="panel-content">
            {/* 원본 내용 */}
            <div className="original-content">
              <span className="label">원본 내용</span>
              <p className="original-text">{suggestion.section}</p>
            </div>

            {/* 쉬운 설명 */}
            <div className="simple-explanation">
              <span className="label">쉽게 풀어서 설명</span>
              <div className="explanation-box">
                <p>{suggestion.explanation}</p>
              </div>
            </div>

            {/* 실생활 예시 */}
            {suggestion.simpleExample && (
              <div className="example-section">
                <span className="label">실생활 예시</span>
                <div className="example-box">
                  <span className="example-icon">💡</span>
                  <p>{suggestion.simpleExample}</p>
                </div>
              </div>
            )}

            {/* 비주얼 설명 */}
            <div className="visual-explanation">
              <span className="label">한눈에 보기</span>
              <div className="visual-cards">
                <div className="visual-card">
                  <span className="card-emoji">📅</span>
                  <span className="card-label">만기일</span>
                  <span className="card-value">1년 후</span>
                </div>
                <div className="visual-card">
                  <span className="card-emoji">💰</span>
                  <span className="card-label">약정 이자</span>
                  <span className="card-value">4.0%</span>
                </div>
                <div className="visual-card warning">
                  <span className="card-emoji">⚠️</span>
                  <span className="card-label">중도해지시</span>
                  <span className="card-value">0.5%</span>
                </div>
              </div>
            </div>

            {/* 빠른 질문 */}
            <div className="quick-questions">
              <span className="label">추가 궁금증</span>
              <div className="question-chips">
                {quickQuestions.map((question, index) => (
                  <button 
                    key={index}
                    className="question-chip"
                    onClick={() => onRequestMore(question)}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
};

export default AIAssistant;