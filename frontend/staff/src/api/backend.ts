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
export interface ConsultationInfo {
  consultation_id: string;
  customer_id: string;
  customer_name: string;
  product_type: string;
  consultation_phase: string;
  status: string;
  start_time: string;
}

export interface RealtimeStats {
  active_consultations: number;
  today_analysis_count: number;
  avg_comprehension_score: number;
  high_risk_customers: number;
}

export interface SessionSummary {
  consultation_id: string;
  total_sections: number;
  avg_difficulty: number;
  avg_confusion: number;
  comprehension_summary: {
    high: number;
    medium: number;
    low: number;
  };
  confused_sections: string[];
  session_duration: number;
}

// Staff용 API 함수들
export const staffAPI = {
  // 건강 상태 확인
  async healthCheck() {
    const response = await api.get('/health');
    return response.data;
  },

  // 실시간 통계 조회
  async getRealtimeStats(): Promise<RealtimeStats> {
    const response = await api.get('/api/eyetracking/stats/realtime');
    return response.data;
  },

  // 상담 목록 조회
  async getConsultations(status?: string) {
    const params = status ? { status } : {};
    const response = await api.get('/api/consultations/', { params });
    return response.data;
  },

  // 특정 상담 세션 요약
  async getSessionSummary(consultationId: string): Promise<SessionSummary> {
    const response = await api.get(`/api/eyetracking/session/${consultationId}/summary`);
    return response.data;
  },

  // 상담 상태 업데이트
  async updateConsultationStatus(consultationId: string, status: string, phase?: string) {
    const params = { status, ...(phase && { phase }) };
    const response = await api.put(`/api/consultations/${consultationId}/status`, {}, { params });
    return response.data;
  },

  // 실시간 모니터링 (특정 상담)
  async getConsultationDetails(consultationId: string): Promise<ConsultationInfo> {
    const response = await api.get(`/api/consultations/${consultationId}`);
    return response.data;
  }
};

export default api;