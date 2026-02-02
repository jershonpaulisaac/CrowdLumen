import os

# System Configuration
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FPS = 30
PRIVACY_BLUR = True # Blur faces

# Detection Configuration
YOLO_MODEL_NAME = 'yolov8n-pose.pt'
CONFIDENCE_THRESHOLD = 0.4
CLASS_ID_PERSON = 0

# Analytics Area
MONITORED_AREA_SQ_METERS = 20.0 

# Thresholds (Baseline - overrides by Context)
RISK_THRESHOLDS = {
    'MEDIUM': 5,
    'HIGH': 10
}

# Behavior Configuration
HISTORY_LENGTH = 30
CHAOS_THRESHOLD = 1.5

# Action Recognition Thresholds (Pixels/Frame)
# Note: These need tuning based on resolution/fps
SPEED_STAND = 1.0  # < 1.0 is Stationary/Standing
SPEED_WALK_MAX = 5.0 # 1.0 to 5.0 is Walking
# > 5.0 is Running (Subject to Context)

# Weights
WEIGHT_DENSITY = 0.1
WEIGHT_CHAOS = 0.5
WEIGHT_SPEED = 0.4

# Threat Scores
THREAT_SCORES = {
    'MEDIUM': 0.4,
    'HIGH': 0.6,
    'CRITICAL': 0.8
}

# Hardware
RED_LED_PIN = 17
YELLOW_LED_PIN = 27
GREEN_LED_PIN = 22
BUZZER_PIN = 18
SIMULATE_HARDWARE = False
