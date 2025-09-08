import React, { useState, useEffect } from 'react';
import './EmotionRecognition.css';

interface EmotionRecognitionProps {
  isTracking: boolean;
  onEmotionData?: (data: EmotionData) => void;
}

interface EmotionData {
  emotion: string;
  confidence: number;
  timestamp: number;
  details: {
    neutral: number;
    happy: number;
    sad: number;
    angry: number;
    fearful: number;
    disgusted: number;
    surprised: number;
    confused: number;
  };
}

const EmotionRecognition: React.FC<EmotionRecognitionProps> = ({ isTracking, onEmotionData }) => {
  const [currentEmotion, setCurrentEmotion] = useState<string>('neutral');
  const [emotionHistory, setEmotionHistory] = useState<Array<{ emotion: string; timestamp: Date }>>([]);
  const [emotionScores, setEmotionScores] = useState({
    neutral: 0,
    happy: 0,
    confused: 0,
    focused: 0,
    stressed: 0
  });

  useEffect(() => {
    if (isTracking) {
      // 감정 인식 시뮬레이션
      const interval = setInterval(() => {
        const emotions = ['neutral', 'focused', 'confused', 'stressed', 'happy'];
        const weights = [0.4, 0.3, 0.15, 0.1, 0.05]; // 가중치
        
        // 가중치 기반 랜덤 감정 선택
        const random = Math.random();
        let cumulative = 0;
        let selectedEmotion = 'neutral';
        
        for (let i = 0; i < emotions.length; i++) {
          cumulative += weights[i];
          if (random < cumulative) {
            selectedEmotion = emotions[i];
            break;
          }
        }
        
        // 감정 스코어 업데이트
        const newScores = {
          neutral: selectedEmotion === 'neutral' ? 0.7 + Math.random() * 0.3 : Math.random() * 0.3,
          happy: selectedEmotion === 'happy' ? 0.6 + Math.random() * 0.4 : Math.random() * 0.2,
          confused: selectedEmotion === 'confused' ? 0.7 + Math.random() * 0.3 : Math.random() * 0.2,
          focused: selectedEmotion === 'focused' ? 0.8 + Math.random() * 0.2 : Math.random() * 0.3,
          stressed: selectedEmotion === 'stressed' ? 0.6 + Math.random() * 0.4 : Math.random() * 0.2
        };
        
        setCurrentEmotion(selectedEmotion);
        setEmotionScores(newScores);
        
        // 히스토리 업데이트
        setEmotionHistory(prev => [...prev.slice(-9), {
          emotion: selectedEmotion,
          timestamp: new Date()
        }]);
        
        if (onEmotionData) {
          onEmotionData({
            emotion: selectedEmotion,
            confidence: Math.max(...Object.values(newScores)),
            timestamp: Date.now(),
            details: {
              neutral: newScores.neutral,
              happy: newScores.happy,
              sad: 0,
              angry: 0,
              fearful: 0,
              disgusted: 0,
              surprised: 0,
              confused: newScores.confused
            }
          });
        }
      }, 2000);

      return () => clearInterval(interval);
    } else {
      setCurrentEmotion('neutral');
      setEmotionHistory([]);
    }
  }, [isTracking, onEmotionData]);

  const getEmotionIcon = (emotion: string) => {
    const icons: { [key: string]: string } = {
      neutral: '😐',
      happy: '😊',
      confused: '😕',
      focused: '🧐',
      stressed: '😰'
    };
    return icons[emotion] || '😐';
  };

  const getEmotionColor = (emotion: string) => {
    const colors: { [key: string]: string } = {
      neutral: '#6c757d',
      happy: '#28a745',
      confused: '#ffc107',
      focused: '#007bff',
      stressed: '#dc3545'
    };
    return colors[emotion] || '#6c757d';
  };

  const getEmotionMessage = (emotion: string) => {
    const messages: { [key: string]: string } = {
      neutral: '평온한 상태입니다',
      happy: '긍정적인 반응을 보이고 있습니다',
      confused: '이해가 어려운 부분이 있는 것 같습니다',
      focused: '집중하여 읽고 계십니다',
      stressed: '부담을 느끼고 계신 것 같습니다'
    };
    return messages[emotion] || '감정을 분석 중입니다';
  };

  return (
    <div className="emotion-recognition-container">
      <h3 className="emotion-title">표정 인식 분석</h3>
      
      {/* 현재 감정 상태 */}
      <div className="current-emotion">
        <div className="emotion-display">
          <div className="emotion-icon" style={{ color: getEmotionColor(currentEmotion) }}>
            {getEmotionIcon(currentEmotion)}
          </div>
          <div className="emotion-info">
            <span className="emotion-label">{currentEmotion.toUpperCase()}</span>
            <span className="emotion-message">{getEmotionMessage(currentEmotion)}</span>
          </div>
        </div>
      </div>

      {/* 감정 스코어 바 */}
      <div className="emotion-scores">
        {Object.entries(emotionScores).map(([emotion, score]) => (
          <div key={emotion} className="score-item">
            <div className="score-header">
              <span className="score-label">{emotion}</span>
              <span className="score-value">{Math.round(score * 100)}%</span>
            </div>
            <div className="score-bar">
              <div 
                className="score-fill" 
                style={{ 
                  width: `${score * 100}%`,
                  backgroundColor: getEmotionColor(emotion)
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* 감정 히스토리 */}
      <div className="emotion-history">
        <h4>최근 감정 변화</h4>
        <div className="history-timeline">
          {emotionHistory.length > 0 ? (
            emotionHistory.map((item, index) => (
              <div key={index} className="history-item">
                <span 
                  className="history-icon" 
                  style={{ color: getEmotionColor(item.emotion) }}
                >
                  {getEmotionIcon(item.emotion)}
                </span>
                <span className="history-time">
                  {item.timestamp.toLocaleTimeString('ko-KR', { 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                  })}
                </span>
              </div>
            ))
          ) : (
            <div className="history-empty">
              추적을 시작하면 감정 변화가 표시됩니다
            </div>
          )}
        </div>
      </div>

      {/* 분석 인사이트 */}
      {isTracking && (
        <div className="emotion-insights">
          <h4>분석 인사이트</h4>
          <div className="insights-content">
            {currentEmotion === 'confused' && (
              <div className="insight-item warning">
                <span className="insight-icon">⚠️</span>
                <span>고객이 이해하기 어려워하는 부분이 있습니다. 추가 설명이 필요할 수 있습니다.</span>
              </div>
            )}
            {currentEmotion === 'stressed' && (
              <div className="insight-item alert">
                <span className="insight-icon">🔴</span>
                <span>고객이 부담을 느끼고 있습니다. 친근한 접근이 필요합니다.</span>
              </div>
            )}
            {currentEmotion === 'focused' && (
              <div className="insight-item info">
                <span className="insight-icon">✅</span>
                <span>고객이 집중하여 내용을 읽고 있습니다.</span>
              </div>
            )}
            {currentEmotion === 'happy' && (
              <div className="insight-item success">
                <span className="insight-icon">😊</span>
                <span>고객이 긍정적인 반응을 보이고 있습니다.</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default EmotionRecognition;