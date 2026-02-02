import numpy as np

class ReliabilityEngine:
    def __init__(self):
        pass

    def calculate_reliability(self, tracks, detections_count, frame_brightness=None):
        """
        Calculate a confidence score (0-100) for the current analysis.
        Factors:
        - Track stability (Are IDs flickering?)
        - Occlusion level (Box overlaps)
        - Detection confidence (YOLO score) - Not passed here but could be.
        """
        score = 100.0
        
        # 1. Low count usually means high reliability (easy to track)
        # High count -> Occlusion risk
        if detections_count > 15:
            score -= 10
        if detections_count > 30:
            score -= 20
            
        # 2. Track Health (If we have IDs)
        # For this prototype we assume tracks passed are valid.
        # Check if many small boxes? (Far away / Noise)
        
        # 3. Simple heuristic: If count is 0, reliability is High (unless pitch black)
        # If frame is too dark? (We'd need image stats)
        
        return max(0.0, min(100.0, score))
