import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from text_gaze_analyzer import TextGazeAnalyzer

class AdjustableGazeTracker:
    def __init__(self):
        self.analyzer = TextGazeAnalyzer()
        self.h_scale = 150  # 수평 스케일
        self.v_scale = 80   # 수직 스케일
        self.smoothing = 0.3  # 스무딩 팩터
        self.last_gaze = None
        
    def create_sample_text_image(self):
        width, height = 1280, 720
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        try:
            font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
            font_medium = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except:
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        draw.text((100, 50), "Adjustable Gaze Tracking Test", font=font_large, fill='black')
        
        sample_text = [
            "Use keyboard to adjust sensitivity:",
            "",
            "W/S - Increase/Decrease vertical scale",
            "A/D - Increase/Decrease horizontal scale", 
            "R - Reset to default values",
            "F - Toggle smoothing filter",
            "",
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning enables computers to learn.",
            "Eye tracking technology has many applications."
        ]
        
        y_offset = 150
        for line in sample_text:
            draw.text((100, y_offset), line, font=font_medium, fill='black')
            y_offset += 45
        
        return np.array(img)
    
    def apply_smoothing(self, current_gaze):
        if self.last_gaze is None:
            self.last_gaze = current_gaze
            return current_gaze
        
        smoothed = (
            self.last_gaze[0] * (1 - self.smoothing) + current_gaze[0] * self.smoothing,
            self.last_gaze[1] * (1 - self.smoothing) + current_gaze[1] * self.smoothing
        )
        self.last_gaze = smoothed
        return smoothed
    
    def run(self):
        text_image = self.create_sample_text_image()
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Text Display', cv2.WINDOW_NORMAL)
        
        print("=" * 60)
        print("ADJUSTABLE GAZE TRACKER")
        print("=" * 60)
        print("Controls:")
        print("W/S - Adjust vertical sensitivity")
        print("A/D - Adjust horizontal sensitivity")
        print("R - Reset to default")
        print("F - Toggle smoothing")
        print("Q - Quit")
        print("=" * 60)
        
        use_smoothing = True
        gaze_trail = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            
            # 커스텀 스케일 값으로 시선 계산
            landmarks = self.analyzer.gaze_tracker.detect_eyes(frame)
            
            display_image = text_image.copy()
            
            if landmarks:
                # 수동으로 시선 방향 계산 (조정 가능한 스케일 사용)
                left_eye_center = self.analyzer.gaze_tracker.get_eye_center(
                    landmarks, self.analyzer.gaze_tracker.LEFT_EYE_INDICES, frame.shape)
                right_eye_center = self.analyzer.gaze_tracker.get_eye_center(
                    landmarks, self.analyzer.gaze_tracker.RIGHT_EYE_INDICES, frame.shape)
                
                left_iris = self.analyzer.gaze_tracker.get_iris_position(
                    landmarks, self.analyzer.gaze_tracker.LEFT_IRIS_INDICES, frame.shape)
                right_iris = self.analyzer.gaze_tracker.get_iris_position(
                    landmarks, self.analyzer.gaze_tracker.RIGHT_IRIS_INDICES, frame.shape)
                
                left_gaze_vector = left_iris - left_eye_center
                right_gaze_vector = right_iris - right_eye_center
                avg_gaze_vector = (left_gaze_vector + right_gaze_vector) / 2
                
                # 조정 가능한 스케일 적용
                nose_tip = landmarks.landmark[1]
                nose_x = nose_tip.x * frame.shape[1]
                nose_y = nose_tip.y * frame.shape[0]
                
                gaze_x = nose_x + avg_gaze_vector[0] * self.h_scale
                gaze_y = nose_y + avg_gaze_vector[1] * self.v_scale
                
                gaze_x = np.clip(gaze_x, 0, frame.shape[1])
                gaze_y = np.clip(gaze_y, 0, frame.shape[0])
                
                current_gaze = (gaze_x, gaze_y)
                
                # 스무딩 적용
                if use_smoothing:
                    current_gaze = self.apply_smoothing(current_gaze)
                
                # 시선 궤적 저장
                gaze_trail.append((int(current_gaze[0]), int(current_gaze[1])))
                if len(gaze_trail) > 50:
                    gaze_trail.pop(0)
                
                # 시선 궤적 그리기
                for i in range(1, len(gaze_trail)):
                    alpha = i / len(gaze_trail)
                    cv2.line(display_image, gaze_trail[i-1], gaze_trail[i], 
                            (0, int(255 * alpha), 0), max(1, int(3 * alpha)))
                
                # 현재 시선 포인트
                cv2.circle(display_image, (int(current_gaze[0]), int(current_gaze[1])), 
                          15, (0, 255, 0), -1)
                cv2.circle(display_image, (int(current_gaze[0]), int(current_gaze[1])), 
                          20, (0, 255, 0), 2)
                
                # 카메라 프레임에도 표시
                cv2.circle(frame, (int(left_iris[0]), int(left_iris[1])), 5, (255, 0, 0), -1)
                cv2.circle(frame, (int(right_iris[0]), int(right_iris[1])), 5, (255, 0, 0), -1)
            
            # 현재 설정 표시
            settings_text = [
                f"H-Scale: {self.h_scale}",
                f"V-Scale: {self.v_scale}",
                f"Smoothing: {'ON' if use_smoothing else 'OFF'} ({self.smoothing:.2f})"
            ]
            
            y_pos = 30
            for text in settings_text:
                cv2.putText(frame, text, (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                y_pos += 30
            
            cv2.imshow('Camera Feed', frame)
            cv2.imshow('Text Display', display_image)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('w'):  # 수직 증가
                self.v_scale += 10
                print(f"Vertical scale: {self.v_scale}")
            elif key == ord('s'):  # 수직 감소
                self.v_scale = max(10, self.v_scale - 10)
                print(f"Vertical scale: {self.v_scale}")
            elif key == ord('d'):  # 수평 증가
                self.h_scale += 10
                print(f"Horizontal scale: {self.h_scale}")
            elif key == ord('a'):  # 수평 감소
                self.h_scale = max(10, self.h_scale - 10)
                print(f"Horizontal scale: {self.h_scale}")
            elif key == ord('r'):  # 리셋
                self.h_scale = 150
                self.v_scale = 80
                print("Reset to default values")
            elif key == ord('f'):  # 스무딩 토글
                use_smoothing = not use_smoothing
                print(f"Smoothing: {'ON' if use_smoothing else 'OFF'}")
            elif key == ord('1'):  # 스무딩 강도 감소
                self.smoothing = max(0.1, self.smoothing - 0.1)
                print(f"Smoothing factor: {self.smoothing:.2f}")
            elif key == ord('2'):  # 스무딩 강도 증가
                self.smoothing = min(0.9, self.smoothing + 0.1)
                print(f"Smoothing factor: {self.smoothing:.2f}")
        
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n" + "=" * 60)
        print("Final Settings:")
        print(f"Horizontal Scale: {self.h_scale}")
        print(f"Vertical Scale: {self.v_scale}")
        print(f"Smoothing: {self.smoothing}")
        print("=" * 60)

if __name__ == "__main__":
    tracker = AdjustableGazeTracker()
    tracker.run()