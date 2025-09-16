import numpy as np
import time
from collections import deque
from typing import Dict, Optional, Any
from fixation_detector import FixationPoint, FixationDetector
from pdf_coordinate_mapper import GazeTextMatch, PDFCoordinateMapper

class ReadingDataCollector:
    """AI 전송용 간단한 데이터 수집기"""

    def __init__(self):
        self.fixation_detector = FixationDetector()
        self.coordinate_mapper = PDFCoordinateMapper()

        # 1분간 데이터 저장용 (60초 * 30fps = 1800개)
        self.recent_matches = deque(maxlen=1800)
        self.recent_fixations = deque(maxlen=1800)
        self.recent_saccades = deque(maxlen=1800)

        # 현재 상태
        self.current_fixation_duration = 0.0
        self.last_saccade_distance = 0.0
        self.current_gazed_text = ""

        # 어려운 용어 목록
        self.difficult_terms = [
            '중도해지', '우대금리', '예금자보호', '만기자동연장', '복리', '단리',
            '세액공제', '원천징수', '과세표준', '소득공제', '비과세',
            '압류', '가압류', '질권설정', '양도담보'
        ]

    def process_gaze_point(self, x: float, y: float, current_page: int = 1,
                          timestamp: float = None) -> Optional[Dict]:
        """시선 포인트 처리 및 AI용 데이터 생성"""
        if timestamp is None:
            timestamp = time.time()

        # 1. 고정점 감지
        fixation = self.fixation_detector.add_gaze_point(x, y, timestamp)

        if fixation:
            self.recent_fixations.append(fixation)
            self.current_fixation_duration = fixation.duration

            # 텍스트 매핑
            text_match = self.coordinate_mapper.map_gaze_to_text(
                fixation.x, fixation.y, current_page, timestamp
            )

            if text_match:
                self.recent_matches.append(text_match)
                self.current_gazed_text = text_match.matched_text

        # 2. 사케이드 거리 업데이트
        recent_saccades = self.fixation_detector.saccades
        if recent_saccades:
            self.last_saccade_distance = recent_saccades[-1].distance
            self.recent_saccades.append(recent_saccades[-1])

        # 3. AI용 데이터 생성
        return self.generate_ai_data(timestamp)

    def generate_ai_data(self, timestamp: float) -> Dict[str, Any]:
        """AI 전송용 데이터 생성"""
        # 1분간 메트릭스 계산
        metrics_1min = self._calculate_1min_metrics(timestamp)

        return {
            "timestamp": timestamp,
            "gaze_features": {
                "current_fixation_duration": self.current_fixation_duration,
                "last_saccade_distance": self.last_saccade_distance,
                "gazed_text": self.current_gazed_text
            },
            "behavioral_metrics_window_1min": metrics_1min
        }

    def _calculate_1min_metrics(self, current_time: float) -> Dict[str, float]:
        """최근 1분간 누적 지표 계산"""
        cutoff_time = current_time - 60.0  # 1분 전

        # 1분 내 데이터 필터링
        recent_fixations_1min = [f for f in self.recent_fixations
                                if f.end_time >= cutoff_time]
        recent_matches_1min = [m for m in self.recent_matches
                              if m.timestamp >= cutoff_time]

        if not recent_matches_1min:
            return {
                "wpm": 0.0,
                "regression_count": 0,
                "avg_fixation_duration": 0.0,
                "special_term_fixation_time": 0.0
            }

        # WPM 계산
        unique_texts = set(m.matched_text for m in recent_matches_1min)
        word_count = sum(len(text.split()) for text in unique_texts)
        wpm = word_count  # 이미 1분간 데이터이므로 * 60 불필요

        # 재읽기 횟수 (같은 텍스트를 여러 번 본 경우)
        text_counts = {}
        for match in recent_matches_1min:
            text = match.matched_text
            text_counts[text] = text_counts.get(text, 0) + 1

        regression_count = sum(count - 1 for count in text_counts.values() if count > 1)

        # 평균 고정 시간
        if recent_fixations_1min:
            avg_fixation_duration = np.mean([f.duration for f in recent_fixations_1min])
        else:
            avg_fixation_duration = 0.0

        # 특수 용어 총 응시 시간
        special_term_time = 0.0
        for match in recent_matches_1min:
            if any(term in match.matched_text for term in self.difficult_terms):
                # 해당 텍스트에 대한 고정점 찾기
                matching_fixations = [f for f in recent_fixations_1min
                                    if abs(f.x - match.gaze_x) < 50 and
                                       abs(f.y - match.gaze_y) < 50 and
                                       abs(f.start_time - match.timestamp) < 1.0]
                special_term_time += sum(f.duration for f in matching_fixations)

        return {
            "wpm": round(wpm, 1),
            "regression_count": regression_count,
            "avg_fixation_duration": round(avg_fixation_duration, 3),
            "special_term_fixation_time": round(special_term_time, 1)
        }

    def clear_history(self):
        """모든 히스토리 초기화"""
        self.recent_matches.clear()
        self.recent_fixations.clear()
        self.recent_saccades.clear()
        self.fixation_detector.clear_history()

        self.current_fixation_duration = 0.0
        self.last_saccade_distance = 0.0
        self.current_gazed_text = ""