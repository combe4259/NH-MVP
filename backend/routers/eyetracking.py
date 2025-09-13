from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from datetime import datetime, timezone
import os
from supabase import create_client, Client

from models.schemas import ReadingData, AnalysisResponse, APIResponse
from models.database import get_db_connection, release_db_connection
from services.eyetrack_service import eyetrack_service

# Supabase 클라이언트 초기화
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

router = APIRouter()
logger = logging.getLogger(__name__)

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
                insert_data = {
                    "consultation_id": data.consultation_id,
                    "customer_id": data.customer_id, 
                    "section_name": data.current_section,
                    "section_text": data.section_text,
                    "difficulty_score": analysis_result.get('difficulty_score', 0.5),
                    "confusion_probability": analysis_result.get('confusion_probability', 0.5),
                    "comprehension_level": analysis_result.get('comprehension_level', 'medium'),
                    "gaze_data": analysis_result.get('gaze_data') or data.gaze_data,
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                result = supabase.table("reading_analysis").insert(insert_data).execute()
                logger.info(f"분석 결과 Supabase 저장 완료: {data.consultation_id}")
            else:
                logger.warning("Supabase 클라이언트가 초기화되지 않음")
                
        except Exception as db_error:
            logger.error(f"DB 저장 실패: {db_error}")
            # DB 저장 실패해도 분석 결과는 반환
        
        # 프론트엔드 친화적 응답 형식 (텍스트 분석 포함)
        return {
            "analysis_status": analysis_result.get('status', 'unknown'),
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
async def get_session_summary(consultation_id: str):
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
async def test_difficulty_analysis(text: str = "중도해지 시 우대금리는 적용되지 않으며, 예금자보호법에 따른 보호 한도는 5천만원입니다."):
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
    section_text: str = "중도해지 시 우대금리 조건은 적용되지 않습니다.", 
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
async def receive_gaze_data(consultation_id: str, gaze_x: float, gaze_y: float, timestamp: float, confidence: float):
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

@router.get("/confusion-status/{consultation_id}")
async def get_confusion_status(consultation_id: str):
    """현재 혼란도 상태 조회 (프론트엔드 AI 도우미용)"""
    try:
        status = eyetrack_service.get_current_confusion_status(consultation_id)

        return {
            "consultation_id": consultation_id,
            "is_confused": status.get("is_confused", False),
            "confusion_probability": status.get("confusion_probability", 0.0),
            "current_section": status.get("current_section", ""),
            "ai_suggestion": status.get("ai_suggestion"),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"혼란도 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="상태 조회 중 오류가 발생했습니다.")

@router.get("/reading-progress/{consultation_id}")
async def get_reading_progress(consultation_id: str):
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

@router.get("/health")
async def eyetracking_health():
    """아이트래킹 서비스 상태 확인"""
    try:
        test_result = eyetrack_service.get_text_difficulty("테스트 텍스트입니다.")

        return {
            "status": "healthy",
            "service": "eyetracking-analysis",
            "test_analysis": "pass" if isinstance(test_result, float) else "fail",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "eyetracking-analysis",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }