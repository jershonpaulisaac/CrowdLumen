from flask import Flask, render_template, Response, jsonify, request
from engine import VisualEngine
import threading

app = Flask(__name__)
engine = None

def start_engine():
    global engine
    engine = VisualEngine(camera_index=0)
    engine.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(engine.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/metrics')
def metrics():
    if engine:
        return jsonify(engine.get_metrics())
    return jsonify({"error": "Engine not running"}), 500

@app.route('/api/camera', methods=['POST'])
def set_camera():
    idx = request.json.get('index', 0)
    if engine:
        engine.set_camera(idx)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 500

if __name__ == '__main__':
    # Start engine in background
    threading.Thread(target=start_engine, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
