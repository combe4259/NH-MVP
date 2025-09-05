import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from collections import deque
from text_gaze_analyzer import TextGazeAnalyzer
import os

class KoreanTextGazeTracker:
    def __init__(self):
        self.analyzer = TextGazeAnalyzer()
        self.h_scale = 200
        self.v_scale = 120
        self.offset_x = 0
        self.offset_y = 0
        self.smoothing_factor = 0.4
        self.gaze_history = deque(maxlen=5)
        
    def create_korean_text_image(self):
        """한글 텍스트 이미지 생성"""
        width, height = 1400, 900
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # 한글 폰트 설정
        try:
            # macOS 한글 폰트 경로들
            font_paths = [
                "/System/Library/Fonts/AppleSDGothicNeo.ttc",
                "/System/Library/Fonts/Supplemental/AppleGothicRegular.ttf",
                "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Helvetica.ttc"  # 폴백
            ]
            
            font_title = None
            font_body = None
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        font_title = ImageFont.truetype(font_path, 28, index=0)
                        font_body = ImageFont.truetype(font_path, 20, index=0)
                        break
                    except:
                        continue
            
            if not font_title:
                font_title = ImageFont.load_default()
                font_body = ImageFont.load_default()
                print("Warning: Korean font not found, using default font")
                
        except Exception as e:
            print(f"Font error: {e}")
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
        
        # 제목
        draw.text((50, 30), "그림 4.13 버퍼 풀 관리를 위한 LRU 리스트 구조", 
                 font=font_title, fill='black')
        
        # 본문 텍스트
        text_content = [
            "",
            "LRU 리스트를 관리하는 목적은 디스크로부터 한 번 읽어온 페이지를 최대한 오랫동안 InnoDB 버퍼",
            "풀의 메모리에 유지해서 디스크 읽기를 최소화하는 것이다. InnoDB 스토리지 엔진에서 데이터를 찾",
            "는 과정은 대략 다음과 같다.",
            "",
            "1. 필요한 레코드가 저장된 데이터 페이지가 버퍼 풀에 있는지 검사",
            "   A. InnoDB 어댑티브 해시 인덱스를 이용해 페이지를 검색",
            "   B. 해당 테이블의 인덱스(B-Tree)를 이용해 버퍼 풀에서 페이지를 검색",
            "   C. 버퍼 풀에 이미 데이터 페이지가 있었다면 해당 페이지의 포인터를 MRU 방향으로 승급",
            "",
            "2. 디스크에서 필요한 데이터 페이지를 버퍼 풀에 적재하고, 적재된 페이지에 대한 포인터를 LRU 헤더 부분에 추가",
            "",
            "3. 버퍼 풀의 LRU 헤더 부분에 적재된 데이터 페이지가 실제로 읽히면 MRU 헤더 부분으로 이동(Read Ahead와 같",
            "   이 대량 읽기의 경우 디스크의 데이터 페이지가 버퍼 풀로 적재는 되지만 실제 쿼리에서 사용되지는 않을 수도 있으",
            "   며, 이런 경우에는 MRU로 이동되지 않음)",
            "",
            "4. 버퍼 풀에 상주하는 데이터 페이지는 사용자 쿼리가 얼마나 최근에 접근했었는지에 따라 나이(Age)가 부여되며, 버",
            "   퍼 풀에 상주하는 동안 쿼리에서 오랫동안 사용되지 않으면 데이터 페이지에 부여된 나이가 오래되고('Aging'이라",
            "   고 함) 결국 해당 페이지는 버퍼 풀에서 제거된다. 버퍼 풀의 데이터 페이지가 쿼리에 의해 사용되면 나이가 초기화",
            "   되어 다시 젊어지고 MRU의 헤더 부분으로 옮겨진다.",
            "",
            "5. 필요한 데이터가 자주 접근됐다면 해당 페이지의 인덱스 키를 어댑티브 해시 인덱스에 추가"
        ]
        
        # 텍스트 그리기
        y_offset = 80
        line_height = 28
        
        for line in text_content:
            # 들여쓰기 처리
            x_offset = 50
            if line.startswith("   "):
                x_offset = 80
                line = line.strip()
            
            draw.text((x_offset, y_offset), line, font=font_body, fill='black')
            y_offset += line_height
        
        # 하단 안내 메시지
        draw.text((50, height - 60), "Controls: WASD(오프셋), ↑↓←→(스케일), R(리셋), Q(종료)", 
                 font=font_body, fill='blue')
        
        return np.array(img)
    
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
    
    def calculate_custom_gaze(self, landmarks, frame_shape):
        """개선된 시선 계산"""
        # 눈 중심과 홍채 위치 계산
        left_eye_center = self.analyzer.gaze_tracker.get_eye_center(
            landmarks, self.analyzer.gaze_tracker.LEFT_EYE_INDICES, frame_shape)
        right_eye_center = self.analyzer.gaze_tracker.get_eye_center(
            landmarks, self.analyzer.gaze_tracker.RIGHT_EYE_INDICES, frame_shape)
        
        left_iris = self.analyzer.gaze_tracker.get_iris_position(
            landmarks, self.analyzer.gaze_tracker.LEFT_IRIS_INDICES, frame_shape)
        right_iris = self.analyzer.gaze_tracker.get_iris_position(
            landmarks, self.analyzer.gaze_tracker.RIGHT_IRIS_INDICES, frame_shape)
        
        # 시선 벡터 계산
        left_gaze_vector = left_iris - left_eye_center
        right_gaze_vector = right_iris - right_eye_center
        avg_gaze_vector = (left_gaze_vector + right_gaze_vector) / 2
        
        # 머리 위치 기반 앵커 포인트
        face_center_x = landmarks.landmark[9].x * frame_shape[1]
        face_center_y = landmarks.landmark[9].y * frame_shape[0]
        
        # 동적 스케일 조정
        eye_distance = np.linalg.norm(left_eye_center - right_eye_center)
        scale_factor = 150 / max(eye_distance, 50)
        
        # 최종 시선 위치 계산 (좌우 반전 수정)
        gaze_x = face_center_x - avg_gaze_vector[0] * self.h_scale * scale_factor + self.offset_x
        gaze_y = face_center_y + avg_gaze_vector[1] * self.v_scale * scale_factor + self.offset_y
        
        # 스무딩 적용
        gaze_x, gaze_y = self.smooth_gaze(gaze_x, gaze_y)
        
        # 화면 경계 내로 제한
        gaze_x = np.clip(gaze_x, 0, frame_shape[1] - 1)
        gaze_y = np.clip(gaze_y, 0, frame_shape[0] - 1)
        
        return int(gaze_x), int(gaze_y)
    
    def run(self):
        # 한글 텍스트 이미지 생성
        text_image = self.create_korean_text_image()
        
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        cv2.namedWindow('Camera Feed', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Korean Text Display', cv2.WINDOW_NORMAL)
        
        print("=" * 60)
        print("한글 텍스트 시선 추적 테스트")
        print("=" * 60)
        print("LRU 리스트 구조 문서를 보면서 시선을 추적합니다.")
        print("=" * 60)
        
        gaze_trail = deque(maxlen=50)
        heatmap = np.zeros(text_image.shape[:2], dtype=np.float32)
        reading_words = []
        fixation_points = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            
            # 얼굴 랜드마크 감지
            landmarks = self.analyzer.gaze_tracker.detect_eyes(frame)
            
            # 텍스트 이미지 복사
            display_image = text_image.copy()
            
            if landmarks:
                # 시선 위치 계산
                gaze_x, gaze_y = self.calculate_custom_gaze(landmarks, text_image.shape)
                
                # 시선 궤적 저장
                gaze_trail.append((gaze_x, gaze_y))
                
                # 히트맵 업데이트
                cv2.circle(heatmap, (gaze_x, gaze_y), 20, 1.0, -1)
                
                # 시선 궤적 그리기
                for i in range(1, len(gaze_trail)):
                    alpha = i / len(gaze_trail)
                    thickness = max(1, int(3 * alpha))
                    color = (0, int(255 * alpha), 0)
                    cv2.line(display_image, gaze_trail[i-1], gaze_trail[i], color, thickness)
                
                # 현재 시선 포인트
                cv2.circle(display_image, (gaze_x, gaze_y), 15, (0, 255, 0), -1)
                cv2.circle(display_image, (gaze_x, gaze_y), 20, (0, 255, 0), 2)
                
                # 십자선
                cv2.line(display_image, (gaze_x - 25, gaze_y), (gaze_x + 25, gaze_y), (0, 255, 0), 1)
                cv2.line(display_image, (gaze_x, gaze_y - 25), (gaze_x, gaze_y + 25), (0, 255, 0), 1)
                
                # 카메라 화면에 눈 위치 표시
                left_eye = self.analyzer.gaze_tracker.get_eye_center(
                    landmarks, self.analyzer.gaze_tracker.LEFT_EYE_INDICES, frame.shape)
                right_eye = self.analyzer.gaze_tracker.get_eye_center(
                    landmarks, self.analyzer.gaze_tracker.RIGHT_EYE_INDICES, frame.shape)
                
                cv2.circle(frame, tuple(left_eye), 5, (255, 0, 0), -1)
                cv2.circle(frame, tuple(right_eye), 5, (255, 0, 0), -1)
            
            # 설정 정보 표시
            info_text = [
                f"H-Scale: {self.h_scale} | V-Scale: {self.v_scale}",
                f"Offset: ({self.offset_x:+.0f}, {self.offset_y:+.0f})",
            ]
            
            y_pos = 30
            for text in info_text:
                cv2.putText(frame, text, (10, y_pos), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                y_pos += 25
            
            cv2.imshow('Camera Feed', frame)
            cv2.imshow('Korean Text Display', display_image)
            
            # 키보드 입력 처리
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('w'):  # 위로 오프셋
                self.offset_y -= 20
                print(f"Offset Y: {self.offset_y}")
            elif key == ord('s'):  # 아래로 오프셋
                self.offset_y += 20
                print(f"Offset Y: {self.offset_y}")
            elif key == ord('a'):  # 왼쪽 오프셋
                self.offset_x -= 20
                print(f"Offset X: {self.offset_x}")
            elif key == ord('d'):  # 오른쪽 오프셋
                self.offset_x += 20
                print(f"Offset X: {self.offset_x}")
            elif key == 82:  # ↑ 키
                self.v_scale += 10
                print(f"V-Scale: {self.v_scale}")
            elif key == 84:  # ↓ 키
                self.v_scale = max(10, self.v_scale - 10)
                print(f"V-Scale: {self.v_scale}")
            elif key == 81:  # ← 키
                self.h_scale = max(10, self.h_scale - 10)
                print(f"H-Scale: {self.h_scale}")
            elif key == 83:  # → 키
                self.h_scale += 10
                print(f"H-Scale: {self.h_scale}")
            elif key == ord('r'):  # 리셋
                self.h_scale = 200
                self.v_scale = 120
                self.offset_x = 0
                self.offset_y = 0
                print("Settings reset")
            elif key == ord('h'):  # 히트맵 표시
                # 히트맵 정규화 및 컬러맵 적용
                heatmap_norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX)
                heatmap_color = cv2.applyColorMap(heatmap_norm.astype(np.uint8), cv2.COLORMAP_JET)
                blended = cv2.addWeighted(display_image, 0.7, heatmap_color, 0.3, 0)
                cv2.imshow('Heatmap', blended)
            elif key == ord('c'):  # 클리어
                gaze_trail.clear()
                heatmap = np.zeros(text_image.shape[:2], dtype=np.float32)
                print("Cleared")
        
        cap.release()
        cv2.destroyAllWindows()
        
        print("\n" + "=" * 60)
        print("세션 종료")
        print(f"최종 설정값:")
        print(f"  H-Scale: {self.h_scale}")
        print(f"  V-Scale: {self.v_scale}")
        print(f"  Offset: ({self.offset_x}, {self.offset_y})")
        print("=" * 60)

if __name__ == "__main__":
    tracker = KoreanTextGazeTracker()
    tracker.run()