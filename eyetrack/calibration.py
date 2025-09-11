import cv2
import numpy as np
from gaze_tracker import EyeGazeTracker
import time

class GazeCalibration:
    def __init__(self):
        self.tracker = EyeGazeTracker()
        self.calibration_points = []
        self.calibration_data = []
        self.transformation_matrix = None
        
    def run_calibration(self, cap):
        """9-point 캘리브레이션 실행"""
        screen_width = 1280
        screen_height = 720
        
        # 9개 캘리브레이션 포인트 (3x3 그리드)
        points = [
            (screen_width * 0.1, screen_height * 0.1),  # 좌상
            (screen_width * 0.5, screen_height * 0.1),  # 중상
            (screen_width * 0.9, screen_height * 0.1),  # 우상
            (screen_width * 0.1, screen_height * 0.5),  # 좌중
            (screen_width * 0.5, screen_height * 0.5),  # 중앙
            (screen_width * 0.9, screen_height * 0.5),  # 우중
            (screen_width * 0.1, screen_height * 0.9),  # 좌하
            (screen_width * 0.5, screen_height * 0.9),  # 중하
            (screen_width * 0.9, screen_height * 0.9),  # 우하
        ]
        
        print("=" * 60)
        print("CALIBRATION MODE")
        print("=" * 60)
        print("Look at each red circle and press SPACE")
        print("Press ESC to skip calibration")
        print("=" * 60)
        
        for idx, (px, py) in enumerate(points):
            collected_gazes = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame = cv2.flip(frame, 1)
                
                # 캘리브레이션 포인트 표시
                display = np.zeros((screen_height, screen_width, 3), dtype=np.uint8)
                cv2.circle(display, (int(px), int(py)), 30, (0, 0, 255), -1)
                cv2.circle(display, (int(px), int(py)), 35, (255, 255, 255), 2)
                
                # 진행 상황 표시
                cv2.putText(display, f"Point {idx+1}/9", (50, 50),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                cv2.putText(display, "Look at the red circle and press SPACE", 
                           (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                
                # 시선 추적
                gaze_data = self.tracker.process_frame(frame)
                if gaze_data:
                    collected_gazes.append((gaze_data.x, gaze_data.y))
                    
                    # 최근 수집된 시선 표시
                    if len(collected_gazes) > 0:
                        avg_x = np.mean([g[0] for g in collected_gazes[-10:]])
                        avg_y = np.mean([g[1] for g in collected_gazes[-10:]])
                        cv2.circle(frame, (int(avg_x), int(avg_y)), 5, (0, 255, 0), -1)
                
                # 화면 표시
                combined = np.hstack([frame, display])
                combined = cv2.resize(combined, (1920, 540))
                cv2.imshow('Calibration', combined)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord(' ') and len(collected_gazes) >= 10:
                    # 평균 시선 위치 저장
                    avg_gaze_x = np.mean([g[0] for g in collected_gazes[-20:]])
                    avg_gaze_y = np.mean([g[1] for g in collected_gazes[-20:]])
                    
                    self.calibration_data.append({
                        'screen': (px, py),
                        'gaze': (avg_gaze_x, avg_gaze_y)
                    })
                    print(f"Point {idx+1} calibrated: Screen({px:.0f}, {py:.0f}) -> Gaze({avg_gaze_x:.0f}, {avg_gaze_y:.0f})")
                    break
                elif key == 27:  # ESC
                    return False
        
        # 변환 행렬 계산
        self.calculate_transformation()
        return True
    
    def calculate_transformation(self):
        """캘리브레이션 데이터로 변환 행렬 계산"""
        if len(self.calibration_data) < 4:
            print("Not enough calibration points!")
            return
        
        # 소스 포인트 (시선 좌표)와 대상 포인트 (화면 좌표) 준비
        src_points = np.array([d['gaze'] for d in self.calibration_data], dtype=np.float32)
        dst_points = np.array([d['screen'] for d in self.calibration_data], dtype=np.float32)
        
        # 호모그래피 행렬 계산
        self.transformation_matrix, _ = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)
        
        print("Calibration complete! Transformation matrix calculated.")
        
    def transform_gaze(self, gaze_x, gaze_y):
        """캘리브레이션된 변환 적용"""
        if self.transformation_matrix is None:
            return gaze_x, gaze_y
        
        # 변환 적용
        point = np.array([[[gaze_x, gaze_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, self.transformation_matrix)
        
        return transformed[0][0][0], transformed[0][0][1]
    
    def save_calibration(self, filename="calibration.npz"):
        """캘리브레이션 데이터 저장"""
        if self.transformation_matrix is not None:
            np.savez(filename, 
                    matrix=self.transformation_matrix,
                    data=self.calibration_data)
            print(f"Calibration saved to {filename}")
    
    def load_calibration(self, filename="calibration.npz"):
        """캘리브레이션 데이터 로드"""
        try:
            data = np.load(filename, allow_pickle=True)
            self.transformation_matrix = data['matrix']
            self.calibration_data = data['data'].tolist()
            print(f"Calibration loaded from {filename}")
            return True
        except:
            return False

if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    calibrator = GazeCalibration()
    
    # 캘리브레이션 실행
    if calibrator.run_calibration(cap):
        calibrator.save_calibration()
    
    cap.release()
    cv2.destroyAllWindows()