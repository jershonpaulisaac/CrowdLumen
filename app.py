from flask import Flask, render_template, Response, jsonify, request
import cv2
import time
import threading
import config
from vision_engine import PersonDetector
from crowd_analytics import CrowdAnalyzer
from hardware_controller import AlertSystem
from behavior_engine import BehaviorAnalyzer
from context_engine import ContextEngine
from reliability_engine import ReliabilityEngine
from explanation_engine import ExplanationEngine
from audio_engine import AudioMonitor

app = Flask(__name__)

# Global State
output_frame = None
lock = threading.Lock()
current_stats = {
    "count": 0,
    "active_count": 0,
    "risk": "LOW",
    "threat_score": 0.0,
    "data_reliability": 100.0,
    "explanation": "Initializing...",
    "action_counts": {},
    "context": "GENERAL",
    "fps": 0,
    "audio": { 
        "db_level": 40.0, 
        "status": "Calm", 
        "anomaly": False, 
        "sim_mode": "NORMAL",
        "bands": [0,0,0,0,0],
        "source": "Init"
    }
}
requested_camera_index = config.CAMERA_INDEX

# Initialize Modules
detector = None
analyzer = None
alert_system = None
behavior_engine = None
context_engine = None
reliability_engine = None
explanation_engine = None
audio_monitor = None

def init_system():
    global detector, analyzer, alert_system, behavior_engine
    global context_engine, reliability_engine, explanation_engine, audio_monitor
    
    if detector is None:
        detector = PersonDetector()
        behavior_engine = BehaviorAnalyzer()
        analyzer = CrowdAnalyzer()
        alert_system = AlertSystem()
        context_engine = ContextEngine()
        reliability_engine = ReliabilityEngine()
        explanation_engine = ExplanationEngine()
        
        # Audio - Real Mic Priority
        audio_monitor = AudioMonitor(simulate=False)
        audio_monitor.start()

def camera_loop():
    global output_frame, current_stats, requested_camera_index
    init_system()
    
    current_idx = requested_camera_index
    cap = cv2.VideoCapture(current_idx)
    
    prev_time = time.time()
    
    while True:
        if requested_camera_index != current_idx:
            cap.release()
            current_idx = requested_camera_index
            cap = cv2.VideoCapture(current_idx)
            
        ret, frame = cap.read()
        context_settings = context_engine.get_settings()
        
        # 1. Always Get Audio Data (Decoupled from Camera)
        audio_stats = audio_monitor.get_stats()
        
        # Defaults for vision if camera fails
        count = current_stats["count"]
        active_count = current_stats.get("active_count", 0)
        risk = "LOW"
        threat_score = 0.0
        reliability = 0.0
        explanation = "Camera Offline. Audio Active."
        chaos = 0.0
        speed = 0.0
        fps = 0.0
        action_counts = current_stats.get("action_counts", {})
        
        if ret and frame is not None:
             # 2. Vision
            try:
                count, annotated_frame, tracks, states = detector.detect(frame)
                
                # 3. Behavior
                behavior_engine.update_tracks(tracks, states)
                behavior_metrics = behavior_engine.analyze_behavior(context_settings)
                active_count = behavior_metrics['active_count']
                action_counts = behavior_metrics['action_counts']
                chaos = behavior_metrics['chaos_score']
                speed = behavior_metrics['avg_speed']
                
                # 4. Analytics
                density, risk, threat_score, visual_score = analyzer.analyze(
                    count, behavior_metrics, context_settings, audio_stats
                )
                
                # 5. Reliability / Explanation
                reliability = reliability_engine.calculate_reliability(tracks, count)
                explanation = explanation_engine.explain(
                    risk, threat_score, 
                    max(action_counts, key=action_counts.get, default="None"),
                    context_settings['description'],
                    behavior_metrics
                )
                
                # Viz Actions
                if tracks.id is not None:
                     track_ids = tracks.id.cpu().numpy().astype(int)
                     boxes = tracks.xyxy.cpu().numpy()
                     for i, tid in enumerate(track_ids):
                         action = behavior_engine.get_track_action(tid, context_settings)
                         x1, y1 = int(boxes[i][0]), int(boxes[i][1])
                         cv2.putText(annotated_frame, action, (x1, y1 + 15), 
                                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                output_frame = annotated_frame.copy()
            except Exception as e:
                print(f"Error in Vision Pipeline: {e}")
        else:
            # Camera Fail
            time.sleep(0.05)
            # If we have previous stats, use them but mark reliability 0
            explanation = "Camera FAILED. Audio Only Mode."
            
        # Audio Explanation Overlay
        if audio_stats['anomaly']:
            explanation += f" [Audio Alert: {audio_stats['status']}]"

        # 6. Alert (Trigger even if just audio is high? No, explicit rule says Audio alone cant trigger Critical)
        # But we pass the calculated risk.
        alert_system.trigger_alert(risk)
        
        curr_time = time.time()
        fps = 1 / (curr_time - prev_time) if (curr_time - prev_time) > 0 else 0
        prev_time = curr_time
        
        with lock:
            current_stats = {
                "count": count,
                "active_count": active_count,
                "risk": risk,
                "threat_score": threat_score,
                "data_reliability": reliability,
                "explanation": explanation,
                "action_counts": action_counts,
                "context": context_engine.current_context,
                "fps": round(fps, 1),
                "chaos": chaos,
                "speed": speed,
                "audio": audio_stats 
            }
            
    cap.release()
    audio_monitor.stop()

def generate():
    global output_frame, lock
    while True:
        with lock:
            if output_frame is None:
                time.sleep(0.1)
                continue
            (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
            if not flag: continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')
        time.sleep(0.05)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    return Response(generate(), mimetype = "multipart/x-mixed-replace; boundary=frame")

@app.route("/api/stats")
def stats():
    with lock:
        return jsonify(current_stats)

@app.route("/api/set_context/<context_name>")
def set_context(context_name):
    if context_engine: context_engine.set_context(context_name)
    return jsonify({"status": "ok"})

@app.route("/api/switch_camera/<int:index>")
def switch_camera(index):
    global requested_camera_index
    requested_camera_index = index
    return jsonify({"status": "ok"})
    
@app.route("/api/audio_sim/<mode>")
def audio_sim(mode):
    if audio_monitor: audio_monitor.set_simulation_mode(mode_map(mode))
    return jsonify({"status": "ok"}) 
    
def mode_map(m):
    if m == 'l': return 'LOUD'
    if m == 'p': return 'PANIC'
    return 'NORMAL'

def start_app():
    t = threading.Thread(target=camera_loop)
    t.daemon = True
    t.start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    start_app()
