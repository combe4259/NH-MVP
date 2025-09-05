import cv2
import numpy as np
from collections import deque
from dataclasses import dataclass
from typing import List, Dict, Optional
import time
import json

from gaze_tracker import EyeGazeTracker, GazeData
from text_detector import TextDetector, TextRegion

@dataclass
class ReadingMetrics:
    total_fixations: int
    avg_fixation_duration: float
    words_read: List[str]
    reading_speed_wpm: float
    regression_count: int
    reading_pattern: str  # 'linear', 'scanning', 'focused'

class TextGazeAnalyzer:
    def __init__(self, buffer_size=30):
        self.gaze_tracker = EyeGazeTracker()
        self.text_detector = TextDetector()
        
        self.gaze_buffer = deque(maxlen=buffer_size)
        self.fixation_buffer = []
        self.current_fixation = None
        
        self.reading_history = []
        self.word_sequence = []
        self.regression_count = 0
        
        self.FIXATION_THRESHOLD = 50  # pixels
        self.FIXATION_MIN_DURATION = 0.1  # seconds
        
    def detect_fixation(self, gaze_data: GazeData) -> bool:
        if not self.gaze_buffer:
            self.gaze_buffer.append(gaze_data)
            return False
        
        recent_points = list(self.gaze_buffer)[-5:]
        if len(recent_points) < 3:
            self.gaze_buffer.append(gaze_data)
            return False
        
        xs = [p.x for p in recent_points]
        ys = [p.y for p in recent_points]
        
        std_x = np.std(xs)
        std_y = np.std(ys)
        
        if std_x < self.FIXATION_THRESHOLD and std_y < self.FIXATION_THRESHOLD:
            if self.current_fixation is None:
                self.current_fixation = {
                    'start_time': gaze_data.timestamp,
                    'x': np.mean(xs),
                    'y': np.mean(ys),
                    'points': recent_points
                }
            else:
                self.current_fixation['points'].extend(recent_points)
                self.current_fixation['x'] = np.mean([p.x for p in self.current_fixation['points']])
                self.current_fixation['y'] = np.mean([p.y for p in self.current_fixation['points']])
            
            self.gaze_buffer.append(gaze_data)
            return True
        else:
            if self.current_fixation:
                duration = gaze_data.timestamp - self.current_fixation['start_time']
                if duration >= self.FIXATION_MIN_DURATION:
                    self.fixation_buffer.append(self.current_fixation)
                self.current_fixation = None
            
            self.gaze_buffer.append(gaze_data)
            return False
    
    def analyze_reading_pattern(self, fixations: List[Dict]) -> str:
        if len(fixations) < 3:
            return "scanning"
        
        x_positions = [f['x'] for f in fixations]
        y_positions = [f['y'] for f in fixations]
        
        x_variance = np.var(x_positions)
        y_variance = np.var(y_positions)
        
        horizontal_movement = sum(abs(x_positions[i] - x_positions[i-1]) 
                                for i in range(1, len(x_positions)))
        vertical_movement = sum(abs(y_positions[i] - y_positions[i-1]) 
                              for i in range(1, len(y_positions)))
        
        if horizontal_movement > vertical_movement * 2:
            return "linear"
        elif x_variance < 1000 and y_variance < 1000:
            return "focused"
        else:
            return "scanning"
    
    def track_word_sequence(self, current_region: Optional[TextRegion]):
        if current_region and current_region.text:
            if self.word_sequence and self.word_sequence[-1] != current_region.text:
                last_word_idx = self.word_sequence[-1] if self.word_sequence else -1
                
                if current_region.word_id < last_word_idx:
                    self.regression_count += 1
                
                self.word_sequence.append(current_region.text)
                self.reading_history.append({
                    'word': current_region.text,
                    'timestamp': time.time(),
                    'confidence': current_region.confidence
                })
    
    def calculate_reading_metrics(self) -> ReadingMetrics:
        if not self.fixation_buffer:
            return ReadingMetrics(
                total_fixations=0,
                avg_fixation_duration=0,
                words_read=[],
                reading_speed_wpm=0,
                regression_count=0,
                reading_pattern="none"
            )
        
        total_fixations = len(self.fixation_buffer)
        
        durations = []
        for i, fix in enumerate(self.fixation_buffer):
            if i < len(self.fixation_buffer) - 1:
                duration = self.fixation_buffer[i+1]['start_time'] - fix['start_time']
                durations.append(duration)
        
        avg_duration = np.mean(durations) if durations else 0
        
        unique_words = list(set(self.word_sequence))
        
        if self.reading_history and len(self.reading_history) > 1:
            time_span = (self.reading_history[-1]['timestamp'] - 
                        self.reading_history[0]['timestamp'])
            if time_span > 0:
                words_per_minute = (len(unique_words) / time_span) * 60
            else:
                words_per_minute = 0
        else:
            words_per_minute = 0
        
        pattern = self.analyze_reading_pattern(self.fixation_buffer[-10:])
        
        return ReadingMetrics(
            total_fixations=total_fixations,
            avg_fixation_duration=avg_duration,
            words_read=unique_words,
            reading_speed_wpm=words_per_minute,
            regression_count=self.regression_count,
            reading_pattern=pattern
        )
    
    def save_session_data(self, filename="reading_session.json"):
        session_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'reading_history': self.reading_history,
            'metrics': {
                'total_words': len(self.word_sequence),
                'unique_words': len(set(self.word_sequence)),
                'regression_count': self.regression_count,
                'fixation_count': len(self.fixation_buffer)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
    
    def create_reading_heatmap(self, frame_shape):
        heatmap = np.zeros(frame_shape[:2], dtype=np.float32)
        
        for fixation in self.fixation_buffer:
            x, y = int(fixation['x']), int(fixation['y'])
            if 0 <= x < frame_shape[1] and 0 <= y < frame_shape[0]:
                cv2.circle(heatmap, (x, y), 40, 1.0, -1)
        
        heatmap = cv2.GaussianBlur(heatmap, (61, 61), 0)
        
        heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8) if heatmap.max() > 0 else heatmap.astype(np.uint8)
        
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_HOT)
        
        return heatmap_colored