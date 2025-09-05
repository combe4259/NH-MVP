import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import time
from collections import defaultdict

@dataclass
class ComprehensionMetrics:
    difficulty_score: float  # 0-1, 높을수록 어려움
    understanding_level: str  # 'high', 'medium', 'low'
    problem_areas: List[str]  # 이해 어려운 부분들
    reading_efficiency: float  # WPM adjusted for comprehension
    cognitive_load: float  # 인지 부하 수준

class ComprehensionAnalyzer:
    def __init__(self):
        self.word_fixations = defaultdict(list)  # 단어별 응시 시간
        self.sentence_metrics = defaultdict(dict)  # 문장별 메트릭
        self.regression_map = []  # 회귀 패턴
        self.reading_speed_variations = []
        
        # 임계값 설정
        self.DIFFICULT_FIXATION_THRESHOLD = 500  # ms
        self.EASY_FIXATION_THRESHOLD = 200  # ms
        self.REGRESSION_THRESHOLD = 3  # 회귀 횟수
        
    def analyze_fixation_pattern(self, word: str, fixation_duration: float, 
                                position: Tuple[int, int]):
        """단어별 응시 패턴 분석"""
        self.word_fixations[word].append({
            'duration': fixation_duration,
            'position': position,
            'timestamp': time.time()
        })
        
        # 난이도 계산
        avg_duration = np.mean([f['duration'] for f in self.word_fixations[word]])
        
        if avg_duration > self.DIFFICULT_FIXATION_THRESHOLD:
            return 'difficult'
        elif avg_duration < self.EASY_FIXATION_THRESHOLD:
            return 'easy'
        else:
            return 'moderate'
    
    def detect_comprehension_issues(self, sentence: str, metrics: Dict) -> Dict:
        """문장 단위 이해도 문제 감지"""
        issues = {
            'has_difficulty': False,
            'difficulty_type': [],
            'suggestions': []
        }
        
        # 1. 긴 응시 시간 체크
        if metrics.get('avg_fixation', 0) > self.DIFFICULT_FIXATION_THRESHOLD:
            issues['has_difficulty'] = True
            issues['difficulty_type'].append('complex_content')
            issues['suggestions'].append('이 부분은 천천히 다시 읽어보세요')
        
        # 2. 높은 회귀율 체크
        if metrics.get('regression_count', 0) > self.REGRESSION_THRESHOLD:
            issues['has_difficulty'] = True
            issues['difficulty_type'].append('confusion')
            issues['suggestions'].append('앞 문장과의 연관성을 확인하세요')
        
        # 3. 불규칙한 읽기 속도
        if metrics.get('speed_variance', 0) > 0.5:
            issues['has_difficulty'] = True
            issues['difficulty_type'].append('inconsistent_reading')
            issues['suggestions'].append('일정한 속도로 읽기를 시도하세요')
        
        return issues
    
    def calculate_cognitive_load(self, fixations: List, regressions: int, 
                                reading_speed: float) -> float:
        """인지 부하 계산 (0-1)"""
        # 응시 시간 변동성
        if len(fixations) > 1:
            fixation_variance = np.std([f['duration'] for f in fixations]) / 1000
        else:
            fixation_variance = 0
        
        # 회귀 빈도
        regression_factor = min(regressions / 10, 1.0)
        
        # 읽기 속도 (너무 빠르거나 느리면 부하 증가)
        optimal_wpm = 250
        speed_factor = abs(reading_speed - optimal_wpm) / optimal_wpm
        
        # 종합 인지 부하
        cognitive_load = (fixation_variance * 0.4 + 
                         regression_factor * 0.4 + 
                         speed_factor * 0.2)
        
        return min(cognitive_load, 1.0)
    
    def generate_comprehension_report(self, reading_session_data: Dict) -> ComprehensionMetrics:
        """종합 이해도 리포트 생성"""
        
        # 전체 난이도 점수 계산
        all_fixations = []
        for word_data in self.word_fixations.values():
            all_fixations.extend([f['duration'] for f in word_data])
        
        if all_fixations:
            avg_fixation = np.mean(all_fixations)
            difficulty_score = min(avg_fixation / 1000, 1.0)  # 정규화
        else:
            difficulty_score = 0.5
        
        # 이해도 수준 판정
        if difficulty_score < 0.3:
            understanding_level = 'high'
        elif difficulty_score < 0.6:
            understanding_level = 'medium'
        else:
            understanding_level = 'low'
        
        # 문제 영역 식별
        problem_areas = []
        for word, fixations in self.word_fixations.items():
            avg_duration = np.mean([f['duration'] for f in fixations])
            if avg_duration > self.DIFFICULT_FIXATION_THRESHOLD:
                problem_areas.append(word)
        
        # 읽기 효율성 (이해도 조정된 WPM)
        base_wpm = reading_session_data.get('wpm', 200)
        efficiency = base_wpm * (1 - difficulty_score * 0.5)
        
        # 인지 부하
        cognitive_load = self.calculate_cognitive_load(
            all_fixations,
            len(self.regression_map),
            base_wpm
        )
        
        return ComprehensionMetrics(
            difficulty_score=difficulty_score,
            understanding_level=understanding_level,
            problem_areas=problem_areas[:5],  # 상위 5개만
            reading_efficiency=efficiency,
            cognitive_load=cognitive_load
        )
    
    def suggest_improvements(self, metrics: ComprehensionMetrics) -> List[str]:
        """개선 제안 생성"""
        suggestions = []
        
        if metrics.difficulty_score > 0.6:
            suggestions.append("📚 이 텍스트는 난이도가 높습니다. 핵심 용어를 먼저 이해하세요.")
        
        if metrics.cognitive_load > 0.7:
            suggestions.append("🧠 인지 부하가 높습니다. 잠시 휴식 후 다시 읽어보세요.")
        
        if len(metrics.problem_areas) > 0:
            suggestions.append(f"⚠️ 어려운 부분: {', '.join(metrics.problem_areas[:3])}")
        
        if metrics.reading_efficiency < 150:
            suggestions.append("🐌 읽기 속도가 느립니다. 단락별로 요약하며 읽어보세요.")
        
        return suggestions

