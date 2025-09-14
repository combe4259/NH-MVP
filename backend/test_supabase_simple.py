import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

try:
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')

    print(f"연결 시도: {supabase_url}")

    # Supabase 클라이언트 생성
    supabase = create_client(supabase_url, supabase_key)

    # 테이블 목록 확인
    response = supabase.table('customers').select('*').limit(1).execute()
    print("연결 성공! customers 테이블 조회됨")
    print(f"데이터: {response.data}")

except Exception as e:
    print(f"연결 실패: {e}")