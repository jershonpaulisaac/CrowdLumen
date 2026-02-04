import cv2
import time
import numpy as np
from detector import HumanDetector
from tracker import CentroidTracker

# --- CONFIGURATION ---
WIDTH, HEIGHT = 640, 480
SPEED_HISTORY_LEN = 10
SURGE_THRESHOLD_WARNING = 15.0  # Pixels/frame avg speed
SURGE_THRESHOLD_CRITICAL = 25.0
DENSITY_WARNING = 8
DENSITY_CRITICAL = 12

from threading import Thread

class ThreadedCamera:
    def __init__(self, src=0, width=640, height=480):
        self.src = src
        self.width = width
        self.height = height
        self.cap = cv2.VideoCapture(self.src, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
             self.cap = cv2.VideoCapture(self.src)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        self.grabbed, self.frame = self.cap.read()
        self.stopped = False
        self.update_thread = None

    def start(self):
        self.update_thread = Thread(target=self.update, args=())
        self.update_thread.daemon = True
        self.update_thread.start()
        return self

    def update(self):
        while True:
            if self.stopped:
                return
            
            grabbed, frame = self.cap.read()
            if grabbed:
                self.grabbed = grabbed
                self.frame = frame
    
    def read(self):
        return self.grabbed, self.frame

    def stop(self):
        self.stopped = True
        if self.update_thread:
            self.update_thread.join()
        self.cap.release()

class CameraSystem:
    def __init__(self):
        self.camera_index = 0
        self.stream = None # Threaded Camera
        # Use Medium model for 'training' equivalent (better accuracy) but can be heavy.
        # We will optimize by tracking more frames between detections.
        self.detector = HumanDetector(model_path='yolov8m.pt', confidence=0.35) 
        self.tracker = CentroidTracker(max_disappeared=15)
        
        # State
        self.frame_counter = 0
        self.last_rects = []
        
        # Analysis Data
        self.prev_centroids = {}
        self.object_speeds = {}
        
        # Public Metrics
        self.status_data = {
            "threat_level": "NORMAL",
            "threat_color": "var(--status-normal)", 
            "person_count": 0,
            "chaos_metric": 0.0,
            "reason": "System Initialized. Monitoring...",
            "history": [] # For graph
        }
        
        self.open_camera(0)

    def open_camera(self, index):
        if self.stream:
            self.stream.stop()
        try:
            self.stream = ThreadedCamera(index, WIDTH, HEIGHT).start()
            self.camera_index = index
        except Exception as e:
            print(f"Camera Error: {e}")

    def read_processed_frame(self):
        """Returns (frame_rgb, status_data) for Streamlit"""
        if not self.stream:
             return None, self.status_data

        success, frame = self.stream.read()
        if not success or frame is None:
            return None, self.status_data

        # Resize & Process
        frame = cv2.resize(frame, (WIDTH, HEIGHT))
        processed_frame = self.process_ai(frame)
        
        # Convert to RGB for Streamlit/PIL
        frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        return frame_rgb, self.status_data

    def get_frame(self):
        """Used by the MJPEG streamer"""
        # ... logic for MJPEG if needed, but we focus on Streamlit now ...
        pass 

    def process_ai(self, frame):
        self.frame_counter += 1
        
        # 1. Detect (Every 5th frame instead of 3rd for speed + smoothness)
        # Tracking handles the in-between frames efficiently.
        if self.frame_counter % 5 == 0:
            self.last_rects = self.detector.detect(frame)
        
        rects = self.last_rects
        
        # 2. Track (Every frame for smoothness)
        objects = self.tracker.update(rects)
        
        # 3. Analyze
        self.analyze_threats(objects)
        
        # 4. Draw Overlay (Professional Corners)
        for (x1, y1, x2, y2) in rects:
            # Determine color based on threat
            color = (0, 255, 0)
            if self.status_data["threat_level"] == "WARNING": color = (0, 255, 255)
            elif self.status_data["threat_level"] == "CRITICAL": color = (0, 0, 255)
            
            # Draw professional corners instead of full box
            self.draw_corners(frame, (x1, y1), (x2, y2), color)
            
            # Label
            # cv2.putText(frame, "PERSON", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        return frame

    def draw_corners(self, img, pt1, pt2, color, thickness=2, r=10, d=20):
        x1, y1 = pt1
        x2, y2 = pt2
        # Top Left
        cv2.line(img, (x1, y1), (x1 + d, y1), color, thickness)
        cv2.line(img, (x1, y1), (x1, y1 + d), color, thickness)
        # Top Right
        cv2.line(img, (x2, y1), (x2 - d, y1), color, thickness)
        cv2.line(img, (x2, y1), (x2, y1 + d), color, thickness)
        # Bottom Left
        cv2.line(img, (x1, y2), (x1 + d, y2), color, thickness)
        cv2.line(img, (x1, y2), (x1, y2 - d), color, thickness)
        # Bottom Right
        cv2.line(img, (x2, y2), (x2 - d, y2), color, thickness)
        cv2.line(img, (x2, y2), (x2, y2 - d), color, thickness)

    def analyze_threats(self, objects):
        current_ids = list(objects.keys())
        total_speed = 0
        moving_people_count = 0
        
        # --- Speed Analysis ---
        for obj_id, centroid in objects.items():
            if obj_id in self.prev_centroids:
                prev_c = self.prev_centroids[obj_id]
                dist = np.linalg.norm(np.array(centroid) - np.array(prev_c))
                
                # Update history
                if obj_id not in self.object_speeds:
                    self.object_speeds[obj_id] = []
                self.object_speeds[obj_id].append(dist)
                if len(self.object_speeds[obj_id]) > SPEED_HISTORY_LEN:
                    self.object_speeds[obj_id].pop(0)
                
                # Get smoothed speed
                avg_obj_speed = np.mean(self.object_speeds[obj_id])
                
                # IGNORE MINOR MOVEMENT (Walking/Fidgeting)
                if avg_obj_speed > 3.0: 
                    total_speed += avg_obj_speed
                    moving_people_count += 1
            
            self.prev_centroids[obj_id] = centroid

        # Cleanup
        for old_id in list(self.prev_centroids.keys()):
            if old_id not in current_ids:
                del self.prev_centroids[old_id]
                if old_id in self.object_speeds:
                    del self.object_speeds[old_id]

        # --- Crowd Metrics ---
        count = len(objects)
        # Average speed of the *moving* crowd only (to catch surges)
        avg_crowd_speed = (total_speed / moving_people_count) if moving_people_count > 0 else 0
        
        # Chaos Metric (Scaled 0-100 for UI)
        chaos_val = min((avg_crowd_speed / 20.0) * 100, 100)
        
        # --- Threat Logic ---
        threat = "NORMAL"
        color = "var(--status-normal)"
        reason = "Stable conditions. Movement is within normal limits."
        
        # 1. Check Surge (Speed)
        if avg_crowd_speed > SURGE_THRESHOLD_CRITICAL and moving_people_count > 2:
            threat = "CRITICAL"
            color = "var(--status-critical)"
            reason = "CRITICAL: RAPID CROWD SURGE DETECTED (High Velocity)"
        elif avg_crowd_speed > SURGE_THRESHOLD_WARNING and moving_people_count > 2:
            threat = "WARNING"
            color = "var(--status-warning)"
            reason = "WARNING: Crowd movement is accelerating abnormally."
        
        # 2. Check Density (Count) - Override if higher threat
        elif count > DENSITY_CRITICAL:
             if threat != "CRITICAL":
                threat = "CRITICAL"
                color = "var(--status-critical)"
                reason = "CRITICAL: Severe Overcrowding. Capacity limit breached."
        elif count > DENSITY_WARNING:
             if threat == "NORMAL": # Don't downgrade a speed warning
                threat = "WARNING"
                color = "var(--status-warning)"
                reason = "WARNING: Crowd density is high."
        
        # 3. Stability Check (If chaos is very low but count is high -> Stationary Crowd)
        if threat == "NORMAL" and count > 0:
            reason = f"Monitoring {count} individuals. Behavior is stable."

        # History update
        history = self.status_data.get("history", [])
        history.append(int(chaos_val))
        if len(history) > 50:
            history.pop(0)

        # Update State
        self.status_data = {
            "threat_level": threat,
            "threat_color": color,
            "person_count": count,
            "chaos_metric": int(chaos_val),
            "reason": reason,
            "history": history
        }
