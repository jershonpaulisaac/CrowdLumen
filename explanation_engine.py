class ExplanationEngine:
    def __init__(self):
        pass

    def explain(self, risk_level, threat_score, top_action, context_desc, behavior_metrics):
        """
        Generate a human-readable explanation for Predictive/Early Warning.
        """
        if risk_level == 'SAFE':
            return "Stable. " + context_desc
            
        reasons = []
        
        # 1. Predictive Trends (Early Warning)
        speed_slope = behavior_metrics.get('trend_slope', 0)
        if speed_slope > 0.1:
            reasons.append("Rising Movement Speed")
            
        # 2. Dynamics
        accel = behavior_metrics.get('avg_accel', 0)
        if accel > 2.0:
            reasons.append("Sudden Acceleration Detected")
            
        flux = behavior_metrics.get('flux_score', 0)
        if flux > 10.0:
            reasons.append("Chaotic Group Flux")
            
        # 3. Audio (Implied via risk logic, but let's check basic metric if available)
        # Note: behavior_metrics doesn't have audio slope directly unless we pass it.
        # But we can infer from Context if needed.
        
        # 4. Fallbacks
        if not reasons:
            if top_action == 'Running':
                 reasons.append("Running Detected")
            elif risk_level == 'THREAT':
                 reasons.append("High Threat Convergence")
            elif risk_level == 'WARNING':
                 reasons.append("Abnormal Pattern Warning")
            
        reason_str = ", ".join(reasons)
        prefix = "EARLY WARNING" if risk_level == 'WARNING' else "THREAT ALERT"
        
        return f"{prefix}: {reason_str}"
