from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import logging
from datetime import datetime, timezone
import os
from supabase import create_client, Client

from models.schemas import ReadingData, AnalysisResponse, APIResponse
from pydantic import BaseModel, UUID4
from typing import Optional
from models.database import get_db_connection, release_db_connection
from services.eyetrack_service import eyetrack_service

# 얼굴 분석 서비스 import (조건부)
try:
    from services.face_service import face_service
    FACE_SERVICE_AVAILABLE = True
except ImportError:
    FACE_SERVICE_AVAILABLE = False

# 텍스트 분석 서비스 import (조건부)
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from eyetrack.hybrid_analyzer import HybridTextAnalyzer
    TEXT_ANALYZER_AVAILABLE = True
except ImportError:
    TEXT_ANALYZER_AVAILABLE = False

# Supabase 클라이언트 초기화
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

router = APIRouter()
logger = logging.getLogger(__name__)

# 통합 분석 요청 모델
class ComprehensiveAnalysisRequest(BaseModel):
    consultation_id: UUID4
    customer_id: UUID4
    section_text: str
    section_name: str = ""
    reading_time: float
    gaze_data: Optional[Dict[str, Any]] = None

# 통합 분석 응답 모델
class ComprehensiveAnalysisResponse(BaseModel):
    overall_difficulty: float
    confusion_probability: float
    comprehension_level: str
    difficult_terms: List[Dict[str, str]]
    difficult_sentences: List[Dict[str, Any]]
    ai_explanation: str
    recommendations: List[str]
    face_emotions: Optional[Dict[str, float]] = None

