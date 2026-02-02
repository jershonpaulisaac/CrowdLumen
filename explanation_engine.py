class ExplanationEngine:
    def __init__(self):
        pass

    def explain(self, risk_level, threat_score, top_action, context_desc, behavior_metrics):
        """
        Generate a human-readable explanation.
        """
        if risk_level == 'LOW':
            return "Normal behavior. " + context_desc
            
        reasons = []
        
        # Speed
        if behavior_metrics.get('speed_anomaly'):
            reasons.append("Sudden Rushing detected")
        elif top_action == 'Running':
            reasons.append("People are Running")
            
        # Chaos
        if behavior_metrics.get('chaos_score', 0) > 1.2: # Threshold from config roughly
            reasons.append("Disorganized/Chaotic movement")
            
        # Density
        # implied if threat is high but no behavior?
        
        if not reasons:
            reasons.append("High Crowd Density")
            
        reason_str = ", ".join(reasons)
        return f"Alert: {reason_str}. ({context_desc})"
