"""
얼굴 표정 분석 API 라우터
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

from services.face_service import face_service
from services.face_analysis_service import face_analyzer
from models.schemas import APIResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# 요청/응답 모델
class FaceAnalysisRequest(BaseModel):
    consultation_id: str
    customer_id: str
    image_data: str  # base64 인코딩된 이미지
    timestamp: Optional[str] = None

class EmotionData(BaseModel):
    confusion: float
    engagement: float
    frustration: float
    boredom: float

class FaceAnalysisResponse(BaseModel):
    status: str
    consultation_id: str
    confusion_detected: bool
    confusion_probability: float
    confidence: float
    emotions: EmotionData
    analysis_timestamp: str

@router.post("/analyze-frame", response_model=FaceAnalysisResponse)
async def analyze_face_frame(request: FaceAnalysisRequest):
    """
    단일 프레임의 얼굴 표정 분석

    웹캠에서 캡처한 이미지의 얼굴 표정을 분석하여
    혼란도와 기타 감정 상태를 측정합니다.
    """
    try:
        logger.info(f"얼굴 분석 요청: 상담ID={request.consultation_id}")

        # 입력 검증
        if not request.image_data:
            raise HTTPException(status_code=400, detail="이미지 데이터가 필요합니다.")

        if not request.consultation_id:
            raise HTTPException(status_code=400, detail="상담 ID가 필요합니다.")

        # 얼굴 분석 수행
        analysis_result = await face_service.analyze_face_emotion(
            image_data=request.image_data,
            consultation_id=request.consultation_id
        )

        # 응답 형식 변환
        if analysis_result.get("status") == "success":
            return FaceAnalysisResponse(
                status=analysis_result["status"],
                consultation_id=analysis_result["consultation_id"],
                confusion_detected=analysis_result["confusion_detected"],
                confusion_probability=analysis_result["confusion_probability"],
                confidence=analysis_result["confidence"],
                emotions=EmotionData(**analysis_result["emotions"]),
                analysis_timestamp=analysis_result["analysis_timestamp"]
            )
        else:
            # 폴백 응답
            return FaceAnalysisResponse(
                status="fallback",
                consultation_id=request.consultation_id,
                confusion_detected=False,
                confusion_probability=0.2,
                confidence=0.5,
                emotions=EmotionData(
                    confusion=0.2,
                    engagement=0.8,
                    frustration=0.1,
                    boredom=0.1
                ),
                analysis_timestamp=datetime.now().isoformat()
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"얼굴 분석 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"얼굴 분석 중 오류 발생: {str(e)}"
        )

@router.post("/analyze")
async def analyze_frame_sequence(request: Dict[str, Any]):
    """
    30프레임 시퀀스 분석 (CNN-LSTM)
    
    프론트엔드 EyeTracker.tsx에서 전송하는 30프레임을 받아
    CNN-LSTM 모델로 confusion 레벨 분석
    """
    try:
        frames = request.get("frames", [])
        sequence_length = request.get("sequence_length", 30)
        
        logger.info(f"CNN-LSTM 분석 요청: {len(frames)}프레임")
        
        # face_analyzer의 analyze_frames 메서드 호출
        result = await face_analyzer.analyze_frames(frames)
        
        logger.info(f"CNN-LSTM 분석 결과: confusion={result.get('confusion')}")
        
        return result
        
    except Exception as e:
        logger.error(f"CNN-LSTM 프레임 분석 실패: {e}")
        return {
            "confusion": 1,
            "confusion_probability": 0.5,
            "confidence": 0.5,
            "error": str(e)
        }

@router.get("/session/{consultation_id}/emotion-summary")
async def get_emotion_summary(consultation_id: str):
    """
    특정 상담 세션의 전체 감정 분석 요약
    """
    try:
        summary = await face_service.get_session_emotion_summary(consultation_id)

        return APIResponse(
            success=True,
            message="감정 분석 요약 조회 성공",
            data=summary
        )

    except Exception as e:
        logger.error(f"감정 요약 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail="감정 분석 요약 조회 중 오류가 발생했습니다."
        )

@router.post("/confusion-alert")
async def send_confusion_alert(consultation_id: str, confusion_level: float):
    """
    높은 혼란도 감지 시 알림 전송
    """
    try:
        if confusion_level > 0.7:
            # 높은 혼란도 감지 시 처리 로직
            alert_data = {
                "consultation_id": consultation_id,
                "confusion_level": confusion_level,
                "alert_type": "high_confusion",
                "timestamp": datetime.now().isoformat(),
                "recommendation": "고객이 내용을 이해하지 못하고 있을 수 있습니다. 추가 설명이 필요합니다."
            }

            logger.warning(f"높은 혼란도 감지: {consultation_id}, 레벨: {confusion_level}")

            return APIResponse(
                success=True,
                message="혼란도 알림 처리 완료",
                data=alert_data
            )
        else:
            return APIResponse(
                success=True,
                message="정상 범위의 혼란도",
                data={
                    "consultation_id": consultation_id,
                    "confusion_level": confusion_level,
                    "status": "normal"
                }
            )

    except Exception as e:
        logger.error(f"혼란도 알림 처리 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail="혼란도 알림 처리 중 오류가 발생했습니다."
        )

@router.get("/confusion-status/{consultation_id}")
async def get_current_confusion_status(consultation_id: str):
    """
    현재 상담 세션의 혼란도 상태 조회
    프론트엔드에서 AI 도우미 팝업 트리거용
    """
    try:
        # TODO: 실제로는 최근 분석 결과를 데이터베이스에서 조회
        # 현재는 Mock 데이터 반환

        current_status = {
            "consultation_id": consultation_id,
            "current_confusion_level": 0.3,
            "is_high_confusion": False,
            "last_analysis_time": datetime.now().isoformat(),
            "should_trigger_ai_assistant": False,
            "emotion_state": {
                "confusion": 0.3,
                "engagement": 0.7,
                "frustration": 0.1,
                "boredom": 0.2
            }
        }

        return current_status

    except Exception as e:
        logger.error(f"혼란도 상태 조회 실패: {e}")
        raise HTTPException(
            status_code=500,
            detail="혼란도 상태 조회 중 오류가 발생했습니다."
        )

@router.get("/health")
async def face_analysis_health():
    """얼굴 분석 서비스 상태 확인"""
    try:
        health_status = face_service.health_check()

        return {
            "status": health_status["status"],
            "service": health_status["service"],
            "model_loaded": health_status["model_loaded"],
            "confusion_tracker": health_status["confusion_tracker"],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"헬스체크 실패: {e}")
        return {
            "status": "unhealthy",
            "service": "face_analysis",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }