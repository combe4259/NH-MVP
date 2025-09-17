"""
자연어를 SQL 쿼리로 변환하는 서비스
ai_model_service에서 로드된 NHSQLNL 모델 사용
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

class NLtoSQLService:
    def __init__(self):
        # ai_model_service에서 이미 로드된 모델 사용
        from services.ai_model_service import ai_model_manager
        self.ai_model_manager = ai_model_manager
        logger.info("NL to SQL 서비스 초기화 (ai_model_service 사용)")
    
    def _prepare_context(self, natural_language_query: str) -> str:
        """
        자연어 쿼리에 데이터베이스 스키마 컨텍스트 추가
        """
        # 데이터베이스 스키마 정보
        schema_context = """
        Table: consultations
        Columns: id (UUID), customer_id (UUID), product_type (VARCHAR), product_details (JSON), 
                consultation_phase (VARCHAR), start_time (TIMESTAMP), end_time (TIMESTAMP), 
                status (VARCHAR - active/completed/cancelled/paused)
        
        Table: customers  
        Columns: id (UUID), name (VARCHAR), created_at (TIMESTAMP)
        
        Table: eyetracking_data
        Columns: id (UUID), consultation_id (UUID), timestamp (TIMESTAMP), 
                current_section (VARCHAR), section_text (TEXT), reading_time_ms (INTEGER),
                difficulty_score (FLOAT), confusion_probability (FLOAT)
        """
        
        # 쿼리에 컨텍스트 추가
        full_query = f"""
        Given the following database schema:
        {schema_context}
        
        Convert this natural language query to SQL:
        {natural_language_query}
        
        Requirements:
        - Join consultations with customers table to get customer name
        - Use proper date/time functions for temporal queries
        - Return relevant columns including consultation_id, customer_name, product_type, status, start_time, end_time
        """
        
        return full_query
    
    async def convert_to_sql(self, natural_language_query: str) -> str:
        """
        자연어를 SQL 쿼리로 변환
        """
        try:
            logger.info(f"[NL서비스] convert_to_sql 시작: {natural_language_query}")
            
            # ai_model_manager의 HuggingFaceModels 인스턴스 확인
            if hasattr(self.ai_model_manager, 'hf_models') and self.ai_model_manager.hf_models:
                logger.info("[NL서비스] AI 모델 사용 가능, 변환 시도")
                # 스키마 컨텍스트 준비
                schema_context = """
                Table: consultations
                Columns: id, customer_id, product_type, product_details, consultation_phase, start_time, end_time, status
                Table: customers  
                Columns: id, name, created_at
                """
                
                # ai_model_service의 convert_nl_to_sql 메서드 사용
                sql_query = await self.ai_model_manager.hf_models.convert_nl_to_sql(
                    natural_language_query, 
                    schema_context
                )
                
                # SQL 정제 및 검증
                sql_query = self._refine_sql(sql_query, natural_language_query)
                
                return sql_query
            else:
                logger.warning("[NL서비스] AI 모델 없음, 폴백 사용")
                logger.warning(f"[NL서비스] hasattr: {hasattr(self.ai_model_manager, 'hf_models')}")
                logger.warning(f"[NL서비스] hf_models: {self.ai_model_manager.hf_models if hasattr(self.ai_model_manager, 'hf_models') else 'None'}")
                return self._generate_fallback_sql(natural_language_query)
            
        except Exception as e:
            logger.error(f"[NL서비스] 변환 실패: {e}")
            import traceback
            logger.error(f"[NL서비스] 상세 에러:\n{traceback.format_exc()}")
            # 폴백: 기본 쿼리 반환
            return self._generate_fallback_sql(natural_language_query)
    
    def _refine_sql(self, sql_query: str, original_query: str) -> str:
        """
        생성된 SQL 쿼리 정제 및 보정
        """
        # SQL 쿼리 정리
        sql_query = sql_query.strip()
        
        # SELECT가 없으면 기본 쿼리 생성
        if not sql_query.upper().startswith("SELECT"):
            return self._generate_fallback_sql(original_query)
        
        # 테이블 별칭 확인 및 수정
        if "consultations" in sql_query and "customers" in sql_query:
            # JOIN이 없으면 추가
            if "JOIN" not in sql_query.upper():
                sql_query = sql_query.replace(
                    "FROM consultations",
                    "FROM consultations c JOIN customers cu ON c.customer_id = cu.id"
                )
        
        # 날짜 함수 보정 (PostgreSQL 형식)
        sql_query = sql_query.replace("NOW()", "CURRENT_TIMESTAMP")
        sql_query = sql_query.replace("CURDATE()", "CURRENT_DATE")
        
        return sql_query
    
    def _generate_fallback_sql(self, natural_language_query: str) -> str:
        """
        폴백 SQL 쿼리 생성
        """
        query_lower = natural_language_query.lower()
        
        # 기본 SELECT 쿼리
        base_sql = """
        SELECT c.id, c.customer_id, cu.name as customer_name, 
               c.product_type, c.consultation_phase, c.status, 
               c.start_time, c.end_time
        FROM consultations c
        JOIN customers cu ON c.customer_id = cu.id
        WHERE 1=1
        """
        
        conditions = []
        
        # 날짜 관련 처리
        if "오늘" in query_lower:
            conditions.append("DATE(c.start_time) = CURRENT_DATE")
        elif "어제" in query_lower:
            conditions.append("DATE(c.start_time) = CURRENT_DATE - INTERVAL '1 day'")
        elif "지난달" in query_lower or "지난 달" in query_lower:
            conditions.append("DATE_TRUNC('month', c.start_time) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')")
        elif "이번달" in query_lower or "이번 달" in query_lower:
            conditions.append("DATE_TRUNC('month', c.start_time) = DATE_TRUNC('month', CURRENT_DATE)")
        elif "최근" in query_lower:
            # 최근 7일
            conditions.append("c.start_time >= CURRENT_DATE - INTERVAL '7 days'")
        
        # 상품 타입 처리
        if "정기예금" in query_lower or "예금" in query_lower:
            conditions.append("c.product_type = '정기예금'")
        elif "적금" in query_lower:
            conditions.append("c.product_type = '적금'")
        elif "펀드" in query_lower:
            conditions.append("c.product_type = '펀드'")
        elif "보험" in query_lower:
            conditions.append("c.product_type = '보험'")
        elif "대출" in query_lower:
            conditions.append("c.product_type = '대출'")
        
        # 상태 처리
        if "완료" in query_lower:
            conditions.append("c.status = 'completed'")
        elif "진행" in query_lower or "활성" in query_lower:
            conditions.append("c.status = 'active'")
        elif "취소" in query_lower:
            conditions.append("c.status = 'cancelled'")
        
        # 고객명 처리 (예: "김민수 고객")
        import re
        name_match = re.search(r'([가-힣]{2,4})\s*(?:고객|님|씨)?', query_lower)
        if name_match:
            customer_name = name_match.group(1)
            conditions.append(f"cu.name LIKE '%{customer_name}%'")
        
        # 조건 결합
        if conditions:
            base_sql += " AND " + " AND ".join(conditions)
        
        # 정렬 및 제한
        base_sql += " ORDER BY c.start_time DESC LIMIT 20"
        
        return base_sql

# 싱글톤 인스턴스
_nl_to_sql_service: Optional[NLtoSQLService] = None

def get_nl_to_sql_service() -> NLtoSQLService:
    """NL to SQL 서비스 싱글톤 인스턴스 반환"""
    global _nl_to_sql_service
    if _nl_to_sql_service is None:
        _nl_to_sql_service = NLtoSQLService()
    return _nl_to_sql_service