class EmotionDataRequest(BaseModel):
    consultation_id: UUID4
    customer_id: UUID4
    raw_emotion_scores: Dict[str, float]
    timestamp: str

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_reading(data: ReadingData):
    """
    실시간 읽기 분석 API
    
    고객의 읽기 패턴을 분석하여 이해도를 측정하고 
    어려워하는 부분에 대한 AI 설명을 제공합니다.
    """
    try:
        # 입력 데이터 검증
        if not data.section_text.strip():
            raise HTTPException(status_code=400, detail="섹션 텍스트가 비어있습니다.")
        
        if data.reading_time <= 0:
            raise HTTPException(status_code=400, detail="읽기 시간은 양수여야 합니다.")
        
        logger.info(f"분석 시작: 상담ID={data.consultation_id}, 섹션={data.current_section}")
        
        # 아이트래킹 서비스로 분석 수행
        analysis_result = await eyetrack_service.analyze_reading_session(
            consultation_id=data.consultation_id,
            section_name=data.current_section,
            section_text=data.section_text,
            reading_time=data.reading_time,
            gaze_data=data.gaze_data
        )
        
        # 데이터베이스에 분석 결과 저장 (Supabase API 사용)
        try:
            if supabase:
                # 분석 결과에서 추출할 필드들
                fixations = analysis_result.get('fixations', [])
                text_elements = analysis_result.get('text_elements', [])
                reading_metrics = analysis_result.get('reading_metrics', {})
                
                # 데이터베이스에 저장할 데이터 구성
                insert_data = {
                    "consultation_id": data.consultation_id,
                    "customer_id": data.customer_id, 
                    "section_name": data.current_section,
                    "section_text": data.section_text,
                    "difficulty_score": analysis_result.get('difficulty_score', 0.5),
                    "confusion_probability": analysis_result.get('confusion_probability', 0.5),
                    "comprehension_level": analysis_result.get('comprehension_level', 'medium'),
                    "gaze_data": analysis_result.get('gaze_data') or data.gaze_data,
                    "fixations": [f.dict() for f in fixations] if fixations and hasattr(fixations[0], 'dict') else fixations,
                    "text_elements": [t.dict() for t in text_elements] if text_elements and hasattr(text_elements[0], 'dict') else text_elements,
                    "reading_metrics": reading_metrics.dict() if hasattr(reading_metrics, 'dict') else reading_metrics,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # 필수 필드 검증
                required_fields = ["consultation_id", "customer_id", "section_name", "section_text"]
                for field in required_fields:
                    if not insert_data.get(field):
                        logger.warning(f"필수 필드가 누락되었습니다: {field}")
                
                # Supabase에 데이터 저장
                try:
                    result = supabase.table("reading_analysis").insert(insert_data).execute()
                    
                    if hasattr(result, 'data') and result.data:
                        logger.info(f"분석 결과 Supabase 저장 완료: {data.consultation_id}")
                        logger.debug(f"저장된 레코드 ID: {result.data[0].get('id')}")
                    else:
                        logger.error(f"데이터베이스에 저장되었지만 예상치 못한 응답 형식입니다: {result}")
                except Exception as db_error:
                    logger.error(f"Supabase 저장 중 오류 발생: {str(db_error)}")
            else:
                logger.warning("Supabase 클라이언트가 초기화되지 않아 분석 결과를 저장하지 못했습니다.")
                
        except Exception as e:
            logger.error(f"데이터베이스 저장 과정에서 예상치 못한 오류가 발생했습니다: {str(e)}")
        
        # 프론트엔드 친화적 응답 형식 (텍스트 분석 포함)
        return {
            "status": analysis_result.get('status', 'unknown'),
            "difficulty_score": analysis_result.get('difficulty_score', 0.5),
            "confusion_probability": analysis_result.get('confusion_probability', 0.0),
            "comprehension_level": analysis_result.get('comprehension_level', 'medium'),

            # AI 설명 및 추천
            "ai_explanation": analysis_result.get('ai_explanation', ''),
            "recommendations": analysis_result.get('recommendations', []),

            # 텍스트 분석 결과 (프론트엔드 UI용)
            "difficult_terms": analysis_result.get('difficult_terms', []),
            "underlined_sections": analysis_result.get('underlined_sections', []),
            "detailed_explanations": analysis_result.get('detailed_explanations', {}),

            # 혼란 감지 (AI 도우미 트리거용)
            "confused_sentences": analysis_result.get('confused_sentences', []),
            "needs_ai_assistance": analysis_result.get('confusion_probability', 0.0) > 0.7,

            # 메타데이터
            "analysis_metadata": analysis_result.get('analysis_metadata', {}),
            "timestamp": datetime.now().isoformat(),
            "error_message": analysis_result.get('error_message')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"분석 중 예상치 못한 오류: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"분석 서비스 오류: {str(e)}"
        )

@router.get("/session/{consultation_id}/summary")
async def get_session_summary(consultation_id: UUID4):
    """
    특정 상담 세션의 전체 분석 요약 조회
    """
    try:
        summary = eyetrack_service.get_session_summary(consultation_id)
        
        if not summary:
            raise HTTPException(
                status_code=404, 
                detail="해당 상담 세션의 분석 데이터를 찾을 수 없습니다."
            )
        
        return APIResponse(
            success=True,
            message="세션 요약 조회 성공",
            data=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 요약 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="세션 요약 조회 중 오류가 발생했습니다.")

@router.get("/test/difficulty")
async def test_difficulty_analysis(text: str = "계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한됩니다."):
    """
    텍스트 난이도 분석 테스트 API (개발/데모용)
    """
    try:
        difficulty_score = eyetrack_service.get_text_difficulty(text)
        confused_sentences = eyetrack_service.identify_confused_sentences(text, difficulty_score)
        explanation = eyetrack_service.generate_ai_explanation(text, confused_sentences)
        
        return {
            "text": text,
            "difficulty_score": round(difficulty_score, 3),
            "confused_sentences": confused_sentences,
            "ai_explanation": explanation,
            "analysis_time": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"난이도 분석 테스트 실패: {e}")
        raise HTTPException(status_code=500, detail="테스트 중 오류가 발생했습니다.")

@router.get("/stats/realtime")
async def get_realtime_stats():
    """
    실시간 분석 통계 조회 (전체 시스템)
    """
    try:
        conn = await get_db_connection()
        
        # 활성 상담 수
        active_count = await conn.fetchval("""
            SELECT COUNT(*) FROM consultations WHERE status = 'active'
        """)
        
        # 오늘의 분석 건수
        today_analysis = await conn.fetchval("""
            SELECT COUNT(*) FROM reading_analysis 
            WHERE DATE(analysis_timestamp) = CURRENT_DATE
        """)
        
        # 평균 이해도 (최근 24시간)
        avg_comprehension = await conn.fetchval("""
            SELECT AVG(
                CASE 
                    WHEN comprehension_level = 'high' THEN 3
                    WHEN comprehension_level = 'medium' THEN 2
                    WHEN comprehension_level = 'low' THEN 1
                    ELSE 2
                END
            )
            FROM reading_analysis 
            WHERE analysis_timestamp >= NOW() - INTERVAL '24 hours'
        """)
        
        # 고위험 고객 수 (최근 분석에서 이해도가 낮은 고객)
        high_risk_count = await conn.fetchval("""
            SELECT COUNT(DISTINCT customer_id) 
            FROM reading_analysis 
            WHERE confusion_probability > 0.7 
            AND analysis_timestamp >= NOW() - INTERVAL '1 hour'
        """)
        
        await release_db_connection(conn)
        
        return {
            "active_consultations": active_count or 0,
            "today_analysis_count": today_analysis or 0,
            "avg_comprehension_score": round(float(avg_comprehension or 2.0), 2),
            "high_risk_customers": high_risk_count or 0,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"실시간 통계 조회 실패: {e}")
        # DB 오류시에도 기본값 반환
        return {
            "active_consultations": 0,
            "today_analysis_count": 0,
            "avg_comprehension_score": 2.0,
            "high_risk_customers": 0,
            "last_updated": datetime.now().isoformat(),
            "error": "통계 조회 중 오류 발생"
        }

@router.post("/simulate")
async def simulate_analysis(
    section_text: str = "계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한", 
    reading_time: float = 45.0,
    customer_confusion_level: str = "medium"
):
    """
    분석 결과 시뮬레이션 API (데모용)
    
    실제 고객 데이터 없이도 분석 결과를 미리 확인할 수 있습니다.
    """
    try:
        # 가짜 상담 ID 생성
        import uuid
        fake_consultation_id = str(uuid.uuid4())
        fake_customer_id = str(uuid.uuid4())
        
        # 혼란도 레벨에 따른 조정
        confusion_multiplier = {
            "low": 0.3,
            "medium": 0.6, 
            "high": 0.9
        }.get(customer_confusion_level, 0.6)
        
        analysis_result = await eyetrack_service.analyze_reading_session(
            consultation_id=fake_consultation_id,
            section_name="시뮬레이션 섹션",
            section_text=section_text,
            reading_time=reading_time,
            gaze_data={"simulated": True, "confusion_level": customer_confusion_level}
        )
        
        # 시뮬레이션임을 명시
        analysis_result['simulation_mode'] = True
        analysis_result['simulation_params'] = {
            "section_text": section_text,
            "reading_time": reading_time,
            "customer_confusion_level": customer_confusion_level
        }
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"시뮬레이션 실패: {e}")
        raise HTTPException(status_code=500, detail="시뮬레이션 중 오류가 발생했습니다.")

