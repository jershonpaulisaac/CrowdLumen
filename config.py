
# Auto-generated Config
CAMERA_INDEX = 0


# Camera Settings
FRAME_WIDTH = 640
FRAME_HEIGHT = 640
FRAME_SKIP_INTERVAL = 3 # Only run AI every Nth frame (1 = every frame, 3 = every 3rd frame)

# Detection
YOLO_MODEL_NAME = "yolov8n-pose.pt" # Pose model for behavior
CONFIDENCE_THRESHOLD = 0.3
CLASS_ID_PERSON = 0



# Perspective & Scale (New in Phase 6)
PERSPECTIVE_FACTOR = 2.5 # Objects at top move 2.5x "faster" logically to compensate for depth
MASSIVE_COUNT_THRESHOLD = 50 # If count > 50, assume density saturation

# Analytics
MONITORED_AREA_SQ_METERS = 20.0
HISTORY_LENGTH = 30 # Frames for track history

# Behavior
SPEED_WALK_MAX = 5.0 # Pixels per frame (Uncorrected)
SPEED_RUN_MIN = 12.0
SPEED_STAND = 1.5
CHAOS_THRESHOLD = 1.5 # Entropy level

# Risk Weights (Must sum to ~1.0)
WEIGHT_DENSITY = 0.4
WEIGHT_CHAOS = 0.3
WEIGHT_SPEED = 0.3

# Thresholds for Threat Score (0-1.2)
THREAT_SCORES = {
    "LOW": 0.3,
    "MEDIUM": 0.5,
    "HIGH": 0.7,
    "CRITICAL": 0.85
}

# Crowd Count Thresholds
RISK_THRESHOLDS = {
    "LOW": 5,
    "MEDIUM": 15,
    "HIGH": 30
}

# Privacy
PRIVACY_BLUR = True


