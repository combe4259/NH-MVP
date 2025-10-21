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
    
    async def convert_to_sql(self, natural_language_query: str) -> str:
        """
        자연어를 SQL 쿼리로 변환
        """
        try:
            logger.info(f"[NL서비스] convert_to_sql 시작: {natural_language_query}")

            # ai_model_manager의 HuggingFaceModels 인스턴스 확인
            if not hasattr(self.ai_model_manager, 'hf_models') or not self.ai_model_manager.hf_models:
                logger.error("[NL서비스] AI 모델 사용 불가")
                raise RuntimeError("AI 모델이 초기화되지 않았습니다.")

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

        except Exception as e:
            logger.error(f"[NL서비스] 변환 실패: {e}")
            import traceback
            logger.error(f"[NL서비스] 상세 에러:\n{traceback.format_exc()}")
            raise  # 예외를 상위로 전달
    
    def _refine_sql(self, sql_query: str, original_query: str) -> str:
        """
        생성된 SQL 쿼리 정제 및 보정
        """
        # SQL 쿼리 정리
        sql_query = sql_query.strip()

        # SELECT가 없으면 에러
        if not sql_query.upper().startswith("SELECT"):
            raise ValueError(f"유효하지 않은 SQL 쿼리: {sql_query}")
        
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

# 싱글톤 인스턴스
_nl_to_sql_service: Optional[NLtoSQLService] = None

def get_nl_to_sql_service() -> NLtoSQLService:
    """NL to SQL 서비스 싱글톤 인스턴스 반환"""
    global _nl_to_sql_service
    if _nl_to_sql_service is None:
        _nl_to_sql_service = NLtoSQLService()
    return _nl_to_sql_service