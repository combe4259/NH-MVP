import fitz  # PyMuPDF
import json
from typing import List, Dict, Optional

class PDFTextExtractor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)

    def find_text_coordinates(self, search_text: str) -> List[Dict]:
        """
        PDF에서 특정 텍스트를 찾고 좌표를 반환

        Returns:
            List[Dict]: 찾은 텍스트들의 좌표 정보
            [{
                "text": "찾은 텍스트",
                "page_number": 1,
                "x": 100,
                "y": 200,
                "width": 300,
                "height": 20,
                "bbox": [x0, y0, x1, y1]
            }]
        """
        results = []

        for page_num, page in enumerate(self.doc, 1):
            # 텍스트 검색
            text_instances = page.search_for(search_text)

            for inst in text_instances:
                x0, y0, x1, y1 = inst
                # 페이지 크기 정보 추가
                page_rect = page.rect
                result = {
                    "text": search_text,
                    "page_number": page_num,
                    "page_width": int(page_rect.width),
                    "page_height": int(page_rect.height),
                    "x": int(x0),
                    "y": int(y0),
                    "width": int(x1 - x0),
                    "height": int(y1 - y0),
                    "bbox": [x0, y0, x1, y1]
                }
                results.append(result)

        return results

    def extract_all_text_with_coordinates(self, page_num: int = 1) -> List[Dict]:
        """
        특정 페이지의 모든 텍스트와 좌표 추출
        """
        page = self.doc[page_num - 1]
        text_dict = page.get_text("dict")

        results = []
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        bbox = span["bbox"]
                        x0, y0, x1, y1 = bbox
                        result = {
                            "text": span["text"].strip(),
                            "page_number": page_num,
                            "x": int(x0),
                            "y": int(y0),
                            "width": int(x1 - x0),
                            "height": int(y1 - y0),
                            "font_size": span["size"],
                            "font_name": span["font"]
                        }
                        if result["text"]:  # 빈 텍스트 제외
                            results.append(result)

        return results

    def find_difficult_sentences(self, sentences: List[str]) -> List[Dict]:
        """
        어려운 문장들의 좌표를 찾아서 반환
        """
        results = []

        for sentence in sentences:
            # 문장이 길면 부분 검색도 시도
            coords = self.find_text_coordinates(sentence)

            if not coords and len(sentence) > 30:
                # 전체 문장이 안 찾아지면 앞부분만으로 검색
                partial_text = sentence[:20]
                coords = self.find_text_coordinates(partial_text)

            if coords:
                results.extend(coords)

        return results

    def close(self):
        self.doc.close()

# 사용 예시
def extract_pdf_coordinates(pdf_path: str, target_sentences: List[str]) -> Dict:
    """
    PDF에서 특정 문장들의 좌표를 추출하는 메인 함수
    """
    extractor = PDFTextExtractor(pdf_path)

    try:
        # 어려운 문장들의 좌표 찾기
        difficult_sentences = []

        for sentence in target_sentences:
            coords = extractor.find_text_coordinates(sentence)

            if coords:
                for coord in coords:
                    difficult_sentence = {
                        "sentence": sentence,
                        "sentence_id": f"sentence_{len(difficult_sentences) + 1:03d}",
                        "difficulty_score": 0.8,
                        "simplified_explanation": "법원에서 계좌를 막거나, 다른 사람이 그 돈에 대한 권리를 주장하면, 예금을 찾을 수 없게 됩니다.",
                        "original_position": len(difficult_sentences) + 1,
                        "location": {
                            "page_number": coord["page_number"],
                            "page_width": coord["page_width"],
                            "page_height": coord["page_height"],
                            "x": coord["x"],
                            "y": coord["y"],
                            "width": coord["width"],
                            "height": coord["height"]
                        }
                    }
                    difficult_sentences.append(difficult_sentence)

        return {
            "difficult_sentences": difficult_sentences,
            "overall_difficulty": 0.7,
            "difficult_terms": ["압류", "가압류", "질권설정"]
        }

    finally:
        extractor.close()

# Flask API 엔드포인트에서 사용할 함수
def analyze_pdf_text(pdf_path: str, section_text: str = None) -> Dict:
    """
    Flask API에서 호출할 메인 함수
    """
    # 찾을 어려운 문장들
    target_sentences = [
        "계좌에 압류, 가압류, 질권설정 등이 등록될 경우 원금 및 이자 지급 제한",
        "압류",
        "가압류",
        "질권설정"
    ]

    return extract_pdf_coordinates(pdf_path, target_sentences)

if __name__ == "__main__":
    # 테스트 실행
    pdf_path = "./NH내가Green초록세상예금.pdf"
    result = analyze_pdf_text(pdf_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))