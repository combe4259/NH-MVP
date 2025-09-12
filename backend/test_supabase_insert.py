import os
import uuid
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timezone

load_dotenv()

# Supabase 클라이언트 초기화
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

print(f"URL: {supabase_url}")
print(f"KEY 존재: {'Yes' if supabase_key else 'No'}")

if supabase_url and supabase_key:
    supabase: Client = create_client(supabase_url, supabase_key)
    
    try:
        consultation_id = str(uuid.uuid4())
        customer_id = str(uuid.uuid4())
        
        # 1. 고객 생성
        customer_data = {
            "id": customer_id,
            "name": "테스트 고객"
        }
        print("고객 생성...")
        customer_result = supabase.table("customers").insert(customer_data).execute()
        print(f"고객 생성 성공: {customer_result.data}")
        
        # 2. 상담 생성
        consultation_data = {
            "id": consultation_id,
            "customer_id": customer_id,
            "product_type": "예금상품",
            "product_details": {"type": "정기예금"}
        }
        print("상담 생성...")
        consultation_result = supabase.table("consultations").insert(consultation_data).execute()
        print(f"상담 생성 성공: {consultation_result.data}")
        
        # 3. 분석 데이터 삽입
        analysis_data = {
            "consultation_id": consultation_id,
            "customer_id": customer_id,
            "section_name": "직접테스트",
            "section_text": "복리와 중도해지에 대한 설명입니다.",
            "difficulty_score": 0.75,
            "confusion_probability": 0.65,
            "comprehension_level": "medium",
            "gaze_data": {"fixations": [{"x": 100, "y": 200, "duration": 300}]},
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print("분석 데이터 삽입...")
        analysis_result = supabase.table("reading_analysis").insert(analysis_data).execute()
        print(f"분석 데이터 성공! 결과: {analysis_result.data}")
        
    except Exception as e:
        print(f"삽입 실패: {e}")
else:
    print("Supabase 환경변수가 설정되지 않음")