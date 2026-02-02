class ContextEngine:
    """
    Manages the current ENVIRONMENTAL context and returns appropriate thresholds.
    Public Spaces Only.
    """
    PRESETS = {
        'RAILWAY_STATION': {
            'speed_run_threshold': 6.0, # Rushing for train is common
            'chaos_weight': 0.6,       # Chaos is bad near tracks
            'density_weight': 0.3,     # Platforms get dense
            'audio_threshold': 85.0,   # Trains are loud
            'description': "High Rush Expected. Audio tolerance high."
        },
        'PUBLIC_SQUARE': {
            'speed_run_threshold': 8.0, # Kids playing etc.
            'chaos_weight': 0.2,       # Chaos normal
            'density_weight': 0.1,     # Events
            'audio_threshold': 80.0,   # Street noise
            'description': "Relaxed rules. High density allowed."
        },
        'BUS_STAND': {
            'speed_run_threshold': 5.0, # Bus movement danger
            'chaos_weight': 0.8,       # High risk of accidents
            'density_weight': 0.4,
            'audio_threshold': 85.0,   # Horns/Engines
            'description': "Strict flow monitoring. Vehicle risk."
        },
        'GENERAL': {
            'speed_run_threshold': 5.0,
            'chaos_weight': 0.5,
            'density_weight': 0.2,
            'audio_threshold': 75.0,
            'description': "Standard public monitoring."
        }
    }

    def __init__(self):
        self.current_context = 'GENERAL'

    def set_context(self, context_name):
        if context_name.upper() in self.PRESETS:
            self.current_context = context_name.upper()
            return True
        return False

    def get_settings(self):
        return self.PRESETS[self.current_context]
