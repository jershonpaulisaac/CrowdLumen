from ultralytics import YOLO
import cv2
import config
import numpy as np

class PersonDetector:
    def __init__(self):
        print(f"Loading YOLOv8 Pose model: {config.YOLO_MODEL_NAME}...")
        self.model = YOLO(config.YOLO_MODEL_NAME)
        print("Model loaded.")

    def detect(self, frame):
        """
        Detects and Tracks people using Pose Estimation.
        Returns:
            count, annotated_frame, tracks, states, keypoints_data
        """
        results = self.model.track(
            frame, 
            persist=True,
            classes=[config.CLASS_ID_PERSON], 
            conf=config.CONFIDENCE_THRESHOLD,
            verbose=False,
            imgsz=(config.FRAME_HEIGHT, config.FRAME_WIDTH) if config.FRAME_WIDTH else 640
        )
        
        result = results[0]
        tracks = result.boxes
        keypoints = result.keypoints
        states = {}
        
        # Privacy Blur
        annotated_frame = frame.copy() 
        if config.PRIVACY_BLUR and keypoints is not None:
             annotated_frame = self.blur_faces(annotated_frame, keypoints)
        
        # If we want YOLO's default boxes on top of blurred frame:
        # annotated_frame = result.plot(img=annotated_frame) # This might re-draw unblurred? 
        # Actually plot() draws on the input image. Better to draw manually or blur first.
        # Ideally: Blur -> Detect? No, Detect -> Blur -> Draw.
        
        count = 0
        if tracks.id is not None:
            count = len(tracks.id)
            track_ids = tracks.id.cpu().numpy().astype(int)
            
            if keypoints is not None and keypoints.xy is not None:
                kpts = keypoints.xy.cpu().numpy()
                for i, tid in enumerate(track_ids):
                    states[tid] = self.check_pose_state(kpts[i])
                    
        else:
            count = len(tracks)

        # Draw boxes manually since we modified frame
        if tracks.id is not None:
             boxes = tracks.xyxy.cpu().numpy()
             for i, box in enumerate(boxes):
                 tid = track_ids[i]
                 state = states.get(tid, "Unknown")
                 
                 # Colors: Sitting=Green, Standing=Blue, we will add action text later locally
                 color = (0, 255, 0) if state == "Sitting" else (0, 0, 255)
                 
                 x1, y1, x2, y2 = map(int, box[:4])
                 cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                 # Text is handled by app.py using behavior engine now for consistency?
                 # Or just generic here.
                 cv2.putText(annotated_frame, f"ID:{tid}", (x1, y1 - 10), 
                             cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return count, annotated_frame, tracks, states

    def blur_faces(self, frame, keypoints):
        """
        Blur face regions based on Nose/Eye keypoints.
        COCO: 0=Nose, 1=LEye, 2=REye, 3=LEar, 4=REar
        """
        if keypoints.xy is None: return frame
        
        kpts = keypoints.xy.cpu().numpy()
        h, w = frame.shape[:2]
        
        for person_kpt in kpts:
            # Get face points
            face_pts = person_kpt[0:5] # Nose to Ears
            
            # Filter valid points (x,y > 0)
            valid_pts = face_pts[face_pts[:, 0] > 0]
            if len(valid_pts) < 2: continue
            
            # Bounding box of face
            min_x, min_y = np.min(valid_pts, axis=0)
            max_x, max_y = np.max(valid_pts, axis=0)
            
            # Add padding
            pad_x = int((max_x - min_x) * 0.5)
            pad_y = int((max_y - min_y) * 0.5)
            
            # Clamp
            x1 = max(0, int(min_x - pad_x))
            y1 = max(0, int(min_y - pad_y))
            x2 = min(w, int(max_x + pad_x))
            y2 = min(h, int(max_y + pad_y))
            
            # Blur
            roi = frame[y1:y2, x1:x2]
            if roi.size > 0:
                roi = cv2.GaussianBlur(roi, (25, 25), 30)
                frame[y1:y2, x1:x2] = roi
                
        return frame

    def check_pose_state(self, keypoints):
        """Sitting vs Standing check"""
        if len(keypoints) == 0: return "Standing"
        
        hip_y = []
        if keypoints[11][1] > 0: hip_y.append(keypoints[11][1])
        if keypoints[12][1] > 0: hip_y.append(keypoints[12][1])
        avg_hip_y = np.mean(hip_y) if hip_y else 0
        
        knee_y = []
        if keypoints[13][1] > 0: knee_y.append(keypoints[13][1])
        if keypoints[14][1] > 0: knee_y.append(keypoints[14][1])
        avg_knee_y = np.mean(knee_y) if knee_y else 0
        
        if avg_hip_y == 0 or avg_knee_y == 0: return "Standing"
            
        vertical_dist = avg_knee_y - avg_hip_y
        if vertical_dist < 30: return "Sitting"
            
        return "Standing"
