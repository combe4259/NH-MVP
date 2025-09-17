import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Any

@dataclass
class TextRegion:
    """PDF 내 텍스트 영역 정보"""
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]  # (x1, y1, x2, y2)

@dataclass
class GazeTextMatch:
    """시선과 텍스트 매칭 결과"""
    gaze_x: float
    gaze_y: float
    matched_text: str
    text_region: TextRegion
    distance: float
    confidence: float
    timestamp: float

class PDFCoordinateMapper:
    """PDF 좌표와 시선 좌표 매핑 클래스"""

    def __init__(self, tolerance_pixels=30):
        self.tolerance_pixels = tolerance_pixels
        self.text_regions: Dict[int, List[TextRegion]] = {}  # page_number -> regions
        self.scale_factor = 1.0
        self.viewport_offset = (0, 0)

    def load_pdf_text_regions(self, pdf_text_data: List[Dict[str, Any]]):
        """
        PDF.js에서 추출한 텍스트 영역 데이터를 로드

        Args:
            pdf_text_data: [{'text': str, 'page': int, 'bbox': [x1,y1,x2,y2]}, ...]
        """
        self.text_regions.clear()

        for item in pdf_text_data:
            page_num = item.get('page', 1)
            text = item.get('text', '').strip()
            bbox = item.get('bbox', [0, 0, 0, 0])

            if not text or len(text) < 2:
                continue

            region = TextRegion(
                text=text,
                page_number=page_num,
                bbox=tuple(bbox)
            )

            if page_num not in self.text_regions:
                self.text_regions[page_num] = []
            self.text_regions[page_num].append(region)

        # 각 페이지별로 y좌표순 정렬 (읽기 순서)
        for page_num in self.text_regions:
            self.text_regions[page_num].sort(key=lambda r: (r.bbox[1], r.bbox[0]))

    def set_pdf_viewport_info(self, scale_factor: float, viewport_offset: Tuple[float, float]):
        """PDF 뷰어의 스케일과 오프셋 정보 설정"""
        self.scale_factor = scale_factor
        self.viewport_offset = viewport_offset

    def map_gaze_to_text(self, gaze_x: float, gaze_y: float,
                        current_page: int = 1, timestamp: float = None) -> Optional[GazeTextMatch]:
        """시선 좌표를 PDF 텍스트에 매핑 (스크린 좌표 사용)"""
        if current_page not in self.text_regions:
            return None

        # 스크린 좌표를 그대로 사용 (프론트엔드에서 스크린 좌표로 전송)
        best_match = None
        min_distance = float('inf')

        for region in self.text_regions[current_page]:
            # 텍스트 영역의 경계 확인 (bbox가 스크린 좌표)
            x1, y1, x2, y2 = region.bbox
            
            # 시선이 텍스트 영역 내부에 있는지 확인
            if x1 <= gaze_x <= x2 and y1 <= gaze_y <= y2:
                # 영역 내부에 있으면 바로 매칭
                best_match = GazeTextMatch(
                    gaze_x=gaze_x,
                    gaze_y=gaze_y,
                    matched_text=region.text,
                    text_region=region,
                    distance=0,
                    confidence=1.0,
                    timestamp=timestamp or 0
                )
                return best_match
            
            # 영역 외부인 경우 중심점과 거리 계산
            region_center_x = (x1 + x2) / 2
            region_center_y = (y1 + y2) / 2
            
            distance = np.sqrt((gaze_x - region_center_x)**2 + (gaze_y - region_center_y)**2)

            # 허용 오차 내에서 가장 가까운 텍스트 찾기
            if distance <= self.tolerance_pixels and distance < min_distance:
                confidence = max(0, 1 - (distance / self.tolerance_pixels))

                best_match = GazeTextMatch(
                    gaze_x=gaze_x,
                    gaze_y=gaze_y,
                    matched_text=region.text,
                    text_region=region,
                    distance=distance,
                    confidence=confidence,
                    timestamp=timestamp or 0
                )
                min_distance = distance

        return best_match

    def get_reading_sequence(self, gaze_matches: List[GazeTextMatch]) -> List[Dict[str, Any]]:
        """시선 매칭 결과로부터 읽기 순서 추출"""
        if not gaze_matches:
            return []

        # 시간순 정렬
        sorted_matches = sorted(gaze_matches, key=lambda m: m.timestamp)

        # 연속된 같은 텍스트 그룹화
        reading_sequence = []
        current_text = None
        current_start = None
        current_end = None
        revisit_counts = {}

        for match in sorted_matches:
            text = match.matched_text

            if text != current_text:
                # 이전 텍스트 그룹 완료
                if current_text is not None:
                    duration = current_end - current_start
                    revisit_count = revisit_counts.get(current_text, 0)

                    reading_sequence.append({
                        'text': current_text,
                        'start_time': current_start,
                        'end_time': current_end,
                        'duration': duration,
                        'revisit_count': revisit_count
                    })

                # 새 텍스트 그룹 시작
                current_text = text
                current_start = match.timestamp
                current_end = match.timestamp
                revisit_counts[text] = revisit_counts.get(text, 0) + 1
            else:
                # 같은 텍스트 계속
                current_end = match.timestamp

        # 마지막 그룹 처리
        if current_text is not None:
            duration = current_end - current_start
            revisit_count = revisit_counts.get(current_text, 0)

            reading_sequence.append({
                'text': current_text,
                'start_time': current_start,
                'end_time': current_end,
                'duration': duration,
                'revisit_count': revisit_count
            })

        return reading_sequence