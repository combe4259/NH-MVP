#!/usr/bin/env python
"""
AI 모델 테스트 스크립트
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

async def test_models():
    from services.ai_model_service import ai_model_manager
    
    # 테스트 텍스트
    complex_text = "중도해지 시 우대금리가 적용되지 않으며, 예금자보호법에 의해 원금과 이자를 합하여 1인당 5천만원까지 보호됩니다."
    
    print("=" * 50)
    print("AI 모델 테스트 시작")
    print("=" * 50)
    
    # 1. 난이도 분석 테스트
    print("\n1. 텍스트 난이도 분석 테스트:")
    print(f"입력: {complex_text}")
    
    if ai_model_manager.current_model:
        difficulty = await ai_model_manager.current_model.analyze_difficulty(complex_text)
        print(f"난이도 점수: {difficulty}")
        
        # 2. 텍스트 간소화 테스트
        print("\n2. 텍스트 간소화 테스트:")
        if hasattr(ai_model_manager.current_model, 'simplify_text'):
            simplified = await ai_model_manager.current_model.simplify_text(complex_text)
            print(f"간소화된 텍스트: {simplified}")
        
        # 3. AI 설명 생성 테스트
        print("\n3. AI 설명 생성 테스트:")
        explanation = await ai_model_manager.current_model.generate_explanation(complex_text, difficulty)
        print(f"AI 설명: {explanation}")
        
        # 4. 통합 분석 테스트
        print("\n4. 통합 분석 테스트:")
        result = await ai_model_manager.analyze_text(complex_text)
        print(f"통합 분석 결과:")
        for key, value in result.items():
            print(f"  - {key}: {value}")
    else:
        print("AI 모델이 로드되지 않았습니다.")
    
    print("\n" + "=" * 50)
    print("테스트 완료")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(test_models())