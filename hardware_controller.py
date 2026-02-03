class AlertSystem:
    def __init__(self):
        # print("[System] Hardware Controller: GPIO Removed per user request. Running in Software-Only Mode.")
        self.current_risk = None

    def trigger_alert(self, risk_level):
        """
        Virtual Alert Trigger.
        Just logs the alert level to the console since GPIO paths are removed.
        """
        if risk_level == self.current_risk:
            return # No change needed

        self.current_risk = risk_level
        
        # Visual feedback in console instead of Hardware LED
        # Silenced per user request
        # if risk_level == 'CRITICAL':
        #     print(f"!!! [VIRTUAL BUZZER/RED LED] CRITICAL ALERT TRIGGERED !!!")
        # elif risk_level == 'HIGH':
        #     print(f"!!! [VIRTUAL RED LED] HIGH RISK DETECTED !!!")
        # elif risk_level == 'MEDIUM':
        #     print(f"--- [VIRTUAL YELLOW LED] Medium Risk ---")
        # else:
        #     print(f"--- [VIRTUAL GREEN LED] System Normal ---")

    def cleanup(self):
        pass # Nothing to clean up
