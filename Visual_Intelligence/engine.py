import cv2
import time
import numpy as np
import datetime
import csv
import os
import threading
from detector import HumanDetector
from tracker import CentroidTracker

# Video Processing Config
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_SKIP = 2 # Process every Nth frame for performance

# Grid Config (4x6 cells)
GRID_ROWS = 4
GRID_COLS = 6
CELL_W = FRAME_WIDTH // GRID_COLS
CELL_H = FRAME_HEIGHT // GRID_ROWS

# Thresholds
DENSITY_SAFE = 2
DENSITY_MODERATE = 4

LOG_FILE = "crowd_intelligence_log.csv"

class VisualEngine:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.detector = HumanDetector(confidence=0.35)
        self.tracker = CentroidTracker(max_disappeared=15)
        
        # Analytics State
        self.object_speeds = {}       
        self.object_directions = {}   
        self.prev_centroids = {}      
        self.grid_density = np.zeros((GRID_ROWS, GRID_COLS), dtype=int)
        self.flow_conflicts = []      
        
        # Public Metrics
        self.person_count = 0
        self.chaos_metric = 0.0
        self.risk_level = 0.0 # 0.0 to 1.0
        self.current_threat = "NORMAL"
        self.threat_color = "green"
        self.current_reason = "System Initializing..."
        
        # Thread Decoupling State
        self.latest_raw_frame = None
        self.current_frame = None
        self.last_rects = []
        self.last_objects = {}
        self.lock = threading.Lock()
        
        self.running = False
        self._init_log()
        
    def _init_log(self):
        if not os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, mode='w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "TotalCount", "MaxDensity", "FlowConflicts", "ChaosMetric", "RiskScore", "Alert"])
            except:
                pass

    def _log_event(self, reason):
        try:
            with open(LOG_FILE, mode='a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    self.person_count,
                    np.max(self.grid_density) if self.grid_density.size > 0 else 0,
                    len(self.flow_conflicts),
                    round(self.chaos_metric, 2),
                    round(self.risk_level, 2),
                    reason
                ])
        except:
            pass

    def start(self):
        if self.cap is not None:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(self.camera_index)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) 
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        self.running = True
        
        threading.Thread(target=self._capture_and_render_loop, daemon=True).start()
        threading.Thread(target=self._process_loop, daemon=True).start()

    def set_camera(self, index):
        self.camera_index = index
        self.start()

    def _capture_and_render_loop(self):
        """ Runs at max camera FPS (e.g. 30fps). Overlays the *latest* AI data immediately. """
        while self.running:
            if self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
                    self.latest_raw_frame = frame.copy()
                    
                    # Instantly draw the last known AI data on this frame
                    annotated_frame = self.draw_predictive_hud(frame, self.last_rects, self.last_objects)
                    
                    with self.lock:
                        self.current_frame = annotated_frame
                else:
                    time.sleep(0.01)
            else:
                time.sleep(0.1)

    def _process_loop(self):
        """ Runs at whatever speed YOLO can handle (e.g. 5-10fps). Updates the AI data gracefully. """
        while self.running:
            if self.latest_raw_frame is None:
                time.sleep(0.01)
                continue
                
            frame_to_process = self.latest_raw_frame
            self.latest_raw_frame = None # Consume it
            
            # Heavy AI Inference
            rects = self.detector.detect(frame_to_process)
            objects = self.tracker.update(rects)
            
            # Run Analytics
            self.analyze_scene(objects)
            
            # Sync to render loop
            self.last_rects = rects
            self.last_objects = objects

    def analyze_scene(self, objects):
        count = len(objects)
        self.person_count = count
        self.grid_density.fill(0)
        self.flow_conflicts = []
        
        total_speed = 0
        current_directions = {}
        
        for obj_id, centroid in objects.items():
            # Grid Mapping
            col = min(centroid[0] // CELL_W, GRID_COLS - 1)
            row = min(centroid[1] // CELL_H, GRID_ROWS - 1)
            self.grid_density[row, col] += 1
            
            # Flow Analysis
            if obj_id in self.prev_centroids:
                prev = self.prev_centroids[obj_id]
                dx = centroid[0] - prev[0]
                dy = centroid[1] - prev[1]
                mag = np.sqrt(dx**2 + dy**2)
                
                if obj_id not in self.object_speeds: self.object_speeds[obj_id] = []
                self.object_speeds[obj_id].append(mag)
                if len(self.object_speeds[obj_id]) > 10: self.object_speeds[obj_id].pop(0)
                
                avg_obj_speed = np.mean(self.object_speeds[obj_id])
                total_speed += avg_obj_speed
                
                self.object_directions[obj_id] = (dx, dy)
                cell_key = (row, col)
                if cell_key not in current_directions: current_directions[cell_key] = []
                current_directions[cell_key].append((dx, dy))

            self.prev_centroids[obj_id] = centroid

        # Flow Conflict
        for cell, dirs in current_directions.items():
            if len(dirs) > 1:
                has_conflict = False
                for i in range(len(dirs)):
                    for j in range(i + 1, len(dirs)):
                        v1, v2 = np.array(dirs[i]), np.array(dirs[j])
                        norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
                        if norm1 > 2 and norm2 > 2:
                            dot = np.dot(v1, v2) / (norm1 * norm2)
                            if dot < -0.7: 
                                has_conflict = True; break
                    if has_conflict: break
                if has_conflict:
                    self.flow_conflicts.append(cell)

        # Chaos Metric
        avg_scene_speed = total_speed / count if count > 0 else 0
        self.chaos_metric = avg_scene_speed
        
        # Risk Scoring
        max_dens = np.max(self.grid_density) if count > 0 else 0
        dens_score = min(max_dens / 8.0, 1.0)
        conflict_score = min(len(self.flow_conflicts) / 3.0, 1.0)
        chaos_score = min(avg_scene_speed / 25.0, 1.0)
        
        self.risk_level = (dens_score * 0.4) + (conflict_score * 0.3) + (chaos_score * 0.3)
        
        status, color, reason = "NORMAL", "green", "Clear and orderly flow."
        if self.risk_level > 0.7:
            status, color, reason = "CRITICAL", "#FF3333", "HIGH RISK: Flow conflicts + Heavy overcrowding detected!"
        elif self.risk_level > 0.4:
            status, color, reason = "WARNING", "#FFBB00", "WARNING: Moderate congestion with conflicting movement."
        elif count > 0 and avg_scene_speed > 20:
             status, color, reason = "PANIC?", "#FF00FF", "SUSPICIOUS: Sudden high-speed movement detected."

        self.current_threat = status
        self.threat_color = color
        self.current_reason = reason
        
        if self.risk_level > 0.4 and self.frame_count % 30 == 0:
            self._log_event(status)

    def draw_predictive_hud(self, frame, rects, objects):
        overlay = frame.copy()
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                count = self.grid_density[r, c]
                color = (0, 255, 0)
                if count >= DENSITY_MODERATE:
                    color = (0, 0, 255)
                elif count >= DENSITY_SAFE:
                    color = (0, 165, 255)
                
                cv2.rectangle(overlay, (c*CELL_W, r*CELL_H), ((c+1)*CELL_W, (r+1)*CELL_H), color, -1)
                cv2.rectangle(frame, (c*CELL_W, r*CELL_H), ((c+1)*CELL_W, (r+1)*CELL_H), (255,255,255), 1)
        
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        for obj_id, centroid in objects.items():
            if obj_id in self.object_directions:
                dx, dy = self.object_directions[obj_id]
                end_pt = (int(centroid[0] + dx * 2), int(centroid[1] + dy * 2))
                cv2.arrowedLine(frame, (centroid[0], centroid[1]), end_pt, (255, 255, 0), 2, tipLength=0.3)
                cv2.circle(frame, (centroid[0], centroid[1]), 3, (0, 0, 255), -1)

        for (r, c) in self.flow_conflicts:
            cv2.circle(frame, (c*CELL_W + CELL_W//2, r*CELL_H + CELL_H//2), 30, (255, 0, 255), 3)
            cv2.putText(frame, "CONFLICT", (c*CELL_W + 5, r*CELL_H + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,255), 2)

        if self.risk_level > 0.4:
            txt = "!!! RISK ALERT: CONGESTION DETECTED !!!"
            cv2.rectangle(frame, (50, 420), (590, 460), (0, 0, 0), -1)
            cv2.putText(frame, txt, (70, 445), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        return frame

    def generate_frames(self):
        while True:
            with self.lock:
                if self.current_frame is None:
                    continue
                ret, buffer = cv2.imencode('.jpg', self.current_frame)
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            else:
                time.sleep(0.01)

    def get_metrics(self):
        max_dens = int(np.max(self.grid_density)) if self.person_count > 0 else 0
        return {
            "count": self.person_count,
            "chaos": round(self.chaos_metric, 2),
            "threat": self.current_threat,
            "color": self.threat_color,
            "reason": self.current_reason,
            "conflicts": len(self.flow_conflicts),
            "maxDensity": max_dens,
            "riskScore": round(self.risk_level * 100, 1)
        }

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
