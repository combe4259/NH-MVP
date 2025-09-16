import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import time

@dataclass
class FixationPoint:
    """시선 고정점 데이터"""
    x: float
    y: float
    start_time: float
    end_time: float
    duration: float
    confidence: float
    raw_points: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, timestamp)

@dataclass
class SaccadeMovement:
    """시선 이동(사케이드) 데이터"""
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    start_time: float
    end_time: float
    duration: float
    distance: float
    velocity: float

class FixationDetector:
    """시선 고정 및 이동 감지 클래스"""

    def __init__(self,
                 fixation_threshold=50,      # 픽셀 단위 거리 임계값
                 min_fixation_duration=100,  # 최소 고정 시간 (ms)
                 max_fixation_duration=2000, # 최대 고정 시간 (ms)
                 sampling_rate=30):          # Hz

        self.fixation_threshold = fixation_threshold
        self.min_fixation_duration = min_fixation_duration / 1000.0  # 초로 변환
        self.max_fixation_duration = max_fixation_duration / 1000.0
        self.sampling_rate = sampling_rate

        # 버퍼
        self.gaze_buffer: List[Tuple[float, float, float]] = []  # (x, y, timestamp)
        self.fixations: List[FixationPoint] = []
        self.saccades: List[SaccadeMovement] = []

        # 상태
        self.current_fixation_candidate: Optional[List[Tuple[float, float, float]]] = None
        self.last_fixation: Optional[FixationPoint] = None

    def add_gaze_point(self, x: float, y: float, timestamp: float = None) -> Optional[FixationPoint]:
        """새로운 시선 점을 추가하고 고정점 감지"""
        if timestamp is None:
            timestamp = time.time()

        self.gaze_buffer.append((x, y, timestamp))

        # 버퍼 크기 제한 (최근 5초간 데이터만 유지)
        cutoff_time = timestamp - 5.0
        self.gaze_buffer = [(gx, gy, gt) for gx, gy, gt in self.gaze_buffer if gt >= cutoff_time]

        return self._detect_fixation(x, y, timestamp)

    def _detect_fixation(self, current_x: float, current_y: float, timestamp: float) -> Optional[FixationPoint]:
        """I-DT (Dispersion-Threshold) 알고리즘을 사용한 고정점 감지"""

        if len(self.gaze_buffer) < 3:
            return None

        # 현재 고정 후보가 없으면 시작
        if self.current_fixation_candidate is None:
            self.current_fixation_candidate = [(current_x, current_y, timestamp)]
            return None

        # 현재 점을 후보에 추가
        self.current_fixation_candidate.append((current_x, current_y, timestamp))

        # 분산(dispersion) 계산
        dispersion = self._calculate_dispersion(self.current_fixation_candidate)

        # 분산이 임계값 이하면 고정점 후보 유지
        if dispersion <= self.fixation_threshold:
            # 최대 고정 시간을 초과하면 강제로 고정점 생성
            duration = timestamp - self.current_fixation_candidate[0][2]
            if duration >= self.max_fixation_duration:
                return self._finalize_fixation()
            return None
        else:
            # 분산이 임계값을 초과하면 이전 후보를 고정점으로 확정
            if len(self.current_fixation_candidate) > 1:
                prev_candidate = self.current_fixation_candidate[:-1]  # 마지막 점 제외
                duration = prev_candidate[-1][2] - prev_candidate[0][2]

                if duration >= self.min_fixation_duration:
                    fixation = self._create_fixation_from_candidate(prev_candidate)
                    self.current_fixation_candidate = [(current_x, current_y, timestamp)]
                    return fixation

            # 새로운 후보 시작
            self.current_fixation_candidate = [(current_x, current_y, timestamp)]
            return None

    def _calculate_dispersion(self, points: List[Tuple[float, float, float]]) -> float:
        """점들의 분산 계산 (최대-최소 거리)"""
        if len(points) < 2:
            return 0.0

        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]

        x_range = max(x_coords) - min(x_coords)
        y_range = max(y_coords) - min(y_coords)

        return max(x_range, y_range)

    def _create_fixation_from_candidate(self, candidate_points: List[Tuple[float, float, float]]) -> FixationPoint:
        """후보 점들로부터 고정점 생성"""
        x_coords = [p[0] for p in candidate_points]
        y_coords = [p[1] for p in candidate_points]

        # 중심점 계산
        centroid_x = np.mean(x_coords)
        centroid_y = np.mean(y_coords)

        # 시간 정보
        start_time = candidate_points[0][2]
        end_time = candidate_points[-1][2]
        duration = end_time - start_time

        # 신뢰도 계산 (분산이 작을수록, 지속 시간이 길수록 높음)
        dispersion = self._calculate_dispersion(candidate_points)
        duration_score = min(duration / self.min_fixation_duration, 2.0)  # 최대 2배
        dispersion_score = max(0, (self.fixation_threshold - dispersion) / self.fixation_threshold)
        confidence = min((duration_score * dispersion_score) / 2, 1.0)

        fixation = FixationPoint(
            x=centroid_x,
            y=centroid_y,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            confidence=confidence,
            raw_points=candidate_points.copy()
        )

        self.fixations.append(fixation)

        # 사케이드 계산 (이전 고정점이 있는 경우)
        if self.last_fixation is not None:
            self._create_saccade(self.last_fixation, fixation)

        self.last_fixation = fixation
        return fixation

    def _finalize_fixation(self) -> Optional[FixationPoint]:
        """현재 후보를 고정점으로 확정"""
        if self.current_fixation_candidate and len(self.current_fixation_candidate) >= 2:
            fixation = self._create_fixation_from_candidate(self.current_fixation_candidate)
            self.current_fixation_candidate = None
            return fixation
        return None

    def _create_saccade(self, prev_fixation: FixationPoint, current_fixation: FixationPoint):
        """두 고정점 사이의 사케이드 생성"""
        distance = np.sqrt((current_fixation.x - prev_fixation.x)**2 +
                          (current_fixation.y - prev_fixation.y)**2)

        duration = current_fixation.start_time - prev_fixation.end_time
        velocity = distance / max(duration, 0.001)  # 0으로 나누기 방지

        saccade = SaccadeMovement(
            start_x=prev_fixation.x,
            start_y=prev_fixation.y,
            end_x=current_fixation.x,
            end_y=current_fixation.y,
            start_time=prev_fixation.end_time,
            end_time=current_fixation.start_time,
            duration=duration,
            distance=distance,
            velocity=velocity
        )

        self.saccades.append(saccade)

    def get_recent_fixations(self, time_window: float = 10.0) -> List[FixationPoint]:
        """최근 시간 윈도우 내의 고정점들 반환"""
        current_time = time.time()
        cutoff_time = current_time - time_window

        return [f for f in self.fixations if f.end_time >= cutoff_time]

    def get_fixation_statistics(self, time_window: float = 30.0) -> dict:
        """고정점 통계 반환"""
        recent_fixations = self.get_recent_fixations(time_window)
        recent_saccades = [s for s in self.saccades
                          if s.end_time >= time.time() - time_window]

        if not recent_fixations:
            return {
                'fixation_count': 0,
                'avg_fixation_duration': 0,
                'total_fixation_time': 0,
                'saccade_count': 0,
                'avg_saccade_velocity': 0,
                'reading_efficiency': 0
            }

        # 고정점 통계
        durations = [f.duration for f in recent_fixations]
        avg_duration = np.mean(durations)
        total_fixation_time = sum(durations)

        # 사케이드 통계
        saccade_count = len(recent_saccades)
        avg_velocity = np.mean([s.velocity for s in recent_saccades]) if recent_saccades else 0

        # 읽기 효율성 (고정 시간 비율)
        reading_efficiency = total_fixation_time / time_window if time_window > 0 else 0

        return {
            'fixation_count': len(recent_fixations),
            'avg_fixation_duration': avg_duration,
            'total_fixation_time': total_fixation_time,
            'saccade_count': saccade_count,
            'avg_saccade_velocity': avg_velocity,
            'reading_efficiency': min(reading_efficiency, 1.0)
        }

    def clear_history(self):
        """모든 히스토리 초기화"""
        self.gaze_buffer.clear()
        self.fixations.clear()
        self.saccades.clear()
        self.current_fixation_candidate = None
        self.last_fixation = None