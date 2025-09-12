import asyncio
import asyncpg
from models.database import DATABASE_CONFIG, init_database

async def test_db_connection():
    """PostgreSQL 연결 테스트"""
    try:
        print("PostgreSQL 연결 테스트 시작...")
        
        # 1. 데이터베이스 연결 테스트
        conn = await asyncpg.connect(
            host=DATABASE_CONFIG["host"],
            port=DATABASE_CONFIG["port"],
            user=DATABASE_CONFIG["user"],
            password=DATABASE_CONFIG["password"],
            database=DATABASE_CONFIG["database"]
        )
        print("✅ 데이터베이스 연결 성공")
        
        # 2. 테이블 생성 테스트
        await conn.execute("SELECT 1")
        print("✅ 쿼리 실행 성공")
        
        await conn.close()
        
        # 3. 데이터베이스 초기화 테스트
        await init_database()
        print("✅ 데이터베이스 초기화 성공")
        
        print("\n모든 데이터베이스 테스트 통과!")
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        print("\n해결 방법:")
        print("1. PostgreSQL이 설치되어 있는지 확인")
        print("2. PostgreSQL 서비스가 실행 중인지 확인")
        print("3. nh_consultation 데이터베이스가 생성되어 있는지 확인")
        print("   CREATE DATABASE nh_consultation;")

if __name__ == "__main__":
    asyncio.run(test_db_connection())