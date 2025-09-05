import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from collections import deque, defaultdict
import time
import os
from comprehension_analyzer import ComprehensionAnalyzer, RealTimeComprehensionMonitor
from text_gaze_analyzer import TextGazeAnalyzer

class ComprehensionTestSystem:
    def __init__(self):
        self.analyzer = TextGazeAnalyzer()
        self.comprehension = ComprehensionAnalyzer()
        self.monitor = RealTimeComprehensionMonitor()
        
        # 시선 추적 설정
        self.h_scale = 200
        self.v_scale = 120
        self.offset_x = 0
        self.offset_y = 0
        self.gaze_history = deque(maxlen=5)
        
        # 이해도 측정 데이터
        self.current_word = None
        self.word_start_time = None
        self.word_fixations = defaultdict(list)
        self.regression_count = 0
        self.total_words_read = []
        
    def create_test_text_image(self):
        """테스트용 한글 텍스트 이미지"""
        width, height = 1400, 900
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font_paths = [
                "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                "/Library/Fonts/Arial Unicode.ttf",
            ]
            
            font_title = None
            font_body = None
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font_title = ImageFont.truetype(font_path, 32, index=0)
                        font_body = ImageFont.truetype(font_path, 24, index=0)
                        break
                    except:
                        continue
            
            if not font_title:
                font_title = ImageFont.load_default()
                font_body = ImageFont.load_default()
                
        except:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
        
        # 제목
        draw.text((50, 30), "📖 문맥 이해도 측정 테스트", font=font_title, fill='black')
        
        # 본문 (각 줄을 단어별로 분리 가능하게)
        text_lines = [
            "",
            "InnoDB 버퍼 풀은 데이터베이스 성능의 핵심입니다.",
            "LRU 알고리즘을 사용하여 자주 사용되는 페이지를 메모리에 유지합니다.",
            "",
            "버퍼 풀의 크기는 시스템 메모리의 70-80%로 설정하는 것이 일반적입니다.",
            "너무 작으면 디스크 I/O가 증가하고, 너무 크면 시스템이 불안정해집니다.",
            "",
            "어댑티브 해시 인덱스는 자주 접근하는 데이터에 대한 해시 테이블입니다.",
            "B-Tree 인덱스 탐색을 건너뛰고 직접 데이터에 접근할 수 있습니다.",
            "",
            "MRU는 Most Recently Used의 약자로 가장 최근 사용된 페이지입니다.",
            "LRU는 Least Recently Used의 약자로 가장 오래 사용되지 않은 페이지입니다."
        ]
        
        # 텍스트 그리기 및 위치 저장
        y_offset = 100
        line_height = 40
        self.text_regions = []  # 각 단어의 위치 저장
        
        for line in text_lines:
            if line:
                words = line.split()
                x_offset = 50
                for word in words:
                    # 단어 크기 계산 (textbbox 대신 간단한 추정)
                    word_width = len(word) * 15  # 한 글자당 약 15픽셀
                    word_height = 30  # 폰트 높이
                    
                    draw.text((x_offset, y_offset), word, font=font_body, fill='black')
                    
                    # 단어 영역 저장 (x, y, width, height)
                    self.text_regions.append({
                        'word': word,
                        'bbox': (x_offset, y_offset, word_width, word_height)
                    })
                    
                    # 디버깅용 - 단어 영역 표시 (활성화)
                    draw.rectangle([x_offset, y_offset, x_offset + word_width, y_offset + word_height], 
                                   outline='lightgray', width=1)
                    
                    x_offset += word_width + 15  # 다음 단어 위치
            
            y_offset += line_height
        
        return np.array(img)
    
    def get_word_at_gaze(self, gaze_x, gaze_y):
        """시선 위치의 단어 찾기"""
        for region in self.text_regions:
            x, y, w, h = region['bbox']
            # 영역 내에 있는지 확인 (여유 공간 추가)
            if (x - 5) <= gaze_x <= (x + w + 5) and (y - 5) <= gaze_y <= (y + h + 5):
                return region['word']
        return None
    
    def smooth_gaze(self, x, y):
        """시선 스무딩"""
        self.gaze_history.append((x, y))
        if len(self.gaze_history) < 2:
            return x, y
        
        weights = [0.1, 0.2, 0.3, 0.3, 0.1][-len(self.gaze_history):]
        total_weight = sum(weights)
        
        smoothed_x = sum(p[0] * w for p, w in zip(self.gaze_history, weights)) / total_weight
        smoothed_y = sum(p[1] * w for p, w in zip(self.gaze_history, weights)) / total_weight
        
        return int(smoothed_x), int(smoothed_y)
    
    def calculate_gaze(self, landmarks, frame_shape):
        """시선 위치 계산"""
        left_eye_center = self.analyzer.gaze_tracker.get_eye_center(
            landmarks, self.analyzer.gaze_tracker.LEFT_EYE_INDICES, frame_shape)
        right_eye_center = self.analyzer.gaze_tracker.get_eye_center(
            landmarks, self.analyzer.gaze_tracker.RIGHT_EYE_INDICES, frame_shape)
        
        left_iris = self.analyzer.gaze_tracker.get_iris_position(
            landmarks, self.analyzer.gaze_tracker.LEFT_IRIS_INDICES, frame_shape)
        right_iris = self.analyzer.gaze_tracker.get_iris_position(
            landmarks, self.analyzer.gaze_tracker.RIGHT_IRIS_INDICES, frame_shape)
        
        left_gaze_vector = left_iris - left_eye_center
        right_gaze_vector = right_iris - right_eye_center
        avg_gaze_vector = (left_gaze_vector + right_gaze_vector) / 2
        
        face_center_x = landmarks.landmark[9].x * frame_shape[1]
        face_center_y = landmarks.landmark[9].y * frame_shape[0]
        
        eye_distance = np.linalg.norm(left_eye_center - right_eye_center)
        scale_factor = 150 / max(eye_distance, 50)
        
        gaze_x = face_center_x - avg_gaze_vector[0] * self.h_scale * scale_factor + self.offset_x
        gaze_y = face_center_y + avg_gaze_vector[1] * self.v_scale * scale_factor + self.offset_y
        
        gaze_x, gaze_y = self.smooth_gaze(gaze_x, gaze_y)
        
        gaze_x = np.clip(gaze_x, 0, frame_shape[1] - 1)
        gaze_y = np.clip(gaze_y, 0, frame_shape[0] - 1)
        
        return int(gaze_x), int(gaze_y)
    
    def run(self):
        text_image = self.create_test_text_image()
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        cv2.namedWindow('Camera', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Reading Test', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Comprehension Dashboard', cv2.WINDOW_NORMAL)
        
        print("=" * 60)
        print("문맥 이해도 측정 시스템")
        print("=" * 60)
        print("텍스트를 읽으면서 이해도를 실시간으로 측정합니다")
        print("Q - 종료 | R - 리셋 | S - 리포트 저장")
        print("=" * 60)
        
        gaze_trail = deque(maxlen=30)
        heatmap = np.zeros(text_image.shape[:2], dtype=np.float32)
        session_start = time.time()
        last_word = None
        last_word_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            current_time = time.time()
            
            landmarks = self.analyzer.gaze_tracker.detect_eyes(frame)
            
            display_image = text_image.copy()
            
            if landmarks:
                gaze_x, gaze_y = self.calculate_gaze(landmarks, text_image.shape)
                
                # 시선이 보고 있는 단어 찾기
                current_word = self.get_word_at_gaze(gaze_x, gaze_y)
                
                if current_word:
                    # 단어 응시 시간 측정
                    if current_word != last_word:
                        if last_word:
                            fixation_time = (current_time - last_word_time) * 1000
                            self.word_fixations[last_word].append(fixation_time)
                            
                            # 이해도 분석
                            difficulty = self.comprehension.analyze_fixation_pattern(
                                last_word, fixation_time, (gaze_x, gaze_y)
                            )
                            
                            # 회귀 검사
                            if last_word in self.total_words_read:
                                self.regression_count += 1
                        
                        self.total_words_read.append(current_word)
                        last_word = current_word
                        last_word_time = current_time
                        
                        # 디버깅: 단어 감지 로그
                        print(f"Looking at: {current_word}")
                    
                    # 현재 보고 있는 단어 하이라이트
                    for region in self.text_regions:
                        if region['word'] == current_word:
                            x, y, w, h = region['bbox']
                            cv2.rectangle(display_image, (x, y), (x+w, y+h), 
                                        (0, 255, 255), 3)  # 노란색으로 강조
                
                # 시선 궤적
                gaze_trail.append((gaze_x, gaze_y))
                cv2.circle(heatmap, (gaze_x, gaze_y), 20, 1.0, -1)
                
                for i in range(1, len(gaze_trail)):
                    alpha = i / len(gaze_trail)
                    cv2.line(display_image, gaze_trail[i-1], gaze_trail[i],
                            (0, int(255 * alpha), 0), max(1, int(3 * alpha)))
                
                # 시선 포인터
                cv2.circle(display_image, (gaze_x, gaze_y), 15, (0, 255, 0), -1)
                cv2.circle(display_image, (gaze_x, gaze_y), 20, (0, 255, 0), 2)
            
            # 대시보드 생성
            dashboard = self.create_dashboard()
            
            # 실시간 피드백
            feedback = self.monitor.get_realtime_feedback()
            cv2.putText(display_image, feedback['message'], (50, display_image.shape[0] - 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, feedback['color'], 2)
            
            cv2.imshow('Camera', frame)
            cv2.imshow('Reading Test', display_image)
            cv2.imshow('Comprehension Dashboard', dashboard)
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('r'):
                self.word_fixations.clear()
                self.total_words_read.clear()
                self.regression_count = 0
                gaze_trail.clear()
                heatmap = np.zeros(text_image.shape[:2], dtype=np.float32)
                print("Reset!")
            elif key == ord('s'):
                self.save_report()
                print("Report saved!")
            elif key == ord('w'):
                self.offset_y -= 20
            elif key == ord('s'):
                self.offset_y += 20
            elif key == ord('a'):
                self.offset_x -= 20
            elif key == ord('d'):
                self.offset_x += 20
        
        # 최종 리포트
        self.generate_final_report()
        
        cap.release()
        cv2.destroyAllWindows()
    
    def create_dashboard(self):
        """실시간 대시보드"""
        dashboard = np.zeros((400, 600, 3), dtype=np.uint8)
        dashboard.fill(30)
        
        # 제목
        cv2.putText(dashboard, "COMPREHENSION METRICS", (150, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        y_offset = 80
        
        # 읽은 단어 수
        words_read = len(set(self.total_words_read))
        cv2.putText(dashboard, f"Words Read: {words_read}", (30, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        y_offset += 30
        
        # 회귀 횟수
        cv2.putText(dashboard, f"Regressions: {self.regression_count}", (30, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        y_offset += 30
        
        # 어려운 단어 (응시 시간 긴 순서)
        difficult_words = []
        for word, times in self.word_fixations.items():
            if times:
                avg_time = np.mean(times)
                if avg_time > 500:  # 500ms 이상
                    difficult_words.append((word, avg_time))
        
        difficult_words.sort(key=lambda x: x[1], reverse=True)
        
        cv2.putText(dashboard, "Difficult Words:", (30, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 100, 100), 1)
        y_offset += 25
        
        for word, avg_time in difficult_words[:5]:
            cv2.putText(dashboard, f"  {word}: {avg_time:.0f}ms", (30, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_offset += 20
        
        # 이해도 점수 계산
        if self.word_fixations:
            all_times = []
            for times in self.word_fixations.values():
                all_times.extend(times)
            
            if all_times:
                avg_fixation = np.mean(all_times)
                comprehension_score = max(0, min(100, 100 - (avg_fixation - 200) / 10))
                
                # 점수 표시
                y_offset += 20
                cv2.putText(dashboard, f"Comprehension Score: {comprehension_score:.1f}%",
                           (30, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # 막대 그래프
                bar_width = int(comprehension_score * 5)
                bar_color = (0, 255, 0) if comprehension_score > 70 else \
                           (255, 255, 0) if comprehension_score > 40 else (255, 0, 0)
                cv2.rectangle(dashboard, (30, y_offset + 10), 
                             (30 + bar_width, y_offset + 30), bar_color, -1)
        
        return dashboard
    
    def save_report(self):
        """리포트 저장"""
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'words_read': len(set(self.total_words_read)),
            'total_words': len(self.total_words_read),
            'regression_count': self.regression_count,
            'word_fixations': dict(self.word_fixations),
            'difficult_words': []
        }
        
        for word, times in self.word_fixations.items():
            if times and np.mean(times) > 500:
                report['difficult_words'].append({
                    'word': word,
                    'avg_time': np.mean(times),
                    'count': len(times)
                })
        
        # JSON으로 저장
        import json
        with open('comprehension_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    
    def generate_final_report(self):
        """최종 이해도 리포트"""
        print("\n" + "=" * 60)
        print("최종 이해도 분석 리포트")
        print("=" * 60)
        
        if self.word_fixations:
            # 전체 통계
            all_times = []
            for times in self.word_fixations.values():
                all_times.extend(times)
            
            if all_times:
                print(f"평균 응시 시간: {np.mean(all_times):.0f}ms")
                print(f"회귀 횟수: {self.regression_count}")
                print(f"읽은 고유 단어 수: {len(set(self.total_words_read))}")
                
                # 이해도 판정
                avg_time = np.mean(all_times)
                if avg_time < 300:
                    print("이해도: 높음 ✅")
                elif avg_time < 600:
                    print("이해도: 보통 ⚠️")
                else:
                    print("이해도: 낮음 ❌")
                
                # 어려운 단어 리스트
                print("\n어려웠던 단어들:")
                difficult = []
                for word, times in self.word_fixations.items():
                    if times and np.mean(times) > 500:
                        difficult.append((word, np.mean(times)))
                
                difficult.sort(key=lambda x: x[1], reverse=True)
                for word, avg_time in difficult[:5]:
                    print(f"  - {word}: {avg_time:.0f}ms")
        
        print("=" * 60)

if __name__ == "__main__":
    system = ComprehensionTestSystem()
    system.run()