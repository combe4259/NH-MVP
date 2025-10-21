import axios from 'axios';

// 백엔드 API 클라이언트 설정
const API_BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 타입 정의
export interface GazeData {
  consultation_id: string;
  gaze_x: number;
  gaze_y: number;
  timestamp: number;
  confidence: number;
}

export interface AnalysisRequest {
  consultation_id: string;
  customer_id: string;
  current_section: string;
  section_text: string;
  reading_time: number;
  gaze_data?: {
    raw_points?: Array<{x: number, y: number, timestamp: number, confidence?: number}>;
    total_duration?: number;
    fixation_count?: number;
    saccade_count?: number;
    regression_count?: number;
  };
}

export interface ConfusionStatus {
  is_confused: boolean;
  confusion_probability: number;
  current_section: string;
  ai_suggestion?: {
    section: string;
    explanation: string;
    simpleExample?: string;
  };
}

export interface ReadingProgress {
  progress_percentage: number;
  current_section: string;
  sections_completed: number;
  total_sections: number;
  estimated_time_remaining: number;
}

// Customer용 API 함수들
export const customerAPI = {
  // 건강 상태 확인
  async healthCheck() {
    const response = await api.get('/health');
    return response.data;
  },

  // 시선 데이터 전송
  async sendGazeData(data: GazeData) {
    const response = await api.post('/api/eyetracking/gaze-data', {}, {
      params: {
        consultation_id: data.consultation_id,
        gaze_x: data.gaze_x,
        gaze_y: data.gaze_y,
        timestamp: data.timestamp,
        confidence: data.confidence
      }
    });
    return response.data;
  },

  // 텍스트 읽기 분석
  async analyzeReading(data: AnalysisRequest) {
    const response = await api.post('/api/eyetracking/analyze', data);
    return response.data;
  },

  // 읽기 진행률 조회
  async getReadingProgress(consultationId: string): Promise<ReadingProgress> {
    const response = await api.get(`/api/eyetracking/reading-progress/${consultationId}`);
    return response.data;
  },

  // 상담 세션 생성
  async createConsultation(customerName: string, productType: string) {
    const response = await api.post('/api/consultations/', {
      customer_name: customerName,
      product_type: productType,
      product_details: { type: productType }
    });
    return response.data;
  }
};

export default api;