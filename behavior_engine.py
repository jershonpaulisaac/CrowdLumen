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
        self.state_buffers = {} # Sliding window for state smoothing
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

    def _calculate_dynamics(self, history):
        """
        Calculate Velocity, Speed, and Acceleration.
        """
        if len(history) < 3: return 0.0, 0.0, (0.0, 0.0)
        
        # Recent points (last 5)
        pts = list(history)[-5:]
        
        # Velocity (dx, dy)
        dx = pts[-1][0] - pts[0][0]
        dy = pts[-1][1] - pts[0][1]
        
        dist = np.sqrt(dx*dx + dy*dy)
        speed = float(dist)
        
        # Acceleration (Change in speed vs previous window)
        # We need more history for this.
        accel = 0.0
        if len(history) >= 10:
             prev_pts = list(history)[-10:-5]
             prev_dx = prev_pts[-1][0] - prev_pts[0][0]
             prev_dy = prev_pts[-1][1] - prev_pts[0][1]
             prev_speed = np.sqrt(prev_dx*prev_dx + prev_dy*prev_dy)
             accel = speed - prev_speed
             
        return speed, accel, (dx, dy)

    def analyze_behavior(self, context_settings=None):
        """
        Predictive Behavior Analysis: Trends, Flux, and Anomalies.
        """
        active_speeds = []
        accelerations = []
        flow_vectors = []
        active_count = 0
        
        action_counts = {
            'Sitting': 0, 'Standing': 0, 'Walking': 0, 'Running': 0, 'Unknown': 0
        }
        
        # Thresholds (Dynamic from Context later, for now Base)
        run_thresh = context_settings['speed_run_threshold'] if context_settings else config.SPEED_WALK_MAX
        
        for tid, history in self.track_history.items():
            pose_state = self.track_states.get(tid, "Unknown")
            
            # 1. Dynamics
            speed, accel, vector = self._calculate_dynamics(history)
            
            # Smooth Speed
            prev_speed = self.current_speeds.get(tid, 0)
            smoothed_speed = (prev_speed * 0.7) + (speed * 0.3)
            self.current_speeds[tid] = smoothed_speed
            
            # 2. Logic: Motion Override & Smoothing
            # (Re-using robust logic from previous step, adding Accel check)
            
            # Update Buffer
            if tid not in self.state_buffers: self.state_buffers[tid] = deque(maxlen=config.HISTORY_LENGTH)
            self.state_buffers[tid].append(pose_state)
            
            from collections import Counter
            utc = Counter(self.state_buffers[tid])
            stable_pose = utc.most_common(1)[0][0]
            
            final_action = stable_pose
            
            # Motion Rules
            if smoothed_speed > run_thresh:
                final_action = "Running"
            elif smoothed_speed > config.SPEED_STAND:
                final_action = "Walking"
                
            # Surge Detection (High Acceleration)
            if accel > 5.0: # Sudden burst
                # Could flag as sub-state "SURGE"
                pass
                
            self.track_states[tid] = final_action
            action_counts[final_action] = action_counts.get(final_action, 0) + 1
            
            if final_action != "Sitting":
                active_count += 1
                active_speeds.append(smoothed_speed)
                accelerations.append(accel)
                flow_vectors.append(vector)

        # --- Aggregate Metrics for Prediction ---
        avg_speed = np.mean(active_speeds) if active_speeds else 0
        avg_accel = np.mean(accelerations) if accelerations else 0
        
        # Trend Analysis (Slope of Avg Speed)
        # We need global history of Avg Speed to get slope.
        # This function is stateless per call? No, class is persistent.
        if not hasattr(self, 'speed_trend_buffer'): self.speed_trend_buffer = deque(maxlen=30)
        self.speed_trend_buffer.append(avg_speed)
        
        trend_slope = 0.0
        if len(self.speed_trend_buffer) >= 10:
             y = np.array(self.speed_trend_buffer)
             x = np.arange(len(y))
             # Linear Regression: Slope
             slope, _ = np.polyfit(x, y, 1)
             trend_slope = slope

        # Chaos / Flux
        flux_score = 0.0
        if flow_vectors:
            # Variance of vectors means chaos
            vecs = np.array(flow_vectors) # (N, 2)
            if len(vecs) > 1:
                mean_vec = np.mean(vecs, axis=0)
                # Flux = Mean distance from mean vector
                diffs = vecs - mean_vec
                flux = np.mean(np.linalg.norm(diffs, axis=1))
                flux_score = flux
                
        # Speed Anomaly
        speed_anomaly = (avg_speed > run_thresh) or (avg_accel > 3.0)

        return {
            "avg_speed": float(avg_speed),
            "avg_accel": float(avg_accel),
            "trend_slope": float(trend_slope), # +ve means getting faster
            "flux_score": float(flux_score),
            "speed_anomaly": bool(speed_anomaly),
            "active_count": active_count,
            "action_counts": action_counts
        }
    
    def get_track_action(self, tid, context_settings=None):
        return self.track_states.get(tid, "Unknown")
