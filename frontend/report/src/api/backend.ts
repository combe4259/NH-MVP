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
export interface ConsultationReport {
  consultation_id: string;
  customer_name: string;
  product_type: string;
  product_details: any;
  start_time: string;
  duration_minutes: number;
  overall_difficulty: number;
  confused_sections: string[];
  total_sections_analyzed: number;
  comprehension_summary: {
    high: number;
    medium: number;
    low: number;
  };
  recommendations: string[];
  detailed_analysis: Array<{
    section_name: string;
    difficulty_score: number;
    confusion_probability: number;
    comprehension_level: string;
    analysis_timestamp: string;
  }>;
}

export interface ConsultationSummary {
  consultation_id: string;
  customer_name: string;
  product_type: string;
  status: string;
  start_time: string;
  end_time?: string;
}

// Report용 API 함수들
export const reportAPI = {
  // 건강 상태 확인
  async healthCheck() {
    const response = await api.get('/health');
    return response.data;
  },

  // 상담 리포트 조회
  async getConsultationReport(consultationId: string): Promise<ConsultationReport> {
    const response = await api.get(`/api/consultations/${consultationId}/report`);
    return response.data;
  },

  // 완료된 상담 목록 조회
  async getCompletedConsultations(limit: number = 20): Promise<{ consultations: ConsultationSummary[] }> {
    const response = await api.get('/api/consultations/', {
      params: { status: 'completed', limit }
    });
    return response.data;
  },

  // 상담 기본 정보 조회
  async getConsultationInfo(consultationId: string) {
    const response = await api.get(`/api/consultations/${consultationId}`);
    return response.data;
  },

  // 전체 통계 조회
  async getOverallStats() {
    const response = await api.get('/api/eyetracking/stats/realtime');
    return response.data;
  }
};

export default api;