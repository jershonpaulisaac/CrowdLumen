import numpy as np
from collections import deque
import config

class BehaviorAnalyzer:
    def __init__(self):
        # Dictionary to store history: {track_id: deque([(x, y, frame_num), ...])}
        self.track_history = {}
        self.max_history = config.HISTORY_LENGTH
        self.frame_count = 0
        self.track_states = {} # Store last known state from Pose (Sit/Stand/Unknown)
        self.current_speeds = {} # Store current speed per track

    def update_tracks(self, tracks, states):
        """
        Update track histories and valid states.
        """
        self.frame_count += 1
        self.track_states = states # Update states map
        
        current_ids = []
        if tracks.id is not None:
            current_ids = tracks.id.cpu().numpy().astype(int)
            boxes = tracks.xywh.cpu().numpy() # x_center, y_center, w, h
            
            for i, track_id in enumerate(current_ids):
                if track_id not in self.track_history:
                    self.track_history[track_id] = deque(maxlen=self.max_history)
                
                # Store center point
                x, y = boxes[i][:2]
                self.track_history[track_id].append((x, y))
        
        # Cleanup
        existing_ids = list(self.track_history.keys())
        for tid in existing_ids:
            if tid not in current_ids:
                del self.track_history[tid]
                if tid in self.current_speeds: del self.current_speeds[tid]

    def _calculate_speed(self, history):
        if len(history) < 5: return 0.0
        # Euclidean distance of last few frames
        pts = list(history)[-5:]
        dx = pts[-1][0] - pts[0][0]
        dy = pts[-1][1] - pts[0][1]
        dist = np.sqrt(dx*dx + dy*dy)
        return float(dist)

    def analyze_behavior(self, context_settings=None):
        """
        Calculate behavioral metrics and Classify Actions.
        context_settings: dict from ContextEngine
        """
        active_speeds = []
        angles = []
        active_count = 0
        
        # Action Counts
        action_counts = {
            'Sitting': 0,
            'Standing': 0,
            'Walking': 0,
            'Running': 0,
            'Lying': 0, # Future impl
            'Unknown': 0
        }
        
        # Thresholds
        run_thresh = context_settings['speed_run_threshold'] if context_settings else config.SPEED_WALK_MAX
        
        for tid, history in self.track_history.items():
            pose_state = self.track_states.get(tid, "Unknown")
            speed = self._calculate_speed(history)
            self.current_speeds[tid] = speed
            
            # Action Classification Logic
            action = "Unknown"
            
            if pose_state == "Sitting":
                action = "Sitting"
            else:
                # State is "Standing" (or Unknown). Check speed.
                if speed < config.SPEED_STAND:
                    action = "Standing"
                elif speed < run_thresh:
                    action = "Walking"
                else:
                    action = "Running"
            
            action_counts[action] = action_counts.get(action, 0) + 1
            
            # For Threat Analysis: exclude Sitting people
            if action != "Sitting":
                active_count += 1
                active_speeds.append(speed)
                
                # Calculate angle for chaos
                if len(history) >= 5:
                    pts = list(history)[-5:]
                    dx = pts[-1][0] - pts[0][0]
                    dy = pts[-1][1] - pts[0][1]
                    raw_speed = np.sqrt(dx*dx + dy*dy)
                    
                    # Perspective Correction (Phase 6 Fix)
                    # y=0(top) -> factor=Max, y=480(bottom) -> factor=1.0
                    y_pos = pts[-1][1]
                    norm_y = max(0, min(1, y_pos / 480.0)) # 0.0 top, 1.0 bottom
                    # If at bottom(1.0), mult=1. If at top(0.0), mult = 1 + PERSPECTIVE
                    correction_mult = 1.0 + ((1.0 - norm_y) * config.PERSPECTIVE_FACTOR)
                    
                    corrected_speed = raw_speed * correction_mult
                    
                    # Update metrics with corrected speed
                    active_speeds.append(corrected_speed)
                    
                    # Recalculate chaos angle
                    angles.append(np.arctan2(dy, dx))
        
        # Metrics
        avg_speed = np.mean(active_speeds) if active_speeds else 0
        speed_anomaly = avg_speed > run_thresh 
        
        if angles and len(angles) > 1:
            hist, _ = np.histogram(angles, bins=8, range=(-np.pi, np.pi))
            probabilities = hist / len(angles)
            entropy = -np.sum(probabilities * np.log(probabilities + 1e-6))
        else:
            entropy = 0
            
        return {
            "avg_speed": float(avg_speed),
            "speed_anomaly": bool(speed_anomaly),
            "chaos_score": float(entropy),
            "active_count": active_count,
            "action_counts": action_counts
        }
    
    def get_track_action(self, tid, context_settings=None):
        """Returns the specific action for a track ID for visualization"""
        # Duplicate logic briefly for single track query (or cache it)
        pose_state = self.track_states.get(tid, "Unknown")
        speed = self.current_speeds.get(tid, 0)
        run_thresh = context_settings['speed_run_threshold'] if context_settings else config.SPEED_WALK_MAX
        
        if pose_state == "Sitting": return "Sitting"
        if speed < config.SPEED_STAND: return "Standing"
        if speed < run_thresh: return "Walking"
        return "Running"
