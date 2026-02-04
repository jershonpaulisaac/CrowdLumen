import cv2
import numpy as np
import time
import os

# --- CONFIGURATION ---
WIDTH = 640
HEIGHT = 480
MOTION_WARNING_THRESHOLD = 2.0  # Average motion magnitude
MOTION_CRITICAL_THRESHOLD = 5.0
INSTABILITY_THRESHOLD = 1.5     # Variance in direction? simplified to motion variance

class VisualMonitor:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.status = "NORMAL"
        self.reason = "Stable flow"
        self.prev_gray = None
        self.sustained_abnormal_start = None
        
        # Setup camera
        self.cap.set(3, WIDTH)
        self.cap.set(4, HEIGHT)

    def process_frame(self, frame):
        # Resize for consistent processing speed
        frame_resized = cv2.resize(frame, (WIDTH, HEIGHT))
        gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
        
        if self.prev_gray is None:
            self.prev_gray = gray
            return 0, 0
            
        # Optical Flow (Farneback)
        flow = cv2.calcOpticalFlowFarneback(self.prev_gray, gray, None, 
                                            0.5, 3, 15, 3, 5, 1.2, 0)
        
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        
        # Metrics
        avg_motion = np.mean(mag)
        # Using standard deviation of magnitude to detect erratic behavior
        motion_dev = np.std(mag)
        
        self.prev_gray = gray
        return avg_motion, motion_dev

    def analyze_metrics(self, avg_motion, motion_dev):
        current_status = "NORMAL"
        current_reason = "Smooth movement"
        
        # Thresholds
        if avg_motion > MOTION_CRITICAL_THRESHOLD:
            current_status = "CRITICAL"
            current_reason = "MASSIVE MOTION DETECTED"
        elif motion_dev > (MOTION_CRITICAL_THRESHOLD * 0.8):
             current_status = "CRITICAL"
             current_reason = "Chaotic / Panic Patterns"
        elif avg_motion > MOTION_WARNING_THRESHOLD:
            current_status = "WARNING"
            current_reason = "High activity level"
            
        # Sustained check
        if current_status != "NORMAL":
            if self.sustained_abnormal_start is None:
                self.sustained_abnormal_start = time.time()
            elif time.time() - self.sustained_abnormal_start > 4.0:
                 # If warning persists for 4s, it becomes critical (crowd surge)
                 if current_status == "WARNING":
                     current_status = "CRITICAL"
                     current_reason = "Sustained Crowd Density/Move"
        else:
            self.sustained_abnormal_start = None
            
        self.status = current_status
        self.reason = current_reason

    def draw_hud(self, frame, avg_motion, motion_dev):
        # Color coding
        color = (0, 255, 0) # Green
        if self.status == "WARNING":
            color = (0, 255, 255) # Yellow
        elif self.status == "CRITICAL":
            color = (0, 0, 255) # Red
            
        # Status Box
        cv2.rectangle(frame, (10, 10), (300, 100), (0, 0, 0), -1)
        cv2.putText(frame, f"STATUS: {self.status}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        cv2.putText(frame, f"REASON: {self.reason}", (20, 70), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Metrics
        cv2.putText(frame, f"Motion Idx: {avg_motion:.2f}", (10, HEIGHT - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Border for Critical
        if self.status == "CRITICAL":
            cv2.rectangle(frame, (0,0), (WIDTH, HEIGHT), color, 10)

        return frame

    def run(self):
        if not self.cap.isOpened():
            print("Error: Could not open video source.")
            return

        print("Visual Intelligence Online. Press 'q' to exit.")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                break
                
            # Process
            avg_m, m_dev = self.process_frame(frame)
            self.analyze_metrics(avg_m, m_dev)
            
            # Display
            final_frame = self.draw_hud(frame, avg_m, m_dev)
            cv2.imshow('CrowdLumen - Visual Intelligence', final_frame)
            
            # Terminal Output (optional, kept minimal to avoid spam)
            # print(f"\rStatus: {self.status} | Motion: {avg_m:.2f}", end="")
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    monitor = VisualMonitor()
    monitor.run()