@router.post("/gaze-data")
async def receive_gaze_data(consultation_id: UUID4, gaze_x: float, gaze_y: float, timestamp: float, confidence: float):
    """실시간 시선 데이터 수신"""
    try:
        gaze_data = {
            "x": gaze_x,
            "y": gaze_y,
            "timestamp": timestamp,
            "confidence": confidence
        }

        # 시선 데이터 처리 및 분석
        analysis = eyetrack_service.process_gaze_data(consultation_id, gaze_data)

        return APIResponse(
            success=True,
            message="시선 데이터 처리 완료",
            data=analysis
        )

    except Exception as e:
        logger.error(f"시선 데이터 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="시선 데이터 처리 중 오류가 발생했습니다.")

@router.get("/ai-status/{consultation_id}")
async def get_ai_assistant_status(consultation_id: UUID4):
    """AI 도우미 활성화 상태 조회 (통합 분석 결과 기반)"""
    try:
        # TODO: AI 서버에서 통합 분석 결과를 reading_analysis 테이블에서 조회
        # 현재는 목업 데이터로 동작

        import random
        import time

        # 목업: 시간에 따라 혼란도가 변하는 시뮬레이션
        current_time = int(time.time())
        should_trigger = (current_time % 20) < 7  # 20초마다 7초간 AI 도우미 활성화

        if should_trigger:
            mock_confused_sections = [
            {
                "id": "seizure_section_" + str(datetime.now().timestamp()),
                "title": "압류 관련 제한 사항",
                "content": "계좌에 법적 조치가 취해지면 예금을 찾을 수 없게 됩니다.",
                "timestamp": datetime.now().isoformat()
            }
        ]

            return {
            "consultation_id": consultation_id,
            "should_trigger_ai_assistant": True,
            "current_section": "압류 관련 제한 사항",
            "ai_explanation": "계좌에 법적 조치가 취해지면 예금을 찾을 수 없게 됩니다.",
            "recommendation": "법원에서 계좌를 막거나, 빚 담보로 예금이 잡히면 돈을 찾을 수 없습니다.",
            "confused_sections": mock_confused_sections,
            "confusion_probability": 0.85, # 높은 값으로 설정
            "overall_difficulty": 0.75, # 높은 값으로 설정
            "timestamp": datetime.now().isoformat()
        }

        # 정상 상태 (AI 도우미 비활성화)
        return {
            "consultation_id": consultation_id,
            "should_trigger_ai_assistant": False,
            "current_section": "상품 소개",
            "ai_explanation": "",
            "recommendation": "",
            "confused_sections": [],
            "confusion_probability": 0.3,
            "overall_difficulty": 0.4,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"AI 상태 조회 실패: {e}")
        # 오류 시에도 기본 목업 응답
        return {
            "consultation_id": consultation_id,
            "should_trigger_ai_assistant": False,
            "current_section": "기본 상태",
            "ai_explanation": "",
            "recommendation": "",
            "confused_sections": [],
            "confusion_probability": 0.2,
            "overall_difficulty": 0.3,
            "timestamp": datetime.now().isoformat()
        }

@router.get("/reading-progress/{consultation_id}")
async def get_reading_progress(consultation_id: UUID4):
    """읽기 진행률 조회"""
    try:
        progress = eyetrack_service.get_reading_progress(consultation_id)

        return {
            "consultation_id": consultation_id,
            "progress_percentage": progress.get("percentage", 0),
            "current_section": progress.get("current_section", ""),
            "sections_completed": progress.get("sections_completed", 0),
            "total_sections": progress.get("total_sections", 0),
            "estimated_time_remaining": progress.get("time_remaining", 0),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"읽기 진행률 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="진행률 조회 중 오류가 발생했습니다.")

@router.post("/submit-emotion-data")
async def submit_raw_emotion_data(request: EmotionDataRequest):
    """Raw 감정 데이터 제출 (AI 서버에서 분석 후 통합 결과 저장)"""
    try:
        # TODO: AI 서버에게 위임할 부분
        # 1. raw_emotion_scores를 AI 서버로 전송
        # 2. AI 서버에서 텍스트, 시선추적, 감정을 종합 분석
        # 3. 통합 분석 결과를 reading_analysis 테이블에 저장

        logger.info(f"Raw 감정 데이터 수신: {request.consultation_id}")

        # 임시: Raw 데이터를 별도 테이블에 저장 (AI 서버 처리 대기)
        if supabase:
            raw_data = {
                "consultation_id": request.consultation_id,
                "customer_id": request.customer_id,
                "raw_confusion": request.raw_emotion_scores.get("confusion", 0),
                "raw_engagement": request.raw_emotion_scores.get("engagement", 0),
                "raw_frustration": request.raw_emotion_scores.get("frustration", 0),
                "raw_boredom": request.raw_emotion_scores.get("boredom", 0),
                "timestamp": request.timestamp,
                "status": "pending_ai_analysis"
            }

            result = supabase.table("raw_emotion_data").insert(raw_data).execute()

        return {"success": True, "message": "Raw 감정 데이터 수신 완료"}
        

    except Exception as e:
        logger.error(f"Raw 감정 데이터 처리 실패: {e}")
        raise HTTPException(status_code=500, detail="Raw 감정 데이터 처리 중 오류가 발생했습니다.")

@router.get("/health")
async def eyetracking_health():
    """
    아이트래킹 서비스 상태 확인
    
    서비스의 전반적인 상태와 의존성 상태를 확인합니다.
    """
    health_status = {
        "status": "healthy",
        "service": "eyetracking-analysis",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "database": "unknown",
            "ai_models": "unknown",
            "face_service": "disabled"
        },
        "version": "1.0.0"
    }
    
    try:
        # 데이터베이스 연결 테스트
        if supabase:
            try:
                # 간단한 쿼리로 데이터베이스 연결 테스트
                result = supabase.table('reading_analysis').select("id").limit(1).execute()
                if hasattr(result, 'data'):
                    health_status["dependencies"]["database"] = "connected"
                else:
                    health_status["dependencies"]["database"] = "query_failed"
                    health_status["status"] = "degraded"
            except Exception as db_error:
                health_status["dependencies"]["database"] = f"error: {str(db_error)}"
                health_status["status"] = "unhealthy"
        else:
            health_status["dependencies"]["database"] = "not_initialized"
            health_status["status"] = "unhealthy"
        
        # AI 모델 상태 확인
        try:
            # AI 모델 초기화 테스트 (임시로 간단한 텍스트로 테스트)
            test_text = "서비스 상태 확인을 위한 테스트 문장입니다."
            difficulty = await eyetrack_service.get_text_difficulty_from_ai(test_text)
            if isinstance(difficulty, float) and 0 <= difficulty <= 1:
                health_status["dependencies"]["ai_models"] = "available"
            else:
                health_status["dependencies"]["ai_models"] = "unexpected_response"
                health_status["status"] = "degraded"
        except Exception as ai_error:
            health_status["dependencies"]["ai_models"] = f"error: {str(ai_error)}"
            health_status["status"] = "degraded"
        
        # 얼굴 인식 서비스 상태 확인 (선택적)
        if FACE_SERVICE_AVAILABLE:
            try:
                # 간단한 얼굴 서비스 상태 확인
                face_status = face_service.get_status()
                health_status["dependencies"]["face_service"] = "available" if face_status.get("status") == "ready" else "not_ready"
            except Exception as face_error:
                health_status["dependencies"]["face_service"] = f"error: {str(face_error)}"
        
        return health_status
        
    except Exception as e:
        health_status.update({
            "status": "unhealthy",
            "error": f"Health check failed: {str(e)}",
            "dependencies": health_status.get("dependencies", {})
        })
        return health_status