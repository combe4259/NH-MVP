"""
얼굴 분석 API 라우터
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import logging
from services.face_analysis_service import face_analyzer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/face", tags=["face"])

class FaceAnalysisRequest(BaseModel):
    """얼굴 분석 요청 모델"""
    frames: List[str]  # Base64 인코딩된 프레임 리스트
    sequence_length: int = 30

class FaceAnalysisResponse(BaseModel):
    """얼굴 분석 응답 모델"""
    confusion: int  # 0-3 레벨
    confusion_probability: float
    confidence: float
    all_probabilities: Dict[str, float] = {}
    error: str = None

@router.post("/analyze", response_model=FaceAnalysisResponse)
async def analyze_face_frames(request: FaceAnalysisRequest):
    """
    프레임 시퀀스를 분석하여 confusion 레벨 반환
    """
    try:
        logger.info(f"얼굴 분석 요청: {len(request.frames)} 프레임")
        
        # 프레임 수 검증
        if len(request.frames) == 0:
            raise HTTPException(status_code=400, detail="프레임이 없습니다")
        
        # 얼굴 분석 서비스 호출
        result = await face_analyzer.analyze_frames(request.frames)
        
        return FaceAnalysisResponse(**result)
        
    except Exception as e:
        logger.error(f"얼굴 분석 API 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "healthy", "service": "face_analysis"}