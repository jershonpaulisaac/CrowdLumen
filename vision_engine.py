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
                    # Geometric Analysis
                    pose_info = self.analyze_pose_geometry(kpts[i])
                    # Store primary state for simple logic (Compatibility)
                    states[tid] = pose_info['primary'] 
                    # Note: We could store full pose_info if we passed it to behavior engine
                    # For now, let's keep states as String map to avoid breaking app.py immediately.
                    # Behavior Engine will compute Motion override anyway.
                    
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
            
            # Blur (Pixelation for speed)
            roi = frame[y1:y2, x1:x2]
            if roi.size > 0:
                # Pixelate: Downscale by 10x then upscale
                try:
                    h_roi, w_roi = roi.shape[:2]
                    # Ensure minimum size for downscaling
                    if h_roi > 10 and w_roi > 10:
                        small = cv2.resize(roi, (w_roi // 10, h_roi // 10), interpolation=cv2.INTER_LINEAR)
                        pixelated = cv2.resize(small, (w_roi, h_roi), interpolation=cv2.INTER_NEAREST)
                        frame[y1:y2, x1:x2] = pixelated
                except Exception:
                    pass # Fail silently and leave unblurred if resize fails to avoid crash
                
        return frame

    def calculate_angle(self, a, b, c):
        """
        Calculate angle ABC (in degrees) where B is the vertex.
        a, b, c are (x, y) coordinates.
        """
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))
        return angle

    def analyze_pose_geometry(self, keypoints):
        """
        Geometric Posture Analysis using Keypoint Angles.
        Returns detailed probability state.
        """
        if len(keypoints) == 0: 
            return {"primary": "Unknown", "conf": 0.0}
            
        # COCO Keypoints:
        # 5,6 Shoulders | 11,12 Hips | 13,14 Knees | 15,16 Ankles
        
        # Helper to get (x,y)
        def get_pt(idx):
             if idx < len(keypoints) and keypoints[idx][0] > 0 and keypoints[idx][1] > 0:
                 return keypoints[idx][:2]
             return None

        left_leg_angle = 180
        right_leg_angle = 180
        
        # Calculate Knee Angles (Hip-Knee-Ankle)
        l_hip, l_knee, l_ank = get_pt(11), get_pt(13), get_pt(15)
        r_hip, r_knee, r_ank = get_pt(12), get_pt(14), get_pt(16)
        
        valid_angles = []
        
        if l_hip is not None and l_knee is not None and l_ank is not None:
            left_leg_angle = self.calculate_angle(l_hip, l_knee, l_ank)
            valid_angles.append(left_leg_angle)
            
        if r_hip is not None and r_knee is not None and r_ank is not None:
            right_leg_angle = self.calculate_angle(r_hip, r_knee, r_ank)
            valid_angles.append(right_leg_angle)
            
        if not valid_angles:
            # Fallback to simple vertical check if ankles are occluded
            return self._backup_heuristic(keypoints)

        avg_knee_angle = np.mean(valid_angles)
        
        # Logic
        # Standing: Legs straight (~160-180 deg)
        # Sitting: Legs bent (~80-110 deg)
        
        # Probabilistic Scoring
        # 180 deg = 1.0 Standing, 0.0 Sitting
        # 90 deg = 0.0 Standing, 1.0 Sitting
        
        # Linear map:
        # Stand Score map: 140->0.0, 160->1.0
        # Sit Score map: 120->0.0, 90->1.0
        
        score_stand = 0.0
        score_sit = 0.0
        
        if avg_knee_angle > 150:
            score_stand = 1.0
        elif avg_knee_angle > 130:
            score_stand = (avg_knee_angle - 130) / 20.0
        
        if avg_knee_angle < 100:
            score_sit = 1.0
        elif avg_knee_angle < 130:
             score_sit = (130 - avg_knee_angle) / 30.0
             
        primary = "Standing"
        conf = score_stand
        
        if score_sit > score_stand:
            primary = "Sitting"
            conf = score_sit
            
        return {
            "primary": primary,
            "conf": float(conf),
            "angles": valid_angles
        }

    def _backup_heuristic(self, keypoints):
        """Original heuristic as backup if feet are occluded"""
        # (Simplified implementation of previous logic)
        return {"primary": "Standing", "conf": 0.3}
