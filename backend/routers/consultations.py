from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
import logging
import json
import uuid
from datetime import datetime, timezone

from models.schemas import (
    ConsultationCreate, ConsultationResponse, ConsultationReportResponse, 
    CustomerCreate, CustomerResponse, APIResponse
)
from models.database import get_db_connection, release_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ConsultationResponse)
async def create_consultation(consultation: ConsultationCreate):
    """
    새 상담 세션 생성
    
    고객 정보와 상품 정보를 받아서 새로운 상담 세션을 시작합니다.
    """
    try:
        conn = await get_db_connection()
        
        consultation_id = str(uuid.uuid4())
        customer_id = str(uuid.uuid4())
        
        # 고객 정보 저장
        await conn.execute("""
            INSERT INTO customers (id, name, created_at)
            VALUES ($1, $2, $3)
        """, customer_id, consultation.customer_name, datetime.now(timezone.utc))
        
        # 상담 세션 생성
        await conn.execute("""
            INSERT INTO consultations (id, customer_id, product_type, product_details, 
                                     consultation_phase, start_time, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, consultation_id, customer_id, consultation.product_type, 
        json.dumps(consultation.product_details), 'terms_reading', 
        datetime.now(timezone.utc), 'active')
        
        await release_db_connection(conn)
        
        logger.info(f"새 상담 생성됨: {consultation_id}, 고객: {consultation.customer_name}")
        
        return ConsultationResponse(
            consultation_id=consultation_id,
            customer_id=customer_id,
            customer_name=consultation.customer_name,
            product_type=consultation.product_type,
            product_details=consultation.product_details,
            consultation_phase='terms_reading',
            status='active',
            start_time=datetime.now(timezone.utc).isoformat()
        )
        
    except Exception as e:
        logger.error(f"상담 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"상담 생성 중 오류 발생: {str(e)}")

@router.get("/{consultation_id}", response_model=ConsultationResponse)
async def get_consultation(consultation_id: str):
    """상담 정보 조회"""
    try:
        conn = await get_db_connection()
        
        consultation = await conn.fetchrow("""
            SELECT c.*, cu.name as customer_name 
            FROM consultations c
            JOIN customers cu ON c.customer_id = cu.id
            WHERE c.id = $1
        """, consultation_id)
        
        await release_db_connection(conn)
        
        if not consultation:
            raise HTTPException(status_code=404, detail="상담을 찾을 수 없습니다.")
        
        return ConsultationResponse(
            consultation_id=consultation['id'],
            customer_id=consultation['customer_id'],
            customer_name=consultation['customer_name'],
            product_type=consultation['product_type'],
            product_details=json.loads(consultation['product_details']),
            consultation_phase=consultation['consultation_phase'],
            status=consultation['status'],
            start_time=consultation['start_time'].isoformat(),
            end_time=consultation['end_time'].isoformat() if consultation['end_time'] else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상담 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="상담 조회 중 오류가 발생했습니다.")

@router.get("/{consultation_id}/report", response_model=ConsultationReportResponse)
async def get_consultation_report(consultation_id: str):
    """
    상담 완료 후 리포트 생성
    
    Report 프론트엔드에서 사용하는 상담 요약 및 분석 결과를 제공합니다.
    """
    try:
        conn = await get_db_connection()
        
        # 상담 기본 정보
        consultation = await conn.fetchrow("""
            SELECT c.*, cu.name as customer_name 
            FROM consultations c
            JOIN customers cu ON c.customer_id = cu.id
            WHERE c.id = $1
        """, consultation_id)
        
        if not consultation:
            await release_db_connection(conn)
            raise HTTPException(status_code=404, detail="상담을 찾을 수 없습니다.")
        
        # 분석 데이터 조회
        analysis_results = await conn.fetch("""
            SELECT * FROM reading_analysis 
            WHERE consultation_id = $1 
            ORDER BY analysis_timestamp
        """, consultation_id)
        
        await release_db_connection(conn)
        
        # 종합 분석
        if analysis_results:
            avg_difficulty = sum(float(r['difficulty_score'] or 0) for r in analysis_results) / len(analysis_results)
            confused_sections = [r['section_name'] for r in analysis_results if float(r['confusion_probability'] or 0) > 0.6]
            
            comprehension_summary = {
                "high": len([r for r in analysis_results if r['comprehension_level'] == 'high']),
                "medium": len([r for r in analysis_results if r['comprehension_level'] == 'medium']),
                "low": len([r for r in analysis_results if r['comprehension_level'] == 'low'])
            }
            
            # 상세 분석 결과
            detailed_analysis = []
            for result in analysis_results:
                detailed_analysis.append({
                    "section_name": result['section_name'],
                    "difficulty_score": float(result['difficulty_score'] or 0),
                    "confusion_probability": float(result['confusion_probability'] or 0),
                    "comprehension_level": result['comprehension_level'],
                    "analysis_timestamp": result['analysis_timestamp'].isoformat()
                })
        else:
            avg_difficulty = 0.0
            confused_sections = []
            comprehension_summary = {"high": 0, "medium": 0, "low": 0}
            detailed_analysis = []
        
        # 권장사항 생성
        recommendations = []
        if len(confused_sections) > 0:
            recommendations.append(f"이해도가 낮았던 부분({', '.join(confused_sections[:3])})을 다시 한번 설명해주세요")
            recommendations.append("특히 어려워했던 금융 용어들에 대한 추가 설명이 필요합니다")
        else:
            recommendations.append("전반적으로 잘 이해하셨습니다")
            recommendations.append("다음 단계로 진행하셔도 좋습니다")
        
        # 상담 소요 시간 계산
        duration_minutes = 0
        if consultation['start_time']:
            end_time = consultation['end_time'] or datetime.now(timezone.utc)
            duration_minutes = (end_time - consultation['start_time']).total_seconds() / 60
        
        return ConsultationReportResponse(
            consultation_id=consultation_id,
            customer_name=consultation['customer_name'],
            product_type=consultation['product_type'],
            product_details=json.loads(consultation['product_details']),
            start_time=consultation['start_time'].isoformat(),
            duration_minutes=duration_minutes,
            overall_difficulty=round(avg_difficulty, 2),
            confused_sections=confused_sections,
            total_sections_analyzed=len(analysis_results),
            comprehension_summary=comprehension_summary,
            recommendations=recommendations,
            detailed_analysis=detailed_analysis
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"리포트 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="리포트 생성 중 오류가 발생했습니다.")

@router.put("/{consultation_id}/status")
async def update_consultation_status(consultation_id: str, status: str, phase: Optional[str] = None):
    """상담 상태 업데이트"""
    try:
        valid_statuses = ["active", "paused", "completed", "cancelled"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail="유효하지 않은 상태입니다.")
        
        conn = await get_db_connection()
        
        # 상담 상태 업데이트
        if phase:
            await conn.execute("""
                UPDATE consultations 
                SET status = $1, consultation_phase = $2, 
                    end_time = CASE WHEN $1 = 'completed' THEN NOW() ELSE end_time END
                WHERE id = $3
            """, status, phase, consultation_id)
        else:
            await conn.execute("""
                UPDATE consultations 
                SET status = $1,
                    end_time = CASE WHEN $1 = 'completed' THEN NOW() ELSE end_time END
                WHERE id = $2
            """, status, consultation_id)
        
        await release_db_connection(conn)
        
        logger.info(f"상담 상태 업데이트: {consultation_id} -> {status}")
        
        return APIResponse(
            success=True,
            message="상담 상태가 성공적으로 업데이트되었습니다.",
            data={
                "consultation_id": consultation_id,
                "new_status": status,
                "new_phase": phase,
                "updated_at": datetime.now().isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"상담 상태 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail="상담 상태 업데이트 중 오류가 발생했습니다.")

@router.get("/")
async def list_consultations(status: Optional[str] = None, limit: int = 20):
    """상담 목록 조회"""
    try:
        conn = await get_db_connection()
        
        if status:
            consultations = await conn.fetch("""
                SELECT c.*, cu.name as customer_name 
                FROM consultations c
                JOIN customers cu ON c.customer_id = cu.id
                WHERE c.status = $1
                ORDER BY c.start_time DESC
                LIMIT $2
            """, status, limit)
        else:
            consultations = await conn.fetch("""
                SELECT c.*, cu.name as customer_name 
                FROM consultations c
                JOIN customers cu ON c.customer_id = cu.id
                ORDER BY c.start_time DESC
                LIMIT $1
            """, limit)
        
        await release_db_connection(conn)
        
        consultation_list = []
        for consultation in consultations:
            consultation_list.append({
                "consultation_id": consultation['id'],
                "customer_id": consultation['customer_id'],
                "customer_name": consultation['customer_name'],
                "product_type": consultation['product_type'],
                "consultation_phase": consultation['consultation_phase'],
                "status": consultation['status'],
                "start_time": consultation['start_time'].isoformat(),
                "end_time": consultation['end_time'].isoformat() if consultation['end_time'] else None
            })
        
        return {
            "consultations": consultation_list,
            "total_count": len(consultation_list),
            "filter": status or "all",
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"상담 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="상담 목록 조회 중 오류가 발생했습니다.")

@router.post("/customers", response_model=CustomerResponse)
async def create_customer(customer: CustomerCreate):
    """새 고객 생성"""
    try:
        conn = await get_db_connection()
        
        customer_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc)
        
        await conn.execute("""
            INSERT INTO customers (id, name, created_at)
            VALUES ($1, $2, $3)
        """, customer_id, customer.name, created_at)
        
        await release_db_connection(conn)
        
        return CustomerResponse(
            id=customer_id,
            name=customer.name,
            created_at=created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"고객 생성 실패: {e}")
        raise HTTPException(status_code=500, detail="고객 생성 중 오류가 발생했습니다.")

@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str):
    """고객 정보 조회"""
    try:
        conn = await get_db_connection()
        
        customer = await conn.fetchrow("""
            SELECT * FROM customers WHERE id = $1
        """, customer_id)
        
        await release_db_connection(conn)
        
        if not customer:
            raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")
        
        return CustomerResponse(
            id=customer['id'],
            name=customer['name'],
            created_at=customer['created_at'].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"고객 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="고객 조회 중 오류가 발생했습니다.")