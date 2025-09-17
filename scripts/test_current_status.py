#!/usr/bin/env python3
"""
현재 시스템 상태 확인 스크립트
"""
import requests
import json
from datetime import datetime

def check_backend_status():
    """백엔드 서버 상태 확인"""
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"✅ 백엔드 서버 실행 중: {response.status_code}")
    except Exception as e:
        print(f"❌ 백엔드 서버 연결 실패: {e}")

def check_ai_models():
    """AI 모델 상태 확인"""
    try:
        # 얼굴 분석 CNN-LSTM 모델 테스트
        test_data = {
            "frames": [[0.5] * 1024] * 30  # 30프레임의 더미 데이터
        }
        response = requests.post("http://localhost:8000/api/face/analyze-sequence", 
                                json=test_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ CNN-LSTM 얼굴 분석 모델 작동 중")
            print(f"   - Confusion probability: {result.get('confusion_probability', 0):.2f}")
        else:
            print(f"⚠️ CNN-LSTM 모델 응답 오류: {response.status_code}")
    except Exception as e:
        print(f"❌ CNN-LSTM 모델 연결 실패: {e}")

def check_eyetracking_flow():
    """아이트래킹 통합 플로우 확인"""
    test_data = {
        "consultation_id": "29853704-6f54-4df2-bb40-6efa9a63cf53",
        "customer_id": "069efa8e-8d80-4700-9355-ec57caca3fe0",
        "current_section": "테스트 섹션",
        "section_text": "테스트 텍스트입니다.",
        "reading_time": 3000,
        "gaze_data": {
            "raw_points": [{"x": 500, "y": 300, "timestamp": datetime.now().timestamp()}],
            "fixation_count": 10,
            "saccade_count": 5,
            "regression_count": 2,
            "total_duration": 3000
        },
        "face_analysis": {
            "confusion_probability": 0.7,
            "emotions": {"neutral": 0.3}
        }
    }
    
    try:
        response = requests.post("http://localhost:8000/api/eyetracking/analyze", 
                                json=test_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 아이트래킹 통합 분석 작동 중")
            print(f"   - 통합 이해도: {result.get('integrated_comprehension', 0):.2f}")
            print(f"   - AI 도우미 트리거: {result.get('ai_triggered', False)}")
        else:
            print(f"⚠️ 통합 분석 응답 오류: {response.status_code}")
            print(f"   응답: {response.text}")
    except Exception as e:
        print(f"❌ 통합 분석 연결 실패: {e}")

def check_pdf_text_extraction():
    """PDF 텍스트 추출 확인"""
    test_regions = [
        {"text": "테스트 텍스트1", "page": 1, "bbox": [100, 100, 200, 120]},
        {"text": "테스트 텍스트2", "page": 1, "bbox": [100, 150, 200, 170]}
    ]
    
    test_data = {
        "consultation_id": "test-123",
        "customer_id": "069efa8e-8d80-4700-9355-ec57caca3fe0",
        "current_section": "PDF 테스트",
        "section_text": "",  # 백엔드에서 추출
        "reading_time": 1000,
        "pdf_text_regions": test_regions,
        "gaze_data": {
            "raw_points": [{"x": 150, "y": 110, "timestamp": datetime.now().timestamp()}],
            "fixation_count": 5,
            "saccade_count": 2,
            "regression_count": 0,
            "total_duration": 1000
        }
    }
    
    try:
        response = requests.post("http://localhost:8000/api/eyetracking/analyze", 
                                json=test_data)
        if response.status_code == 200:
            print(f"✅ PDF 텍스트 매핑 테스트 완료")
            # 백엔드 로그에서 실제 매핑 결과 확인 필요
        else:
            print(f"⚠️ PDF 텍스트 매핑 오류: {response.status_code}")
    except Exception as e:
        print(f"❌ PDF 텍스트 매핑 실패: {e}")

if __name__ == "__main__":
    print("="*50)
    print("시스템 상태 확인 중...")
    print("="*50)
    
    check_backend_status()
    print()
    check_ai_models()
    print()
    check_eyetracking_flow()
    print()
    check_pdf_text_extraction()
    
    print("="*50)
    print("✨ 상태 확인 완료")
    print("="*50)