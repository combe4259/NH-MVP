"""
Gemma를 사용한 금융 텍스트 간소화 및 난이도 평가
기존 JSON 파일의 문장들을 쉽게 변환하고 난이도를 평가
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
try:
    from transformers import BitsAndBytesConfig
    BNBCONFIG_AVAILABLE = True
except ImportError:
    BNBCONFIG_AVAILABLE = False
    print("⚠️ BitsAndBytesConfig not available")
from huggingface_hub import login
import json
from tqdm import tqdm
import os
from datetime import datetime
from typing import List, Dict

class GemmaTextSimplifier:
    def __init__(self, hf_token=""):
        """
        Gemma 기반 텍스트 간소화 및 난이도 평가
        """
        self.model_name = "google/gemma-2-2b-it"
        
        # HuggingFace 로그인
        if hf_token:
            login(token=hf_token)
            print("✅ HuggingFace 로그인 완료")
        
        # 모델 로드
        print(f"🔄 Gemma 모델 로딩 중...")
        self.load_model()
        print("✅ 모델 로딩 완료!")
        
        # 결과 저장용
        self.results = []
    
    def load_model(self):
        """모델과 토크나이저 로드"""
        try:
            # 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # GPU 사용 가능 여부 확인
            if torch.cuda.is_available():
                print(f"🎮 GPU 사용: {torch.cuda.get_device_name(0)}")
                self.device = "cuda"
                
                # BitsAndBytes 사용 가능하면 4bit 양자화 시도
                if BNBCONFIG_AVAILABLE:
                    try:
                        print("🔧 4bit 양자화 시도...")
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_use_double_quant=True,
                            bnb_4bit_quant_type="nf4"
                        )
                        self.model = AutoModelForCausalLM.from_pretrained(
                            self.model_name,
                            quantization_config=quantization_config,
                            device_map="auto"
                        )
                        print("✅ 4bit 양자화 성공!")
                    except Exception as e:
                        print(f"⚠️ 4bit 실패, 일반 모드: {e}")
                        self.model = AutoModelForCausalLM.from_pretrained(
                            self.model_name,
                            device_map="auto",
                            dtype=torch.float16
                        )
                else:
                    # 양자화 없이 일반 로드
                    print("📦 일반 모드 로드 (양자화 없음)")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        self.model_name,
                        device_map="auto",
                        dtype=torch.float16
                    )
            elif torch.backends.mps.is_available():
                print("🍎 MPS (Mac GPU) 사용")
                self.device = "mps"
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="mps",
                    dtype=torch.float16
                )
            else:
                print("💻 CPU 모드")
                self.device = "cpu"
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="cpu",
                    dtype=torch.float32
                )
        except Exception as e:
            print(f"⚠️ 양자화 실패, 일반 모드로 재시도: {e}")
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                device_map="auto"
            )
    
    def simplify_text(self, text: str) -> str:
        """복잡한 금융 텍스트를 쉬운 말로 변환"""
        
        prompt = f"""아래 문장을 쉬운 한국어로 다시 써주세요. 원본 문장의 의미를 정확히 유지하면서 어려운 단어만 쉽게 바꿔주세요.

원본 문장: {text}

