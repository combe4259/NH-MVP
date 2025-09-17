from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import uuid

# ===== 시선추적 관련 모델들 =====

class GazePoint(BaseModel):
    """Raw gaze point data from eye tracker"""
    x: float = Field(..., ge=0, le=1, description="Normalized x-coordinate (0-1)")
    y: float = Field(..., ge=0, le=1, description="Normalized y-coordinate (0-1)")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the gaze point was captured"
    )
    confidence: float = Field(
        default=1.0,
        ge=0,
        le=1,
        description="Confidence score (0-1) of the gaze point detection"
    )

class FixationData(BaseModel):
    """Processed fixation data"""
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the fixation"
    )
    start_timestamp: datetime = Field(..., description="When the fixation started")
    end_timestamp: datetime = Field(..., description="When the fixation ended")
    duration: float = Field(..., description="Duration of the fixation in milliseconds")
    avg_x: float = Field(..., ge=0, le=1, description="Average x position (0-1)")
    avg_y: float = Field(..., ge=0, le=1, description="Average y position (0-1)")
    dispersion: float = Field(..., ge=0, description="Dispersion of gaze points")

class SaccadeData(BaseModel):
    """Saccade data between fixations"""
    start_fixation_id: str
    end_fixation_id: str
    duration: float  # in milliseconds
    amplitude: float  # Distance between fixations
    velocity: float   # Average velocity (pixels/ms)

class TextElement(BaseModel):
    """Text element with bounding box"""
    text: str
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    line_number: int
    word_index: Optional[int] = None

class ReadingMetrics(BaseModel):
    """Reading behavior metrics"""
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp() * 1000)
    avg_fixation_duration: float  # in milliseconds
    fixations_per_minute: float
    regression_count: int
    words_per_minute: Optional[float] = None
    difficult_terms: Dict[str, float] = Field(
        default_factory=dict,
        description="Dictionary of terms and total fixation time (ms)"
    )

class ReadingDataRequest(BaseModel):
    """시선추적 분석 요청 데이터 (프론트엔드 → 백엔드)"""
    current_section: str = Field(..., description="현재 읽고 있는 섹션명")
    customer_id: str = Field(..., description="고객 ID")
    consultation_id: str = Field(..., description="상담 세션 ID")
    section_text: str = Field(..., description="섹션 텍스트 내용")
    gaze_data: List[GazePoint] = Field(
        default_factory=list,
        description="Raw gaze point data from eye tracker"
    )
    text_elements: List[TextElement] = Field(
        default_factory=list,
        description="Text elements with their bounding boxes in the document"
    )

class ReadingDataResponse(ReadingDataRequest):
    """시선추적 분석 응답 데이터 (백엔드 → 프론트엔드)"""
    fixations: List[FixationData] = Field(
        default_factory=list,
        description="Processed fixation data"
    )
    reading_metrics: ReadingMetrics = Field(
        default_factory=ReadingMetrics,
        description="Calculated reading metrics"
    )
    processed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the analysis was performed"
    )

# 요청 모델들
class ReadingData(BaseModel):
    """아이트래킹 분석 요청 데이터"""
    current_section: str = Field(..., description="현재 읽고 있는 섹션명")
    reading_time: float = Field(..., description="읽기 시간(초)")
    customer_id: str = Field(..., description="고객 ID")
    consultation_id: str = Field(..., description="상담 세션 ID")
    section_text: str = Field(..., description="섹션 텍스트 내용")
    gaze_data: Optional[Dict[str, Any]] = Field(None, description="시선 추적 데이터")
    face_analysis: Optional[Dict[str, Any]] = Field(None, description="얼굴 분석 데이터 (CNN-LSTM)")

class ConsultationCreate(BaseModel):
    """새 상담 생성 요청"""
    customer_name: str = Field(..., description="고객명")
    product_type: str = Field(..., description="상품 유형")
    product_details: Dict[str, Any] = Field(..., description="상품 상세 정보")

class CustomerCreate(BaseModel):
    """고객 생성 요청"""
    name: str = Field(..., min_length=1, max_length=100, description="고객명")

# 응답 모델들
class AnalysisResponse(BaseModel):
    """아이트래킹 분석 결과 응답"""
    status: str = Field(..., description="분석 상태 (good/moderate/confused/error)")
    confused_sentences: List[int] = Field(..., description="어려워하는 문장 번호들")
    ai_explanation: str = Field(..., description="AI가 생성한 쉬운 설명")
    difficulty_score: float = Field(..., description="텍스트 난이도 점수 (0-1)")
    confusion_probability: Optional[float] = Field(None, description="혼란도 확률 (0-1)")
    comprehension_level: str = Field(..., description="이해도 수준 (high/medium/low)")
    recommendations: List[str] = Field(..., description="추천사항 목록")
    analysis_metadata: Optional[Dict[str, Any]] = Field(None, description="분석 메타데이터")
    error_message: Optional[str] = Field(None, description="오류 메시지")

class StaffMonitoringResponse(BaseModel):
    """직원용 실시간 모니터링 응답"""
    consultation_id: str = Field(..., description="상담 세션 ID")
    customer_name: str = Field(..., description="고객명")
    current_section: Optional[str] = Field(None, description="현재 읽는 섹션")
    difficulty_score: Optional[float] = Field(None, description="현재 난이도 점수")
    comprehension_level: Optional[str] = Field(None, description="현재 이해도 수준")
    confusion_probability: Optional[float] = Field(None, description="현재 혼란도")
    needs_intervention: bool = Field(..., description="개입 필요 여부")
    alert_message: Optional[str] = Field(None, description="알림 메시지")
    timestamp: Optional[str] = Field(None, description="마지막 업데이트 시간")
    session_summary: Optional[Dict[str, Any]] = Field(None, description="세션 전체 요약")

