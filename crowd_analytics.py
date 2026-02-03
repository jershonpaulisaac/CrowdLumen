import config
import numpy as np
from collections import deque

class CrowdAnalyzer:
    def __init__(self):
        self.area = config.MONITORED_AREA_SQ_METERS
        
        # Predictive Buffers (History for Trends)
        self.audio_trend_buffer = deque(maxlen=60) # 2-3 seconds
        self.threat_trend_buffer = deque(maxlen=30)
    
    def analyze(self, count, behavior_metrics, context_settings=None, audio_stats=None):
        """
        Predictive Fusion Analysis.
        Inputs: 
          - behavior_metrics (from Behavior Engine: trends, slopes, flux)
          - audio_stats (from Frontend: db_level, risk)
        """
        
        # 1. Context & Density State
        density = count / self.area if self.area > 0 else 0
        
        # Adaptive Thresholds calculation
        # If density is high, we lower the tolerance for fast movement.
        density_factor = min(1.0, count / 20.0) # 0.0 to 1.0 (Saturation at 20 people)
        
        # Dynamic Run Threshold: Base 5.0 -> Reduces to 2.5 in dense crowd
        base_run = context_settings['speed_run_threshold'] if context_settings else config.SPEED_WALK_MAX
        dynamic_run_thresh = base_run * (1.0 - (density_factor * 0.5))
        
        # 2. Extract Behavior Signals
        avg_speed = behavior_metrics.get('avg_speed', 0)
        accel = behavior_metrics.get('avg_accel', 0)
        flux = behavior_metrics.get('flux_score', 0)
        speed_slope = behavior_metrics.get('trend_slope', 0)
        
        # 3. Extract Audio Signals & Calculate Trend
        audio_risk = 0.0
        audio_db = 0
        if audio_stats:
            audio_risk = audio_stats.get('risk_score', 0)
            audio_db = audio_stats.get('db_level', 0)
            self.audio_trend_buffer.append(audio_db)
            
        # Calc Audio Slope
        audio_slope = 0.0
        if len(self.audio_trend_buffer) >= 10:
             y = np.array(self.audio_trend_buffer)
             x = np.arange(len(y))
             slope, _ = np.polyfit(x, y, 1)
             audio_slope = slope # dB per frame change
        
        # 4. Multi-Modal Fusion Logic 
        
        # Base Threat (0-1)
        threat_level = 0.0
        visual_score = 0.0
        status_label = "NORMAL"
        
        # A. Visual Component
        # Speed contribution (weighted by density)
        speed_risk = min(1.0, avg_speed / dynamic_run_thresh)
        visual_score += speed_risk * 0.4
        
        # Flux/Chaos contribution
        flux_risk = min(1.0, flux / 50.0)
        visual_score += flux_risk * 0.3
        
        # Acceleration contribution (Panic bursts)
        accel_risk = min(1.0, accel / 2.0)
        visual_score += accel_risk * 0.3
        
        # B. Audio Component
        # Audio acts as context.
        # If Audio is RISING significantly, it amplifies visual threat.
        
        # C. Early Warning Detection (Trends)
        is_speed_rising = speed_slope > 0.05
        is_audio_rising = audio_slope > 0.5 # 0.5dB gain per frame is fast
        
        warning_signal = False
        
        # PREDICTIVE LOGIC:
        if is_speed_rising and is_audio_rising:
            # Both rising: Strong Early Warning
            threat_level = 0.6 # Warning Level
            warning_signal = True
            status_label = "early_warning"
            
        elif is_speed_rising and density_factor > 0.5:
             # Fast gathering in dense crowd
             threat_level = 0.5
             warning_signal = True
        
        # INCIDENT LOGIC (Current State):
        if audio_risk > 0.8: # Scream
            # If confirmed by even mild movement -> THREAT
            if visual_score > 0.2:
                threat_level = max(threat_level, 0.85)
                status_label = "critical"
            else:
                threat_level = max(threat_level, 0.5) # Audio only = Suspicious
                
        if visual_score > 0.7: # High chaotic movement
             threat_level = max(threat_level, 0.8)
             status_label = "critical"
        
        # Final Clamping & Hysteresis could go here
        
        # Map float to String Risk
        if threat_level >= 0.8:
            risk_str = "THREAT"
        elif threat_level >= 0.5:
            risk_str = "WARNING"
        elif warning_signal:
            risk_str = "WARNING"
        else:
            risk_str = "SAFE"
            
        return density, risk_str, float(threat_level), float(visual_score)
