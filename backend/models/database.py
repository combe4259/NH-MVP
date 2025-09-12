import asyncpg
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# PostgreSQL 연결 설정
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "postgres")
}

DATABASE_URL = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"

class DatabaseManager:
    def __init__(self):
        self.pool = None
    
    async def create_pool(self):
        """데이터베이스 연결 풀 생성"""
        try:
            self.pool = await asyncpg.create_pool(
                host=DATABASE_CONFIG["host"],
                port=DATABASE_CONFIG["port"],
                user=DATABASE_CONFIG["user"],
                password=DATABASE_CONFIG["password"],
                database=DATABASE_CONFIG["database"],
                min_size=1,
                max_size=10
            )
            logger.info("데이터베이스 연결 풀이 생성되었습니다.")
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            raise
    
    async def close_pool(self):
        """연결 풀 종료"""
        if self.pool:
            await self.pool.close()
            logger.info("데이터베이스 연결 풀이 종료되었습니다.")
    
    async def get_connection(self):
        """데이터베이스 연결 반환"""
        if not self.pool:
            await self.create_pool()
        return await self.pool.acquire()
    
    async def release_connection(self, conn):
        """연결 반환"""
        if self.pool:
            await self.pool.release(conn)

# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()

async def get_db_connection():
    """데이터베이스 연결 헬퍼 함수"""
    return await db_manager.get_connection()

async def release_db_connection(conn):
    """데이터베이스 연결 해제 헬퍼 함수"""
    await db_manager.release_connection(conn)

# 테이블 생성 SQL
CREATE_TABLES_SQL = """
-- 고객 테이블
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 상담 테이블
CREATE TABLE IF NOT EXISTS consultations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    product_type VARCHAR(50) NOT NULL,
    product_details JSONB,
    consultation_phase VARCHAR(20) DEFAULT 'terms_reading',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 읽기 분석 결과 테이블
CREATE TABLE IF NOT EXISTS reading_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID REFERENCES consultations(id),
    customer_id UUID REFERENCES customers(id),
    section_name VARCHAR(100) NOT NULL,
    section_text TEXT,
    difficulty_score DECIMAL(3,2),
    confusion_probability DECIMAL(3,2),
    comprehension_level VARCHAR(10),
    gaze_data JSONB,
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 상담 요약 테이블 (리포트용)
CREATE TABLE IF NOT EXISTS consultation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    consultation_id UUID REFERENCES consultations(id),
    overall_difficulty DECIMAL(3,2),
    confused_sections TEXT[],
    total_sections INTEGER,
    comprehension_high INTEGER DEFAULT 0,
    comprehension_medium INTEGER DEFAULT 0,
    comprehension_low INTEGER DEFAULT 0,
    recommendations TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_consultations_customer_id ON consultations(customer_id);
CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status);
CREATE INDEX IF NOT EXISTS idx_reading_analysis_consultation_id ON reading_analysis(consultation_id);
CREATE INDEX IF NOT EXISTS idx_reading_analysis_timestamp ON reading_analysis(analysis_timestamp);
"""

async def init_database():
    """데이터베이스 초기화 (테이블 생성)"""
    try:
        conn = await get_db_connection()
        await conn.execute(CREATE_TABLES_SQL)
        await release_db_connection(conn)
        logger.info("데이터베이스 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise

# 앱 시작시 데이터베이스 초기화
async def startup_database():
    """FastAPI 앱 시작시 실행"""
    await db_manager.create_pool()
    await init_database()

async def shutdown_database():
    """FastAPI 앱 종료시 실행"""
    await db_manager.close_pool()