import cv2
import numpy as np
import pytesseract
from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class TextRegion:
    text: str
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    confidence: float
    word_id: int

class TextDetector:
    def __init__(self):
        self.current_regions = []
        self.text_history = []
        
    def detect_text_regions(self, frame) -> List[TextRegion]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        try:
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        except Exception as e:
            print(f"OCR Error: {e}")
            return []
        
        regions = []
        n_boxes = len(data['text'])
        
        for i in range(n_boxes):
            if int(data['conf'][i]) > 30:  # Confidence threshold
                text = data['text'][i].strip()
                if text:
                    x, y, w, h = (data['left'][i], data['top'][i], 
                                 data['width'][i], data['height'][i])
                    
                    region = TextRegion(
                        text=text,
                        bbox=(x, y, w, h),
                        confidence=float(data['conf'][i]),
                        word_id=i
                    )
                    regions.append(region)
        
        self.current_regions = regions
        return regions
    
    def create_text_overlay(self, frame, show_regions=True) -> np.ndarray:
        overlay = frame.copy()
        
        if not show_regions:
            return overlay
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        font_color = (255, 255, 255)
        line_type = 2
        
        for region in self.current_regions:
            x, y, w, h = region.bbox
            
            cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            label = f"{region.text[:20]}"
            cv2.putText(overlay, label, (x, y - 10), 
                       font, font_scale, font_color, line_type)
        
        return overlay
    
    def get_region_at_point(self, x: int, y: int) -> Optional[TextRegion]:
        for region in self.current_regions:
            rx, ry, rw, rh = region.bbox
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return region
        return None
    
    def analyze_reading_area(self, gaze_points: List[Tuple[int, int]], 
                            time_window: float = 0.5) -> List[TextRegion]:
        if not gaze_points or not self.current_regions:
            return []
        
        region_hits = {}
        
        for gaze_x, gaze_y in gaze_points:
            region = self.get_region_at_point(gaze_x, gaze_y)
            if region:
                if region.word_id not in region_hits:
                    region_hits[region.word_id] = 0
                region_hits[region.word_id] += 1
        
        focused_regions = []
        min_hits = len(gaze_points) * 0.3
        
        for region in self.current_regions:
            if region.word_id in region_hits and region_hits[region.word_id] >= min_hits:
                focused_regions.append(region)
        
        return focused_regions
    
    def generate_text_heatmap(self, frame_shape: Tuple[int, int], 
                             gaze_points: List[Tuple[int, int]]) -> np.ndarray:
        heatmap = np.zeros(frame_shape[:2], dtype=np.float32)
        
        for gaze_x, gaze_y in gaze_points:
            if 0 <= gaze_x < frame_shape[1] and 0 <= gaze_y < frame_shape[0]:
                cv2.circle(heatmap, (gaze_x, gaze_y), 30, 1.0, -1)
        
        heatmap = cv2.GaussianBlur(heatmap, (31, 31), 0)
        heatmap = np.clip(heatmap * 255, 0, 255).astype(np.uint8)
        
        heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        return heatmap_colored