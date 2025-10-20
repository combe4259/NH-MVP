import React, { useState, useEffect, useRef, useLayoutEffect } from 'react';
import ReactDOM from 'react-dom';
import './AIAssistant.css';

interface AIAssistantProps {
  suggestion: {
    section: string;
    explanation: string;
    simpleExample?: string;
  } | null;
  onDismiss: () => void;
  onRequestMore?: (topic: string) => void;
}

const AIAssistant: React.FC<AIAssistantProps> = ({ suggestion, onDismiss, onRequestMore = () => {} }) => {
  const [mounted, setMounted] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showAnimation, setShowAnimation] = useState(false);
  const [userFeedback, setUserFeedback] = useState<'helpful' | 'not-helpful' | null>(null);
  const portalRoot = useRef<HTMLElement | null>(null);

  useLayoutEffect(() => {
    portalRoot.current = document.getElementById('ai-portal');
    setMounted(true);
    
    if (suggestion) {
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      document.body.style.overflow = '';
    };
  }, [suggestion]);

  useEffect(() => {
    if (suggestion) {
      setTimeout(() => setShowAnimation(true), 100);
    }
  }, [suggestion]);

  if (!mounted || !portalRoot.current || !suggestion) {
    return null;
  }

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

  return ReactDOM.createPortal(
    <div className={`ai-assistant ${showAnimation ? 'show' : ''}`}>
      {!isExpanded && (
        <div className="ai-bubble" onClick={() => setIsExpanded(true)}>
          <div className="ai-avatar">
            <span className="ai-icon"></span>
          </div>
          <div className="ai-message">
            <p className="ai-greeting">이 부분이 어려우신가요?</p>
            <p className="ai-section">{suggestion.section}</p>
          </div>
          <button className="expand-btn">자세히 보기</button>
        </div>
      )}

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
            <div className="original-content">
              <span className="label">원본 내용</span>
              <p className="original-text">{suggestion.section}</p>
            </div>

            <div className="simple-explanation">
              <span className="label">쉽게 풀어서 설명</span>
              <div className="explanation-box">
                <p>{suggestion.explanation}</p>
              </div>
            </div>

            {suggestion.simpleExample && (
              <div className="example-section">
                <span className="label">실생활 예시</span>
                <div className="example-box">
                  <span className="example-icon"></span>
                  <p>{suggestion.simpleExample}</p>
                </div>
              </div>
            )}

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
    </div>,
    portalRoot.current
  );
};

export default AIAssistant;