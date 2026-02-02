import config

class CrowdAnalyzer:
    def __init__(self):
        self.area = config.MONITORED_AREA_SQ_METERS
        
    def analyze(self, count, behavior_metrics, context_settings=None, audio_stats=None):
        """
        Analyze crowd risk with Multi-Modal Fusion (Visual + Audio + Context).
        """
        # Load Context
        if context_settings:
            w_chaos = context_settings['chaos_weight']
            w_density = context_settings['density_weight']
            audio_limit = context_settings.get('audio_threshold', 80.0)
        else:
            w_chaos = config.WEIGHT_CHAOS
            w_density = config.WEIGHT_DENSITY
            audio_limit = 80.0
            
        w_speed = config.WEIGHT_SPEED

        # 1. Visual Base Score (Density + Behavior)
        density = count / self.area if self.area > 0 else 0
        norm_density = min(count / config.RISK_THRESHOLDS['HIGH'], 1.2)
        
        chaos_score = 0
        speed_score = 0
        
        if behavior_metrics:
            raw_chaos = behavior_metrics.get('chaos_score', 0)
            chaos_score = min(raw_chaos / config.CHAOS_THRESHOLD, 1.2)
            
            if behavior_metrics.get('speed_anomaly'):
                speed_score = 1.0
            else:
                avg_spd = behavior_metrics.get('avg_speed', 0)
                base_info = context_settings['speed_run_threshold'] if context_settings else config.SPEED_WALK_MAX
                speed_score = min(avg_spd / base_info, 1.2)

        visual_threat = (
            (norm_density * w_density) +
            (chaos_score * w_chaos) +
            (speed_score * w_speed)
        )
        
        # 2. Audio Fusion Logic
        # Audio acts as a "Confidence Booster" or "Validator"
        final_threat = visual_threat
        audio_risk = 0.0
        
        if audio_stats:
            audio_risk = audio_stats.get('risk_score', 0)
            db = audio_stats.get('db_level', 0)
            
            # RULE 1: High Audio + High Visual = Boost
            if audio_risk > 0.7:
                final_threat *= 1.3 # 30% Boost
                
            # RULE 2: Panic Audio (Screaming) forces at least HIGH if Visual is non-zero
            if audio_risk > 0.9 and visual_threat > 0.2:
                final_threat = max(final_threat, config.THREAT_SCORES['HIGH'])
                
            # RULE 3: Calm Audio dampens edge-case False Visuals
            if audio_risk < 0.2 and visual_threat < 0.5:
                final_threat *= 0.9 # Slight reduction
                
            # RULE 4: Audio alone CANNOT trigger Critical (as requested)
            if visual_threat < config.THREAT_SCORES['MEDIUM'] and audio_risk > 0.8:
                # High sound but no visual crowd chaos -> Maybe firework/train
                # Cap at MEDIUM risk
                final_threat = min(final_threat, config.THREAT_SCORES['MEDIUM'] - 0.01)

        # 3. Level Determination
        if final_threat >= config.THREAT_SCORES['CRITICAL']:
            risk = 'CRITICAL'
        elif final_threat >= config.THREAT_SCORES['HIGH']:
            risk = 'HIGH'
        elif final_threat >= config.THREAT_SCORES['MEDIUM']:
            risk = 'MEDIUM'
        else:
            risk = 'LOW'
            
        return density, risk, final_threat, visual_threat # Return final and visual-only for detailed stats