class ConsultationReportResponse(BaseModel):
    """상담 리포트 응답"""
    consultation_id: str = Field(..., description="상담 세션 ID")
    customer_name: str = Field(..., description="고객명")
    product_type: str = Field(..., description="상품 유형")
    product_details: Dict[str, Any] = Field(..., description="상품 상세 정보")
    start_time: str = Field(..., description="상담 시작 시간")
    duration_minutes: float = Field(..., description="상담 소요 시간(분)")
    overall_difficulty: float = Field(..., description="전체 평균 난이도")
    confused_sections: List[str] = Field(..., description="어려워했던 섹션들")
    total_sections_analyzed: int = Field(..., description="분석된 총 섹션 수")
    comprehension_summary: Dict[str, int] = Field(..., description="이해도별 섹션 수 {'high': 3, 'medium': 2, 'low': 1} 형식")
    recommendations: List[str] = Field(..., description="향후 권장사항")
    detailed_analysis: Optional[List[Dict[str, Any]]] = Field(None, description="상세 분석 결과")
    detailed_info: Optional[Dict[str, Any]] = Field(None, description="상담 상세 정보 (UI용)")

class ConsultationResponse(BaseModel):
    """상담 생성/조회 응답"""
    consultation_id: str = Field(..., description="상담 세션 ID")
    customer_id: str = Field(..., description="고객 ID")
    customer_name: Optional[str] = Field(None, description="고객명")
    product_type: str = Field(..., description="상품 유형")
    product_details: Dict[str, Any] = Field(..., description="상품 상세 정보")
    consultation_phase: str = Field(..., description="상담 단계")
    status: str = Field(..., description="상담 상태")
    start_time: str = Field(..., description="시작 시간")
    end_time: Optional[str] = Field(None, description="종료 시간")

class CustomerResponse(BaseModel):
    """고객 정보 응답"""
    id: str = Field(..., description="고객 ID")
    name: str = Field(..., description="고객명")
    created_at: str = Field(..., description="생성일시")

# 상태 관리용 모델들
class HealthCheck(BaseModel):
    """서비스 상태 확인"""
    status: str = Field(..., description="서비스 상태")
    service: str = Field(..., description="서비스명")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class APIResponse(BaseModel):
    """기본 API 응답 래퍼"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[Any] = Field(None, description="응답 데이터")
    error: Optional[str] = Field(None, description="오류 정보")

class ServiceInfo(BaseModel):
    """서비스 정보"""
    message: str
    version: str
    status: str
    endpoints: Dict[str, str]

# 데이터베이스 관련 모델들
class ReadingAnalysisDB(BaseModel):
    """읽기 분석 DB 저장용 모델 (시선추적 데이터 포함)"""
    id: Optional[str] = None
    consultation_id: str
    customer_id: str
    section_name: str
    section_text: Optional[str] = None
    difficulty_score: Optional[float] = None
    confusion_probability: Optional[float] = None
    comprehension_level: Optional[str] = None

    # 시선추적 관련 데이터
    gaze_data: Optional[Dict[str, Any]] = None
    fixations: Optional[List[Dict[str, Any]]] = None
    text_elements: Optional[List[Dict[str, Any]]] = None
    reading_metrics: Optional[Dict[str, Any]] = None

    analysis_timestamp: Optional[datetime] = None
    created_at: Optional[datetime] = None

class ConsultationDB(BaseModel):
    """상담 DB 저장용 모델"""
    id: Optional[str] = None
    customer_id: str
    product_type: str
    product_details: Dict[str, Any]
    consultation_phase: str = "terms_reading"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "active"
    created_at: Optional[datetime] = None

class CustomerDB(BaseModel):
    """고객 DB 저장용 모델"""
    id: Optional[str] = None
    name: str
    created_at: Optional[datetime] = None

# 검증 함수들
def validate_consultation_phase(phase: str) -> bool:
    """상담 단계 유효성 검증"""
    valid_phases = ["product_intro", "terms_reading", "application", "completed"]
    return phase in valid_phases

def validate_comprehension_level(level: str) -> bool:
    """이해도 수준 유효성 검증"""
    valid_levels = ["high", "medium", "low"]
    return level in valid_levels

def validate_consultation_status(status: str) -> bool:
    """상담 상태 유효성 검증"""
    valid_statuses = ["active", "paused", "completed", "cancelled"]
    return status in valid_statuses

# 예외 모델들
class ErrorResponse(BaseModel):
    """오류 응답 모델"""
    error: str = Field(..., description="오류 타입")
    message: str = Field(..., description="오류 메시지")
    detail: Optional[str] = Field(None, description="상세 오류 정보")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# 실시간 알림 관련
class AlertMessage(BaseModel):
    """실시간 알림 메시지"""
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    consultation_id: str
    customer_name: str
    alert_type: str = Field(..., description="알림 유형 (critical/warning/info)")
    message: str = Field(..., description="알림 메시지")
    needs_immediate_action: bool = Field(default=False)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

class RealtimeStats(BaseModel):
    """실시간 통계 데이터"""
    active_consultations: int = Field(default=0)
    high_risk_customers: int = Field(default=0)
    average_comprehension: float = Field(default=0.0)
    total_alerts: int = Field(default=0)
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())