"""
텍스트 난이도 자동 라벨링 프로그램
Google Colab에서 실행하세요.

사용법:
1. Google Colab에서 이 파일 업로드
2. GPU 런타임 설정
3. 실행: !python text_difficulty_labeler.py
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from huggingface_hub import login
import pandas as pd
from tqdm import tqdm
import re
import time
import os
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

# PDF 처리용 라이브러리
try:
    import pdfplumber
    PDF_SUPPORT = True
    # 개선된 추출기가 있으면 사용
    try:
        from improved_pdf_extractor import ImprovedPDFExtractor
        IMPROVED_EXTRACTOR = True
    except ImportError:
        IMPROVED_EXTRACTOR = False
except ImportError:
    PDF_SUPPORT = False
    IMPROVED_EXTRACTOR = False
    print("⚠️ PDF 지원을 위해 설치 필요: pip install pdfplumber")

class TextDifficultyLabeler:
    def __init__(self, model_name="google/gemma-2-2b-it", hf_token=None):
        """
        텍스트 난이도 라벨러 초기화

        Args:
            model_name: HuggingFace 모델명
            hf_token: HuggingFace 토큰 (gated 모델용)
        """
        self.model_name = model_name

        # HuggingFace 로그인 (필요시)
        if hf_token:
            login(token=hf_token)
            print("✅ HuggingFace 로그인 완료")

        # 모델 로드
        print(f"🔄 모델 로딩 중: {model_name}")
        self.load_model()
        print("✅ 모델 로딩 완료!")

        # 결과 저장용
        self.results = []

    def load_model(self):
        """모델과 토크나이저 로드"""
        try:
            # GPU 사용 가능 여부 확인
            if torch.cuda.is_available():
                print(f"🎮 GPU 사용 가능: {torch.cuda.get_device_name(0)}")
                # 4bit 양자화 설정 (새로운 방식)
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    dtype=torch.float16,  # torch_dtype 대신 dtype 사용
                )
            else:
                print("💻 CPU 모드로 실행")
                # CPU에서 실행
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="cpu",
                    dtype=torch.float32,  # CPU는 float32 사용
                )
        except Exception as e:
            print(f"⚠️ 4bit 로딩 실패, 일반 모드로 재시도: {e}")
            # 4bit 실패시 일반 로드
            if torch.cuda.is_available():
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    device_map="auto",
                    dtype=torch.float16,
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    dtype=torch.float32,
                ).to('cpu')

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

        # 디바이스 확인
        self.device = next(self.model.parameters()).device
        print(f"✅ 모델 디바이스: {self.device}")

        # 패딩 토큰 설정
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def create_prompt(self, text):
        """금융 문서 특화 10단계 난이도 평가 프롬프트 (단순화)"""

        # Few-shot 방식으로 변경
        prompt = f"""당신은 한국 금융 상품 설명서의 텍스트 난이도를 평가하는 전문가입니다.
아래 텍스트가 일반 고객이 이해하기 얼마나 어려운지 1-10으로 평가하세요.

예시:
"은행에 돈을 맡겨요" → 1
"통장에 이자가 붙어서 돈이 늘어났어요" → 2  
"정기예금은 정해진 기간 동안 돈을 맡기는 상품입니다" → 3
"자동이체를 신청하면 매달 정해진 날짜에 이체됩니다" → 4
"예금자보호법에 따라 5천만원까지 보호됩니다" → 5
"변동금리는 기준금리에 가산금리를 더하여 결정됩니다" → 6
"계좌에 압류, 가압류, 질권설정 등이 등록될 경우" → 7
"민사집행법에 따라 압류금지채권 범위 변경 신청" → 8
"신용파생결합증권의 CDS 스프레드 변동에 따른 수익구조" → 9
"IFRS 9 적용시 대손충당금 산출 및 Stage 분류 기준" → 10

