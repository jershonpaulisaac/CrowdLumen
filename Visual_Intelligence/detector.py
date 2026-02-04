from ultralytics import YOLO
import cv2
import numpy as np

class HumanDetector:
    def __init__(self, model_path='yolov8n.pt', confidence=0.3):
        print(f"Loading YOLO model from {model_path}...")
        self.model = YOLO(model_path)
        self.confidence = confidence
        # COCO class 0 is 'person'
        self.target_class = 0 

    def detect(self, frame):
        """
        Detects humans in the frame.
        Returns a list of bounding boxes [(x1, y1, x2, y2), ...]
        """
        # Optimize: restrict to class 0 (person) directly in inference
        results = self.model(frame, verbose=False, stream=True, classes=[0], conf=self.confidence)
        rects = []
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # No need to check class here if we filtered in model()
                x1, y1, x2, y2 = box.xyxy[0]
                rects.append((int(x1), int(y1), int(x2), int(y2)))
        
        return rects
