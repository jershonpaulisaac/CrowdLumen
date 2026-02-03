import unittest
import numpy as np
from collections import deque
from crowd_analytics import CrowdAnalyzer
from behavior_engine import BehaviorAnalyzer
import config

class TestCrowdSystem(unittest.TestCase):
    
    def setUp(self):
        self.analyzer = CrowdAnalyzer()
        self.behavior = BehaviorAnalyzer()
        
        # Mock Context
        self.context_general = {
            'description': 'PUBLIC_SQUARE',
            'density_weight': 0.5,
            'chaos_weight': 0.4,
            'speed_run_threshold': 15.0  # px/frame
        }

    # ==========================================
    # 1. LOGIC CORRECTNESS: Risk Calculation
    # ==========================================
    def test_risk_calculation_sparse_static(self):
        """Test Sparse, Static Crowd (Should be LOW logic)"""
        count = 5
        metrics = {
            "avg_speed": 1.0,
            "speed_anomaly": False,
            "chaos_score": 0.1,
            "active_count": 5
        }
        audio_stats = {"risk_score": 0.1, "db_level": 50, "anomaly": False}
        
        _, risk, score, _ = self.analyzer.analyze(count, metrics, self.context_general, audio_stats)
        print(f"\n[Sparse Static] Count: {count}, Risk: {risk}, Score: {score:.2f}")
        
        self.assertEqual(risk, 'LOW', "Sparse static crowd should be LOW risk")
        self.assertLess(score, 0.3, "Score should be very low")

    def test_risk_calculation_panic(self):
        """Test Panic Scenario (Run + Chaos + Scream)"""
        count = 50
        metrics = {
            "avg_speed": 20.0, # High speed
            "speed_anomaly": True,
            "chaos_score": 0.9, # High chaos
            "active_count": 50
        }
        audio_stats = {"risk_score": 1.0, "db_level": 100, "anomaly": True} # Scream
        
        _, risk, score, _ = self.analyzer.analyze(count, metrics, self.context_general, audio_stats)
        print(f"[Panic Scenario] Count: {count}, Risk: {risk}, Score: {score:.2f}")
        
        self.assertIn(risk, ['HIGH', 'CRITICAL'], "Panic metrics should trigger HIGH/CRITICAL")

    # ==========================================
    # 2. FAIL-SAFE BEHAVIOR: Audio Fusion
    # ==========================================
    def test_audio_alone_safety(self):
        """CRITICAL: Audio alone should NOT trigger CRITICAL if Visual is Calm"""
        count = 10
        metrics = {
            "avg_speed": 1.0, # Calm
            "speed_anomaly": False,
            "chaos_score": 0.1,
            "active_count": 10
        }
        # Simulate Train passing (High dB, High Risk Score audio)
        audio_stats = {"risk_score": 0.95, "db_level": 100, "anomaly": True}
        
        _, risk, score, _ = self.analyzer.analyze(count, metrics, self.context_general, audio_stats)
        print(f"[Audio Only] Visually Calm + Loud Audio -> Risk: {risk}, Score: {score:.2f}")
        
        self.assertNotEqual(risk, 'CRITICAL', "Audio alone MUST NOT trigger CRITICAL (False Positive Prevention)")
        self.assertTrue(risk in ['MEDIUM', 'HIGH'], "Should alert but not panic")

    # ==========================================
    # 3. EDGE CASE: Massive Crowd Saturation
    # ==========================================
    def test_massive_crowd_saturation(self):
        """AUDIT FINDING: Check if system handles 10,000 count input correctly"""
        # Note: YOLO usually won't output 10,000, but if we feed it manually...
        count = 1000
        metrics = {"avg_speed": 0.5, "speed_anomaly": False, "chaos_score": 0.2, "active_count": 1000}
        audio_stats = {"risk_score": 0.2, "db_level": 60, "anomaly": False}
        
        _, risk, score, _ = self.analyzer.analyze(count, metrics, self.context_general, audio_stats)
        print(f"[Massive Input] Count: {count}, Risk: {risk}, Score: {score:.2f}")
        
        # With current area=20m^2 (hardcoded), 1000 people = 50 people/m^2 which is physically impossible
        # The system currently maxes out density score.
        self.assertTrue(score > 0.8, "Massive density should trigger high threat even if static")

    # ==========================================
    # 4. BEHAVIOR LOGIC: Perspective Issue
    # ==========================================
    def test_perspective_speed_issue(self):
        """AUDIT FINDING: Pixel speed is not depth-aware"""
        # We need at least 5 points for speed calc
        # Person A (Foreground - y=500): Moves 10px per frame -> 40px total
        self.behavior.track_history[1] = deque([
            (100, 500), (100, 500), (100, 500), (100, 490), (100, 480) # Very small move? No, let's do big move
        ], maxlen=30)
        # Reset to clear old
        
        # Setup Track A (close/bottom, y~480): Moves 10px/frame. Phys Speed = Normal
        # Scale factor at y=480 is 1.0. Speed ~ 10.
        pts_a = [(100, 480 - i*10) for i in range(5)] # (100,480), (100,470)...
        self.behavior.track_history[1] = deque(pts_a, maxlen=30)
        self.behavior.track_states[1] = "Standing"
        
        # Setup Track B (far/top, y~0): Moves 2px/frame. 
        # Physical Speed should be similar if Perspective Factor is ~5x.
        # Scale factor at y=0 is 1+2.5 = 3.5. Speed ~2 * 3.5 = 7.
        pts_b = [(100, 0 + i*2) for i in range(5)]
        self.behavior.track_history[2] = deque(pts_b, maxlen=30) 
        self.behavior.track_states[2] = "Standing"
        
        metrics = self.behavior.analyze_behavior(self.context_general)
        
        print(f"[Perspective] Avg Corrected Speed: {metrics['avg_speed']:.2f}")
        
        # We just want to ensure it runs and produces non-zero speed
        self.assertGreater(metrics['avg_speed'], 0.0)

if __name__ == '__main__':
    unittest.main()
