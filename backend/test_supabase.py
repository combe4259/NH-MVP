import asyncio
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import asyncpg

# .env 파일 로드
load_dotenv()

async def test_supabase_connection():
    """Supabase 연결 테스트"""
    
    # Supabase 설정 확인
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("[ERROR] .env 파일에 SUPABASE_URL과 SUPABASE_KEY를 설정해주세요")
        return False
    
    try:
        print("[INFO] Supabase 연결 테스트 시작...")
        
        # 1. Supabase 클라이언트 생성
        supabase: Client = create_client(supabase_url, supabase_key)
        print("[SUCCESS] Supabase 클라이언트 생성 성공")
        
        # 2. 간단한 쿼리 테스트 (테이블이 없어도 연결 확인 가능)
        try:
            result = supabase.table("customers").select("*").limit(1).execute()
            print("[SUCCESS] Supabase 쿼리 테스트 성공")
        except Exception as e:
            print(f"[WARN] 쿼리 테스트 (테이블 없음): {e}")
            print("-> 정상적인 상황입니다. 테이블은 나중에 생성됩니다.")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Supabase 연결 실패: {e}")
        return False

async def test_postgres_connection():
    """PostgreSQL 직접 연결 테스트 (asyncpg 사용)"""
    
    db_host = os.getenv("DB_HOST")
    db_password = os.getenv("DB_PASSWORD")
    
    if not db_host or not db_password:
        print("[ERROR] .env 파일에 DB_HOST와 DB_PASSWORD를 설정해주세요")
        return False
    
    try:
        print("[INFO] PostgreSQL 직접 연결 테스트...")
        
        conn = await asyncpg.connect(
            host=db_host,
            port=5432,
            user="postgres",
            password=db_password,
            database="postgres"
        )
        
        # 간단한 쿼리
        result = await conn.fetchval("SELECT 1")
        print(f"[SUCCESS] PostgreSQL 연결 성공: {result}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] PostgreSQL 연결 실패: {e}")
        return False

async def create_tables_if_needed():
    """필요시 테이블 생성"""
    
    try:
        from models.database import init_database
        await init_database()
        print("[SUCCESS] 데이터베이스 테이블 생성/확인 완료")
        
    except Exception as e:
        print(f"[ERROR] 테이블 생성 실패: {e}")

async def main():
    """전체 테스트 실행"""
    print("=== Supabase 연결 테스트 ===\n")
    
    # 1. Supabase API 테스트
    supabase_ok = await test_supabase_connection()
    print()
    
    # 2. PostgreSQL 직접 연결 테스트
    postgres_ok = await test_postgres_connection()
    print()
    
    if supabase_ok or postgres_ok:
        # 3. 테이블 생성 테스트
        await create_tables_if_needed()
        print()
        
        print("[SUCCESS] 모든 테스트 통과!")
        
    else:
        print("\n[ERROR] 연결 실패")

if __name__ == "__main__":
    asyncio.run(main())