평가 기준:
- 1-3: 일상어휘 (초등~중학생 이해 가능)
- 4-6: 금융기본용어 (일반인 이해 가능)
- 7-8: 법률/전문용어 (금융지식 필요)
- 9-10: 고급전문용어 (전문가 수준)

중요: 복잡한 구조, 전문용어, 숫자/비율이 많으면 난이도가 높습니다.

텍스트: "{text[:600]}"

난이도(1-10):"""

        return prompt

    def get_difficulty(self, text):
        """텍스트 난이도 평가 (순수 LLM 접근)"""

        # 여러 번 시도해서 안정적인 결과 얻기
        attempts = []
        for i in range(3):  # 3번 시도
            score = self._single_evaluation(text, attempt_num=i)
            if score != -1:  # 유효한 응답
                attempts.append(score)

        # 결과 처리
        if not attempts:
            print(f"[WARNING] 모든 시도 실패, 텍스트: {text[:50]}...")
            return 5  # 완전 실패시 중간값

        # 중앙값 반환 (outlier 제거)
        if len(attempts) >= 2:
            attempts.sort()
            return attempts[len(attempts)//2]

        return attempts[0]

    def _single_evaluation(self, text, attempt_num=0):
        """단일 평가 시도"""
        prompt = self.create_prompt(text)

        try:
            # 토크나이징 (프롬프트가 길어졌으므로 max_length 증가)
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024  # 768 → 1024로 증가
            )

            # 모델과 같은 디바이스로 이동
            if hasattr(self, 'device'):
                inputs = inputs.to(self.device)
            elif torch.cuda.is_available() and next(self.model.parameters()).is_cuda:
                inputs = inputs.to('cuda')
            else:
                inputs = inputs.to('cpu')

            # 생성 - 시도마다 약간 다른 설정
            temp_values = [0.1, 0.3, 0.5]
            temperature = temp_values[attempt_num % 3]

            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=5,        # 여유있게 5로 증가
                    temperature=temperature,
                    do_sample=(temperature > 0.1),
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    top_k=10,                # 상위 10개 토큰만
                    top_p=0.9
                )

            # 디코딩
            response = self.tokenizer.decode(
                outputs[0][inputs['input_ids'].shape[-1]:],
                skip_special_tokens=True
            ).strip()

            # 디버깅 (필요시)
            if attempt_num == 0:  # 첫 시도만 출력
                # print(f"[DEBUG] Response: '{response}' for: {text[:30]}...")
                pass

            # 파싱 - 더 유연하게
            # 정확한 매칭 우선
            if response == '10':
                return 10
            elif response in '123456789':
                return int(response)

            # 숫자로 시작하는 경우
            if response and response[0] == '1' and len(response) >= 2 and response[1] == '0':
                return 10
            elif response and response[0] in '123456789':
                return int(response[0])

            # 숫자가 포함된 경우 - 더 안전하게
            import re
            match = re.search(r'\d+', response)
            if match:
                num = int(match.group())
                # 1-10 범위만 허용
                if 1 <= num <= 10:
                    return num
                else:
                    # 범위 밖이면 가장 가까운 값으로 클리핑
                    if attempt_num == 0:
                        print(f"[WARNING] 범위 밖 난이도 {num} → 클리핑")
                    return min(max(num, 1), 10)

            return -1  # 파싱 실패

        except Exception as e:
            if attempt_num == 0:
                print(f"[ERROR] 평가 실패: {e}")
            return -1

    def label_texts(self, texts, batch_save=10, checkpoint_path=None):
        """
        텍스트 리스트 라벨링

        Args:
            texts: 텍스트 리스트
            batch_save: N개마다 중간 저장
            checkpoint_path: 체크포인트 파일 경로
        """
        # 체크포인트 확인
        processed_texts = set()
        if checkpoint_path and os.path.exists(checkpoint_path):
            checkpoint_df = pd.read_csv(checkpoint_path)
            processed_texts = set(checkpoint_df['text'].tolist())
            self.results = checkpoint_df.to_dict('records')
            print(f"📌 체크포인트 로드: {len(processed_texts)}개 이미 처리됨")

        # 라벨링 시작
        new_results = []

        for i, text in enumerate(tqdm(texts, desc="라벨링 진행")):
            # 이미 처리된 텍스트는 스킵
            if text in processed_texts:
                continue

            try:
                # 난이도 평가
                difficulty = self.get_difficulty(text)

                result = {
                    'text': text,
                    'difficulty': difficulty,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                new_results.append(result)
                self.results.append(result)

                # 배치 저장
                if checkpoint_path and len(new_results) % batch_save == 0:
                    self.save_checkpoint(new_results, checkpoint_path)
                    new_results = []

                # 속도 조절
                time.sleep(0.1)

            except Exception as e:
                print(f"❌ 에러 발생: {e}")
                print(f"   문제 텍스트: {text[:50]}...")
                continue

        # 마지막 배치 저장
        if checkpoint_path and new_results:
            self.save_checkpoint(new_results, checkpoint_path)

        print(f"✅ 라벨링 완료: 총 {len(self.results)}개")

        return pd.DataFrame(self.results)

    def save_checkpoint(self, new_results, checkpoint_path):
        """체크포인트 저장"""
        df = pd.DataFrame(new_results)
        if os.path.exists(checkpoint_path):
            df.to_csv(checkpoint_path, mode='a', header=False, index=False)
        else:
            df.to_csv(checkpoint_path, index=False)
        print(f"  💾 {len(new_results)}개 저장됨")

    def save_results(self, output_dir='/content/drive/MyDrive'):
        """결과 저장 (CSV, Excel, JSON)"""
        df = pd.DataFrame(self.results)

        if df.empty:
            print("⚠️ 저장할 데이터가 없습니다.")
            return

        # 타임스탬프
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # CSV 저장
        csv_path = os.path.join(output_dir, f'labeled_data_{timestamp}.csv')
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✅ CSV 저장: {csv_path}")

        # Excel 저장
        excel_path = os.path.join(output_dir, f'labeled_data_{timestamp}.xlsx')
        df.to_excel(excel_path, index=False, engine='openpyxl')
        print(f"✅ Excel 저장: {excel_path}")

        # JSON 저장 (Fine-tuning용)
        json_data = []
        for _, row in df.iterrows():
            json_data.append({
                "text": row['text'],
                "label": int(row['difficulty']) - 1,  # 0-9로 변환 (0-indexed)
                "difficulty": int(row['difficulty']),  # 원본 유지 (1-10)
                "difficulty_name": self._get_difficulty_name(int(row['difficulty']))
            })

        json_path = os.path.join(output_dir, f'training_data_{timestamp}.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        print(f"✅ JSON 저장: {json_path}")

        return csv_path, excel_path, json_path

    def _get_difficulty_name(self, level):
        """난이도 레벨에 대한 이름 반환"""
        names = {
            1: "아주 쉬움",
            2: "쉬움",
            3: "약간 쉬움",
            4: "보통-낮음",
            5: "보통",
            6: "보통-높음",
            7: "어려움",
            8: "매우 어려움",
            9: "전문가-상",
            10: "전문가-최상"
        }
        return names.get(level, f"Level {level}")

    def visualize_results(self, save_path=None):
        """결과 시각화"""
        df = pd.DataFrame(self.results)

        if df.empty:
            print("⚠️ 시각화할 데이터가 없습니다.")
            return

        # 그래프 생성
        fig, axes = plt.subplots(1, 2, figsize=(15, 5))

        # 1. 난이도 분포
        difficulty_counts = df['difficulty'].value_counts().sort_index()
        colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.9, 10))  # 초록(쉬움)→빨강(어려움)
        bar_colors = [colors[i-1] for i in difficulty_counts.index]

        axes[0].bar(difficulty_counts.index, difficulty_counts.values, color=bar_colors)
        axes[0].set_xlabel('난이도 레벨')
        axes[0].set_ylabel('텍스트 개수')
        axes[0].set_title('난이도 분포')
        axes[0].set_xticks(range(1, 11))
        axes[0].grid(axis='y', alpha=0.3)

        # 2. 난이도별 비율
        # 10단계 색상 그라데이션
        pie_colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.9, len(difficulty_counts)))

        axes[1].pie(difficulty_counts.values,
                    labels=[f'Lv{i}' for i in difficulty_counts.index],
                    colors=pie_colors,
                    autopct='%1.1f%%',
                    startangle=90)
        axes[1].set_title('난이도별 비율')

        plt.suptitle(f'텍스트 난이도 분석 결과 (총 {len(df)}개)', fontsize=16)
        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=100, bbox_inches='tight')
            print(f"✅ 그래프 저장: {save_path}")

        plt.show()

    def print_summary(self):
        """결과 요약 출력"""
        df = pd.DataFrame(self.results)

        if df.empty:
            print("⚠️ 데이터가 없습니다.")
            return

        print("\n" + "="*50)
        print("📊 라벨링 결과 요약")
        print("="*50)

        print(f"총 텍스트 수: {len(df)}개")
        print(f"\n난이도 분포:")

        difficulty_names = {
            1: "아주 쉬움 (초등 저학년)",
            2: "쉬움 (초등 고학년)",
            3: "약간 쉬움 (초·중간)",
            4: "보통-낮음 (중학생)",
            5: "보통 (중~고교)",
            6: "보통-높음 (복합문장)",
            7: "어려움 (고등학생)",
            8: "매우 어려움 (대학 전공)",
            9: "전문가-상 (전문용어)",
            10: "전문가-최상 (매우 전문적)"
        }

        for difficulty in range(1, 11):
            count = len(df[df['difficulty'] == difficulty])
            percentage = (count / len(df)) * 100 if len(df) > 0 else 0
            if count > 0:  # 존재하는 레벨만 출력
                print(f"  Level {difficulty:2d} - {difficulty_names[difficulty]}: {count}개 ({percentage:.1f}%)")

        print(f"\n평균 난이도: {df['difficulty'].mean():.2f}")
        print(f"중앙값: {df['difficulty'].median():.1f}")

        # 샘플 출력 (존재하는 레벨만)
        print("\n📝 샘플 텍스트:")
        for difficulty in sorted(df['difficulty'].unique()):
            samples = df[df['difficulty'] == difficulty].head(1)
            if not samples.empty:
                text = samples.iloc[0]['text']
                preview = text[:80] + "..." if len(text) > 80 else text
                print(f"\nLevel {difficulty}: {preview}")


# ============ 메인 실행 함수 ============

def extract_texts_from_pdf(pdf_path, split_mode='smart', use_improved=True):
    """
    PDF에서 텍스트 추출 (금융/법률 문서에 최적화)

    Args:
        pdf_path: PDF 파일 경로
        split_mode: 텍스트 분리 방식
            - 'smart': 지능형 분리 (번호 항목 + 문장 복합)
            - 'sentence': 문장 단위 분리
            - 'paragraph': 단락 단위 분리
            - 'bullet': 번호/기호 항목 단위
            - 'page': 페이지 단위
        use_improved: 개선된 추출기 사용 여부

    Returns:
        텍스트 리스트
    """
    if not PDF_SUPPORT:
        print("❌ pdfplumber가 설치되지 않았습니다.")
        print("   실행: pip install pdfplumber")
        return []

    # 개선된 추출기가 있고 사용하도록 설정된 경우
    if use_improved and IMPROVED_EXTRACTOR and split_mode == 'smart':
        print("🚀 개선된 PDF 추출기 사용")
        extractor = ImprovedPDFExtractor(pdf_path)
        return extractor.extract_all(mode='smart')

    texts = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"📄 PDF 파일 열기: {pdf_path}")
            print(f"   총 {len(pdf.pages)}페이지")
            print(f"   분리 모드: {split_mode}")

            # 전체 텍스트 추출
            all_text = ""
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    all_text += page_text + "\n"

            if split_mode == 'smart':
                # 지능형 분리: 금융/법률 문서에 최적화
                texts = extract_smart_segments(all_text)

            elif split_mode == 'sentence':
                # 기본 문장 단위 분리
                sentences = re.split(r'[.!?]+', all_text)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 10:
                        texts.append(sentence)

            elif split_mode == 'paragraph':
                # 단락 단위 분리 (줄바꿈 2개 이상)
                paragraphs = re.split(r'\n\n+', all_text)
                for para in paragraphs:
                    para = para.strip()
                    if len(para) > 20:
                        texts.append(para)

            elif split_mode == 'bullet':
                # 번호/기호 항목 단위 분리
                texts = extract_bullet_items(all_text)

            else:  # 'page' 또는 기타
                # 페이지 단위로 저장
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text and len(page_text.strip()) > 10:
                        texts.append(page_text.strip())

        print(f"✅ {len(texts)}개 텍스트 세그먼트 추출 완료")

        # 처음 3개 샘플 출력
        if texts:
            print("\n📝 추출된 텍스트 샘플:")
            for i, text in enumerate(texts[:3], 1):
                preview = text[:60] + "..." if len(text) > 60 else text
                print(f"   {i}. {preview}")

        return texts

    except Exception as e:
        print(f"❌ PDF 처리 오류: {e}")
        return []


def extract_smart_segments(text):
    """
    지능형 텍스트 분리 (금융/법률 문서 최적화)
    번호 항목, 조건절, 서브섹션 등을 개별적으로 분리
    """
    segments = []

    # 텍스트 전처리 - 테이블 구조 정리
    text = preprocess_text_for_extraction(text)

    # 1단계: 주요 섹션 분리 (대제목 기준)
    section_patterns = [
        r'^제\s*\d+\s*[조항관]',      # 제1조, 제2항 등
        r'^\d+\s*\.\s*[가-힣]+',      # 1. 제목
        r'^[A-Z]\.\s*',               # A. B. C.
        r'^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]\.',     # 로마 숫자
    ]

    # 2단계: 번호 항목 분리 (더 정확한 패턴)
    bullet_patterns = [
        r'^[①②③④⑤⑥⑦⑧⑨⑩]',        # 원 번호
        r'^[❶❷❸❹❺❻❼❽❾❿]',        # 검은 원 번호
        r'^[⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽]',        # 괄호 번호
        r'^\d+\)',                    # 1) 2) 3)
        r'^[가나다라마바사아자차]\)',  # 가) 나) 다)
        r'^[-•▪▫◦※]',                # 불릿 포인트
        r'^\*',                       # 별표
    ]

    # 모든 패턴 통합
    all_patterns = '|'.join(section_patterns + bullet_patterns)

    # 텍스트를 줄 단위로 분리
    lines = text.split('\n')
    current_segment = []
    current_type = None

    for i, line in enumerate(lines):
        original_line = line
        line = line.strip()

        if not line:
            # 빈 줄이 나오면 현재 세그먼트 종료
            if current_segment and len(' '.join(current_segment).strip()) > 10:
                segments.append(' '.join(current_segment).strip())
                current_segment = []
                current_type = None
            continue

        # 테이블 헤더 감지 (서비스구분, 우대내용 등)
        if is_table_header(line):
            # 현재 세그먼트 저장
            if current_segment:
                segments.append(' '.join(current_segment).strip())
                current_segment = []
            # 테이블 처리
            table_segments = extract_table_segments(lines[i:])
            segments.extend(table_segments)
            # 테이블 부분 스킵
            skip_lines = count_table_lines(lines[i:])
            for _ in range(skip_lines - 1):
                if i < len(lines) - 1:
                    i += 1
            continue

        # 패턴 매칭 확인
        pattern_match = re.match(all_patterns, line)

        if pattern_match:
            # 이전 세그먼트 저장
            if current_segment:
                segment_text = ' '.join(current_segment).strip()
                if len(segment_text) > 10:
                    segments.append(segment_text)
            # 새 세그먼트 시작
            current_segment = [line]
            current_type = detect_segment_type(line)
        else:
            # 들여쓰기나 연속된 내용인 경우
            if current_segment:
                # 같은 세그먼트에 추가
                current_segment.append(line)
            else:
                # 독립적인 텍스트
                if len(line) > 10:
                    segments.append(line)

    # 마지막 세그먼트 저장
    if current_segment:
        segment_text = ' '.join(current_segment).strip()
        if len(segment_text) > 10:
            segments.append(segment_text)

    # 후처리: 너무 긴 세그먼트는 다시 분리
    final_segments = []
    for seg in segments:
        if len(seg) > 500:  # 500자 이상이면
            # 문장 단위로 다시 분리
            sub_sentences = re.split(r'(?<=[.!?])\s+', seg)
            for sub in sub_sentences:
                if len(sub.strip()) > 10:
                    final_segments.append(sub.strip())
        else:
            final_segments.append(seg)

    # 중복 제거
    unique_segments = []
    seen = set()

    for seg in final_segments:
        normalized = ' '.join(seg.split())
        if normalized not in seen and len(normalized) > 10:
            seen.add(normalized)
            unique_segments.append(normalized)

    return unique_segments


def preprocess_text_for_extraction(text):
    """
    텍스트 전처리 - 테이블이나 특수 구조 정리
    """
    # 간단한 접근: 한글 단어 단위로 중복 제거
    # 자금조달금리 → 자금조달금리 (변화 없음)
    # 자자자금금금조조조달달달금금금리리리 → 자금조달금리

    import re

    # 방법 1: 한글 2음절 이상 단위가 정확히 3번 반복되는 패턴
    # 예: (자금)(자금)(자금) → (자금)
    # 하지만 이것도 잘못될 수 있음

    # 방법 2: 더 간단하게 - 한글 1음절이 정확히 3번 연속 반복
    # 자자자금금금 → 자금
    result = []
    i = 0

    while i < len(text):
        # 현재 문자가 한글이고, 다음 2개가 같은 문자인지 확인
        if i + 2 < len(text) and '가' <= text[i] <= '힣':
            if text[i] == text[i+1] == text[i+2]:
                # 3개가 같으면 하나만 추가
                result.append(text[i])
                i += 3
            else:
                result.append(text[i])
                i += 1
        else:
            result.append(text[i])
            i += 1

    text = ''.join(result)

    # 연속된 공백을 단일 공백으로
    text = re.sub(r'[ \t]+', ' ', text)

    # 테이블 구분자 처리
    text = re.sub(r'(\S)\s{3,}(\S)', r'\1 | \2', text)  # 3개 이상 공백은 구분자로

    # 특수 bullet 문자 정규화 (선택사항)
    text = text.replace('‣', '•')
    text = text.replace('➜', '→')

    return text


def is_table_header(line):
    """
    테이블 헤더인지 확인
    """
    table_headers = [
        '서비스구분', '우대내용', '우대조건', '적용기준',
        '구분', '내용', '조건', '비고', '항목', '설명'
    ]

    for header in table_headers:
        if header in line and len(line.split()) <= 5:
            return True
    return False


def extract_table_segments(lines):
    """
    테이블 형식의 데이터를 세그먼트로 추출
    """
    segments = []
    current_row = []

    for line in lines:
        line = line.strip()

        # 테이블 끝 감지
        if not line or re.match(r'^[①②③④⑤]', line):
            if current_row:
                segments.append(' '.join(current_row))
            break

        # 번호 항목이 있는 행
        if re.match(r'^[❶❷❸❹❺❻❼❽❾❿]', line):
            if current_row:
                segments.append(' '.join(current_row))
            current_row = [line]
        else:
            if current_row:
                current_row.append(line)

    if current_row:
        segments.append(' '.join(current_row))

    return [s for s in segments if len(s) > 10]


def count_table_lines(lines):
    """
    테이블이 차지하는 줄 수 계산
    """
    count = 0
    for line in lines:
        line = line.strip()
        if not line or re.match(r'^[①②③④⑤]', line):
            break
        count += 1
    return count


def detect_segment_type(line):
    """
    세그먼트 타입 감지
    """
    if re.match(r'^[①②③④⑤⑥⑦⑧⑨⑩]', line):
        return 'main_item'
    elif re.match(r'^[❶❷❸❹❺❻❼❽❾❿]', line):
        return 'sub_item'
    elif re.match(r'^제\s*\d+\s*[조항관]', line):
        return 'article'
    elif re.match(r'^\d+\)', line):
        return 'numbered'
    else:
        return 'other'


def extract_bullet_items(text):
    """
    번호/기호 항목만 추출
    """
    items = []

    # 번호/기호 패턴
    patterns = [
        (r'[①②③④⑤⑥⑦⑧⑨⑩]', '원번호'),
        (r'[❶❷❸❹❺❻❼❽❾❿]', '검은원'),
        (r'\d+\)', '숫자괄호'),
        (r'[가나다라마바사아자차]\)', '한글괄호'),
        (r'[-•▪▫◦]', '불릿'),
    ]

    lines = text.split('\n')
    current_item = []
    current_type = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 패턴 매칭
        matched = False
        for pattern, ptype in patterns:
            if re.match(f'^{pattern}', line):
                # 이전 항목 저장
                if current_item:
                    item_text = ' '.join(current_item).strip()
                    if len(item_text) > 10:
                        items.append(item_text)

                # 새 항목 시작
                current_item = [line]
                current_type = ptype
                matched = True
                break

        if not matched and current_item:
            # 현재 항목에 계속 추가
            current_item.append(line)

    # 마지막 항목 저장
    if current_item:
        item_text = ' '.join(current_item).strip()
        if len(item_text) > 10:
            items.append(item_text)

    return items


def extract_texts_from_multiple_pdfs(pdf_paths, split_mode='smart'):
    """
    여러 PDF에서 텍스트 추출

    Args:
        pdf_paths: PDF 파일 경로 리스트
        split_mode: 텍스트 분리 방식 (smart/sentence/paragraph/bullet/page)

    Returns:
        모든 텍스트 리스트
    """
    all_texts = []

    for pdf_path in pdf_paths:
        texts = extract_texts_from_pdf(pdf_path, split_mode)
        all_texts.extend(texts)

    print(f"\n📊 전체 추출 결과:")
    print(f"   • PDF 파일 수: {len(pdf_paths)}개")
    print(f"   • 총 텍스트 세그먼트: {len(all_texts)}개")

    return all_texts


def main():
    """메인 실행 함수"""

    # Colab 환경 확인
    try:
        from google.colab import drive
        drive.mount('/content/drive')
        print("✅ Google Drive 마운트 완료")
        is_colab = True
    except:
        print("⚠️ 로컬 환경에서 실행 중...")
        is_colab = False

    # PDF 지원 확인
    if not PDF_SUPPORT:
        print("\n📌 PDF 처리를 위해 설치:")
        print("   !pip install pdfplumber")

    # 설정
    HF_TOKEN = "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"  # 환경 변수나 별도 파일에서 로드하세요

    # 모델 선택 (하나만 주석 해제)
    #MODEL_NAME = "google/gemma-2-2b-it"  # 기존 (2B)
    MODEL_NAME = "google/gemma-2-9b-it"  # 더 큰 Gemma (9B) ⭐
    # MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"  # Mistral (7B)
    # MODEL_NAME = "microsoft/Phi-3.5-mini-instruct"  # Phi (3.8B)
    # MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"  # Llama (3B)

    # 출력 디렉토리 설정
    if is_colab:
        OUTPUT_DIR = "/content/drive/MyDrive/text_difficulty_labels"
    else:
        OUTPUT_DIR = "./labeled_data"

    # 출력 디렉토리 생성
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 라벨러 초기화
    labeler = TextDifficultyLabeler(
        model_name=MODEL_NAME,
        hf_token=HF_TOKEN  # None이면 환경변수에서 자동으로 찾음
    )

    # ===== 텍스트 준비 =====

    # split_mode 옵션:
    # - 'smart': 지능형 분리 (금융/법률 문서 추천) ⭐
    # - 'sentence': 문장 단위 분리
    # - 'paragraph': 단락 단위 분리
    # - 'bullet': 번호/기호 항목 단위
    # - 'page': 페이지 단위

    #옵션 1: 단일 PDF (smart 모드 사용)
    #pdf_path = "/content/drive/MyDrive/10000831_pi.pdf"
    #texts = extract_texts_from_pdf(pdf_path, split_mode='smart')

    #옵션 2: 여러 PDF 파일 직접 지정
    #pdf_files = [
    #    "/content/drive/MyDrive/doc1.pdf",
    #    "/content/drive/MyDrive/doc2.pdf",
    #]
    #texts = extract_texts_from_multiple_pdfs(pdf_files, split_mode='smart')

    #옵션 3: 여러 폴더에서 모든 PDF 자동 수집 ⭐
    import glob

    # 폴더 목록
    folders = [
        "/content/drive/MyDrive/ELS",
        "/content/drive/MyDrive/대출",
        "/content/drive/MyDrive/대출 약관",
        "/content/drive/MyDrive/외환",
        "/content/drive/MyDrive/저축"
    ]

    # 모든 PDF 파일 수집
    all_pdf_files = []
    for folder in folders:
        # 각 폴더에서 PDF 파일 찾기
        pdf_pattern = f"{folder}/*.pdf"
        pdf_files = glob.glob(pdf_pattern)

        # 하위 폴더도 포함하려면
        pdf_pattern_recursive = f"{folder}/**/*.pdf"
        pdf_files_recursive = glob.glob(pdf_pattern_recursive, recursive=True)

        # 합치기
        all_files = list(set(pdf_files + pdf_files_recursive))
        all_pdf_files.extend(all_files)

        print(f"📁 {folder}: {len(all_files)}개 PDF 발견")

    print(f"\n📚 총 {len(all_pdf_files)}개 PDF 파일 발견")

    # 파일 목록 출력 (선택사항)
    if len(all_pdf_files) <= 10:
        print("\n파일 목록:")
        for i, file in enumerate(all_pdf_files, 1):
            print(f"  {i}. {file.split('/')[-1]}")
    else:
        print(f"\n처음 10개 파일:")
        for i, file in enumerate(all_pdf_files[:10], 1):
            print(f"  {i}. {file.split('/')[-1]}")
        print(f"  ... 외 {len(all_pdf_files)-10}개")

    # 모든 PDF에서 텍스트 추출
    texts = extract_texts_from_multiple_pdfs(all_pdf_files, split_mode='smart')



    print(f"📚 총 {len(texts)}개 텍스트 준비 완료")

    # 라벨링 실행
    checkpoint_path = os.path.join(OUTPUT_DIR, "checkpoint.csv")
    df_results = labeler.label_texts(
        texts=texts,
        batch_save=10,
        checkpoint_path=checkpoint_path
    )

    # 결과 요약
    labeler.print_summary()

    # 결과 저장
    csv_path, excel_path, json_path = labeler.save_results(OUTPUT_DIR)

    # 시각화
    graph_path = os.path.join(OUTPUT_DIR, "difficulty_distribution.png")
    labeler.visualize_results(save_path=graph_path)

    print("\n" + "="*50)
    print("🎉 모든 작업 완료!")
    print("="*50)
    print(f"저장된 파일:")
    print(f"  📄 CSV: {csv_path}")
    print(f"  📊 Excel: {excel_path}")
    print(f"  📋 JSON: {json_path}")
    print(f"  📈 그래프: {graph_path}")

    return df_results


# 실행
if __name__ == "__main__":
    results = main()