위 문장을 초등학생도 이해할 수 있도록 쉽게 다시 쓰면:"""
        
        try:
            # 토크나이징
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )
            
            # 모델과 같은 디바이스로 이동
            if hasattr(self, 'device'):
                inputs = inputs.to(self.device)
            
            # 생성
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=100,
                    temperature=0.3,  # 낮춰서 더 안정적으로
                    do_sample=True,
                    top_p=0.85,
                    top_k=50,
                    repetition_penalty=1.1,  # 반복 방지
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # 디코딩
            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[-1]:],
                skip_special_tokens=True
            ).strip()
            
            # 응답에서 첫 문장만 추출 (더 깔끔하게)
            if '.' in response:
                response = response.split('.')[0] + '.'
            
            return response
            
        except Exception as e:
            print(f"[ERROR] 변환 실패: {e}")
            return text  # 실패시 원본 반환
    
    def process_json_file(self, input_path: str, output_path: str = None):
        """JSON 파일 처리: 원본 -> 간소화 -> 난이도 매핑"""
        
        # 출력 경로 설정
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"simplified_data_{timestamp}.json"
        
        # JSON 파일 로드
        print(f"📂 Loading: {input_path}")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 데이터 형식 확인
        if isinstance(data, dict) and 'sentences' in data:
            sentences = data['sentences']
        elif isinstance(data, list):
            sentences = data
        else:
            print("⚠️ 지원하지 않는 JSON 형식입니다.")
            return
        
        print(f"📊 총 {len(sentences)} 개 문장 처리 시작")
        
        # 결과 저장용
        results = []
        
        # 각 문장 처리
        for item in tqdm(sentences, desc="Processing"):
            # 원본 텍스트와 난이도 추출
            if isinstance(item, dict):
                original_text = item.get('text', item.get('sentence', str(item)))
                # 기존 난이도가 있으면 사용, 없으면 기본값 5
                difficulty = item.get('difficulty', item.get('score', 5))
            else:
                original_text = str(item)
                difficulty = 5  # 기본값
            
            # 간소화만 수행 (난이도 평가 제거)
            simplified_text = self.simplify_text(original_text)
            
            # 결과 저장
            result = {
                "complex": original_text,  # 학습 데이터 형식에 맞춤
                "simple": simplified_text,
                "difficulty": difficulty  # 기존 난이도 사용
            }
            
            results.append(result)
            
            # 진행상황 출력 (10개마다)
            if len(results) % 10 == 0:
                print(f"✅ {len(results)} 개 완료")
                # 샘플 출력
                print(f"  원본: {original_text[:50]}...")
                print(f"  변환: {simplified_text[:50]}...")
                print(f"  난이도: {difficulty}")
        
        # JSON 파일로 저장
        output_data = {
            "metadata": {
                "source_file": input_path,
                "processed_date": datetime.now().isoformat(),
                "total_sentences": len(results),
                "model": self.model_name
            },
            "data": results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 처리 완료!")
        print(f"📄 결과 저장: {output_path}")
        
        # 통계 출력
        self.print_statistics(results)
        
        return results
    
    def print_statistics(self, results: List[Dict]):
        """처리 결과 통계 출력"""
        
        if not results:
            return
        
        # 통계 계산
        difficulties = [r['difficulty'] for r in results]
        
        print("\n📊 통계 정보:")
        print("-" * 40)
        print(f"총 처리 문장: {len(results)} 개")
        print(f"평균 난이도: {sum(difficulties) / len(difficulties):.2f}")
        print(f"최대 난이도: {max(difficulties)}")
        print(f"최소 난이도: {min(difficulties)}")
        
        # 난이도 분포
        print("\n난이도 분포:")
        for level in range(1, 11):
            count = sum(1 for d in difficulties if d == level)
            if count > 0:
                bar = "█" * (count * 30 // len(results))
                print(f"  {level:2d}: {count:3d}개 {bar}")
        
        # 샘플 출력
        print("\n📝 샘플 결과 (높은 난이도 순):")
        print("-" * 40)
        sorted_results = sorted(results, key=lambda x: x['difficulty'], reverse=True)
        
        for i, result in enumerate(sorted_results[:3], 1):
            print(f"\n[{i}] 난이도 {result['difficulty']}")
            print(f"원본: {result['complex'][:80]}...")
            print(f"변환: {result['simple'][:80]}...")


def main():
    """메인 실행 함수"""
    
    print("=" * 50)
    print("Gemma 텍스트 간소화 시스템")
    print("=" * 50)
    
    # 간소화 시스템 초기화
    simplifier = GemmaTextSimplifier()
    
    # 입력 파일 경로
    input_file = "/content/training_data_20250910_092856.json"
    
    # 파일 존재 확인
    if not os.path.exists(input_file):
        print(f"❌ 파일을 찾을 수 없습니다: {input_file}")
        # 대화형 모드
        print("\n대화형 모드로 전환합니다.")
        while True:
            text = input("\n복잡한 문장 입력 (종료: quit): ").strip()
            if text.lower() == 'quit':
                break
            
            simplified = simplifier.simplify_text(text)
            
            print(f"\n원본: {text}")
            print(f"변환: {simplified}")
    else:
        # 파일 처리
        output_file = "financial_training_simplified.json"
        results = simplifier.process_json_file(input_file, output_file)
        
        print(f"\n✅ 모든 처리 완료!")
        print(f"결과 파일: {output_file}")


if __name__ == "__main__":
    main()