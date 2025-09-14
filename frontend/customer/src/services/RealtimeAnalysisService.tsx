/**
 * 실시간 AI 분석 서비스
 * WebSocket을 통한 아이트래킹 + 얼굴인식 + 텍스트 난이도 분석
 */

import { useEffect, useRef, useState, useCallback } from 'react';

interface AnalysisResult {
  difficultyScore: number;
  confusedSections: any[];
  faceConfusion: boolean;
  confusionProbability: number;
  aiExplanation: string;
  needsAiAssistance: boolean;
}

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export class RealtimeAnalysisService {
  private ws: WebSocket | null = null;
  private consultationId: string;
  private onAnalysisUpdate: (result: AnalysisResult) => void;
  private videoRef: React.RefObject<HTMLVideoElement | null> | null = null;
  private frameInterval: NodeJS.Timer | null = null;

  constructor(
    consultationId: string,
    onAnalysisUpdate: (result: AnalysisResult) => void
  ) {
    this.consultationId = consultationId;
    this.onAnalysisUpdate = onAnalysisUpdate;
  }

  // WebSocket 연결
  connect() {
    const wsUrl = `ws://localhost:8000/ws/${this.consultationId}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket 연결 성공');
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket 오류:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket 연결 종료');
      this.stopHeartbeat();
      // 재연결 시도
      setTimeout(() => this.reconnect(), 3000);
    };
  }

  // 메시지 처리
  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'difficulty_analysis':
        // 텍스트 난이도 분석 결과
        this.onAnalysisUpdate({
          difficultyScore: message.difficulty_score,
          confusedSections: message.confused_sections,
          faceConfusion: false,
          confusionProbability: 0,
          aiExplanation: '',
          needsAiAssistance: message.difficulty_score > 0.7
        });
        break;

      case 'face_analysis':
        // 얼굴 혼란도 분석 결과
        this.onAnalysisUpdate({
          difficultyScore: 0,
          confusedSections: [],
          faceConfusion: message.confused,
          confusionProbability: message.confusion_probability,
          aiExplanation: '',
          needsAiAssistance: message.confused
        });
        break;

      case 'combined_analysis':
        // 통합 분석 결과
        this.onAnalysisUpdate({
          difficultyScore: message.difficulty_score,
          confusedSections: message.confused_sections || [],
          faceConfusion: message.face_analysis?.confused || false,
          confusionProbability: message.confusion_probability,
          aiExplanation: message.ai_explanation,
          needsAiAssistance: message.needs_ai_assistance
        });
        break;

      case 'ai_helper_trigger':
        // AI 도우미 트리거
        this.onAnalysisUpdate({
          difficultyScore: message.difficulty_score,
          confusedSections: message.confused_sections,
          faceConfusion: false,
          confusionProbability: 0,
          aiExplanation: message.explanation,
          needsAiAssistance: true
        });
        break;
    }
  }

  // 텍스트 분석 요청
  analyzeText(sectionText: string, readingTime: number) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'eyetracking',
        section_text: sectionText,
        reading_time: readingTime,
        gaze_data: {},
        timestamp: new Date().toISOString()
      }));
    }
  }

  // 얼굴 프레임 전송 (웹캠 사용)
  startFaceTracking(videoRef: React.RefObject<HTMLVideoElement | null>) {
    this.videoRef = videoRef;
    
    // 웹캠 시작
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      })
      .catch(err => console.error('웹캠 접근 오류:', err));

    // 주기적으로 프레임 캡처 및 전송
    this.frameInterval = setInterval(() => {
      this.captureAndSendFrame();
    }, 1000); // 1초마다
  }

  // 프레임 캡처 및 전송
  private captureAndSendFrame() {
    if (!this.videoRef?.current || this.ws?.readyState !== WebSocket.OPEN) {
      return;
    }

    const video = this.videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0);
      
      // base64로 인코딩
      canvas.toBlob((blob) => {
        if (blob) {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result?.toString().split(',')[1];
            if (base64) {
              this.ws?.send(JSON.stringify({
                type: 'face_frame',
                frame: base64,
                timestamp: new Date().toISOString()
              }));
            }
          };
          reader.readAsDataURL(blob);
        }
      }, 'image/jpeg', 0.8);
    }
  }

  // 통합 분석 요청 (텍스트 + 얼굴)
  analyzeCombined(
    sectionName: string,
    sectionText: string,
    readingTime: number
  ) {
    if (!this.videoRef?.current || this.ws?.readyState !== WebSocket.OPEN) {
      return;
    }

    // 현재 프레임 캡처
    const video = this.videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0);
      
      canvas.toBlob((blob) => {
        if (blob) {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result?.toString().split(',')[1];
            if (base64) {
              this.ws?.send(JSON.stringify({
                type: 'combined_analysis',
                section_name: sectionName,
                section_text: sectionText,
                reading_time: readingTime,
                face_frame: base64,
                gaze_data: {},
                timestamp: new Date().toISOString()
              }));
            }
          };
          reader.readAsDataURL(blob);
        }
      }, 'image/jpeg', 0.8);
    }
  }

  // Heartbeat (연결 유지)
  private heartbeatInterval: NodeJS.Timer | null = null;

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // 30초마다
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  // 재연결
  private reconnect() {
    if (this.ws?.readyState === WebSocket.CLOSED) {
      this.connect();
    }
  }

  // 정리
  disconnect() {
    this.stopHeartbeat();
    if (this.frameInterval) {
      clearInterval(this.frameInterval);
      this.frameInterval = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// React Hook
export function useRealtimeAnalysis(consultationId: string) {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult>({
    difficultyScore: 0,
    confusedSections: [],
    faceConfusion: false,
    confusionProbability: 0,
    aiExplanation: '',
    needsAiAssistance: false
  });

  const serviceRef = useRef<RealtimeAnalysisService | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // 서비스 초기화
    serviceRef.current = new RealtimeAnalysisService(
      consultationId,
      setAnalysisResult
    );

    // WebSocket 연결
    serviceRef.current.connect();

    // 정리
    return () => {
      serviceRef.current?.disconnect();
    };
  }, [consultationId]);

  // 텍스트 분석
  const analyzeText = useCallback((text: string, readingTime: number) => {
    serviceRef.current?.analyzeText(text, readingTime);
  }, []);

  // 얼굴 추적 시작
  const startFaceTracking = useCallback(() => {
    if (videoRef.current) {
      serviceRef.current?.startFaceTracking(videoRef);
    }
  }, []);

  // 통합 분석
  const analyzeCombined = useCallback((
    sectionName: string,
    sectionText: string,
    readingTime: number
  ) => {
    serviceRef.current?.analyzeCombined(sectionName, sectionText, readingTime);
  }, []);

  return {
    analysisResult,
    videoRef,
    analyzeText,
    startFaceTracking,
    analyzeCombined
  };
}