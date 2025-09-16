import os
from dotenv import load_dotenv
import asyncpg
import asyncio

load_dotenv()

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )
        print('✅ PostgreSQL 연결 성공!')

        # 테이블 목록 확인
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        print('📋 테이블 목록:')
        for table in tables:
            print(f'  - {table["table_name"]}')

        await conn.close()

    except Exception as e:
        print(f'❌ PostgreSQL 연결 실패: {e}')

if __name__ == "__main__":
    asyncio.run(test_connection())