# 실시간 이해도 모니터링
class RealTimeComprehensionMonitor:
    def __init__(self):
        self.analyzer = ComprehensionAnalyzer()
        self.current_paragraph = ""
        self.paragraph_start_time = None
        
    def process_gaze_event(self, gaze_x: int, gaze_y: int, 
                          text_at_gaze: str, timestamp: float):
        """실시간 시선 이벤트 처리"""
        
        # 현재 보고 있는 텍스트가 있으면
        if text_at_gaze:
            # 응시 시간 계산
            if hasattr(self, 'last_word') and self.last_word == text_at_gaze:
                fixation_duration = (timestamp - self.last_timestamp) * 1000
                difficulty = self.analyzer.analyze_fixation_pattern(
                    text_at_gaze, fixation_duration, (gaze_x, gaze_y)
                )
                
                # 실시간 피드백
                if difficulty == 'difficult':
                    return f"⚠️ '{text_at_gaze}' - 이해가 어려우신가요?"
                
            self.last_word = text_at_gaze
            self.last_timestamp = timestamp
        
        return None
    
    def get_realtime_feedback(self) -> Dict:
        """실시간 피드백 생성"""
        recent_fixations = []
        for word_data in self.analyzer.word_fixations.values():
            if word_data:
                recent_fixations.extend(word_data[-5:])  # 최근 5개
        
        if recent_fixations:
            avg_recent = np.mean([f['duration'] for f in recent_fixations])
            
            if avg_recent > 600:
                return {
                    'status': 'struggling',
                    'message': '집중력이 떨어지고 있나요? 잠시 휴식을 취하세요.',
                    'color': (255, 100, 100)
                }
            elif avg_recent < 200:
                return {
                    'status': 'skimming',
                    'message': '너무 빨리 읽고 있습니다. 내용을 이해하며 읽으세요.',
                    'color': (255, 255, 100)
                }
            else:
                return {
                    'status': 'good',
                    'message': '좋은 속도로 읽고 있습니다!',
                    'color': (100, 255, 100)
                }
        
        return {
            'status': 'starting',
            'message': '읽기를 시작하세요...',
            'color': (200, 200, 200)
        }