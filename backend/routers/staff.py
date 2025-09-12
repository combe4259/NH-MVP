from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
import logging
from datetime import datetime, timezone

from models.schemas import StaffMonitoringResponse, AlertMessage, RealtimeStats, APIResponse
from models.database import get_db_connection, release_db_connection
from services.eyetrack_service import eyetrack_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/realtime/{consultation_id}", response_model=StaffMonitoringResponse)
async def get_realtime_monitoring_data(consultation_id: str):
    """
    특정 상담의 실시간 모니터링 데이터 조회
    
    직원이 고객의 이해도와 상태를 실시간으로 모니터링할 수 있는 API입니다.
    """
    try:
        conn = await get_db_connection()
        
        # 최신 분석 데이터 조회
        latest_analysis = await conn.fetchrow("""
            SELECT ra.*, c.product_type, cu.name as customer_name
            FROM reading_analysis ra
            JOIN consultations c ON ra.consultation_id = c.id
            JOIN customers cu ON ra.customer_id = cu.id
            WHERE ra.consultation_id = $1
            ORDER BY ra.analysis_timestamp DESC
            LIMIT 1
        """, consultation_id)
        
        if not latest_analysis:
            await release_db_connection(conn)
            raise HTTPException(
                status_code=404, 
                detail="해당 상담의 분석 데이터를 찾을 수 없습니다."
            )
        
        await release_db_connection(conn)
        
        # 개입 필요 여부 판단
        confusion_prob = float(latest_analysis['confusion_probability'] or 0)
        needs_intervention = confusion_prob > 0.7
        
        # 알림 메시지 생성
        alert_message = None
        if needs_intervention:
            if confusion_prob > 0.8:
                alert_message = f"🚨 긴급: {latest_analysis['customer_name']} 고객이 '{latest_analysis['section_name']}' 부분에서 매우 어려워하고 있습니다. 즉시 개입이 필요합니다."
            else:
                alert_message = f"⚠️ 주의: {latest_analysis['customer_name']} 고객이 현재 내용을 이해하기 어려워하고 있습니다. 도움이 필요할 수 있습니다."
        
        # 세션 전체 요약 가져오기
        session_summary = eyetrack_service.get_session_summary(consultation_id)
        
        return StaffMonitoringResponse(
            consultation_id=consultation_id,
            customer_name=latest_analysis['customer_name'],
            current_section=latest_analysis['section_name'],
            difficulty_score=float(latest_analysis['difficulty_score'] or 0),
            comprehension_level=latest_analysis['comprehension_level'],
            confusion_probability=confusion_prob,
            needs_intervention=needs_intervention,
            alert_message=alert_message,
            timestamp=latest_analysis['analysis_timestamp'].isoformat(),
            session_summary=session_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"실시간 모니터링 데이터 조회 실패: {e}")
        raise HTTPException(
            status_code=500, 
            detail="모니터링 데이터를 가져오는 중 오류가 발생했습니다."
        )

@router.get("/dashboard/overview")
async def get_dashboard_overview():
    """직원 대시보드 개요 정보"""
    try:
        conn = await get_db_connection()
        
        # 활성 상담 목록
        active_consultations = await conn.fetch("""
            SELECT DISTINCT 
                c.id as consultation_id,
                cu.name as customer_name,
                c.product_type,
                c.start_time,
                c.consultation_phase,
                COALESCE(latest.comprehension_level, 'unknown') as latest_comprehension,
                COALESCE(latest.confusion_probability, 0) as latest_confusion,
                COALESCE(latest.section_name, '분석 대기중') as current_section
            FROM consultations c
            JOIN customers cu ON c.customer_id = cu.id
            LEFT JOIN (
                SELECT DISTINCT ON (consultation_id) 
                    consultation_id, comprehension_level, confusion_probability, 
                    section_name, analysis_timestamp
                FROM reading_analysis
                ORDER BY consultation_id, analysis_timestamp DESC
            ) latest ON c.id = latest.consultation_id
            WHERE c.status = 'active'
            ORDER BY c.start_time DESC
            LIMIT 20
        """)
        
        await release_db_connection(conn)
        
        # 데이터 가공
        consultation_list = []
        for row in active_consultations:
            consultation_list.append({
                "consultation_id": row['consultation_id'],
                "customer_name": row['customer_name'],
                "product_type": row['product_type'],
                "current_section": row['current_section'],
                "comprehension_level": row['latest_comprehension'],
                "confusion_probability": float(row['latest_confusion']),
                "needs_attention": float(row['latest_confusion']) > 0.6,
                "duration_minutes": (datetime.now(timezone.utc) - row['start_time']).total_seconds() / 60
            })
        
        return {
            "active_consultations": consultation_list,
            "overview": {
                "active_consultations_count": len(active_consultations),
                "high_risk_customers": len([c for c in consultation_list if c['confusion_probability'] > 0.7]),
            },
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"대시보드 개요 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="대시보드 데이터 조회 실패")

@router.get("/alerts")
async def get_active_alerts():
    """활성 알림 목록 조회"""
    try:
        conn = await get_db_connection()
        
        high_confusion_analyses = await conn.fetch("""
            SELECT 
                ra.consultation_id,
                cu.name as customer_name,
                ra.section_name,
                ra.confusion_probability,
                ra.analysis_timestamp
            FROM reading_analysis ra
            JOIN customers cu ON ra.customer_id = cu.id
            JOIN consultations c ON ra.consultation_id = c.id
            WHERE ra.confusion_probability > 0.6
            AND ra.analysis_timestamp >= NOW() - INTERVAL '30 minutes'
            AND c.status = 'active'
            ORDER BY ra.confusion_probability DESC
            LIMIT 10
        """)
        
        await release_db_connection(conn)
        
        alerts = []
        for analysis in high_confusion_analyses:
            confusion_level = float(analysis['confusion_probability'])
            
            if confusion_level > 0.8:
                alert_type = "critical"
                message = f"{analysis['customer_name']} 고객이 '{analysis['section_name']}' 부분에서 매우 어려워하고 있습니다."
            elif confusion_level > 0.7:
                alert_type = "warning"
                message = f"{analysis['customer_name']} 고객이 '{analysis['section_name']}' 부분에서 어려워하고 있습니다."
            else:
                alert_type = "info"
                message = f"{analysis['customer_name']} 고객의 이해도가 다소 낮습니다."
            
            alerts.append({
                "consultation_id": analysis['consultation_id'],
                "customer_name": analysis['customer_name'],
                "alert_type": alert_type,
                "message": message,
                "timestamp": analysis['analysis_timestamp'].isoformat()
            })
        
        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"알림 조회 실패: {e}")
        raise HTTPException(status_code=500, detail="알림 조회 실패")