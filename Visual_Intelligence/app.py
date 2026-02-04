from flask import Flask, render_template, Response, jsonify, request
from camera_system import CameraSystem
import threading
import os

app = Flask(__name__)

# Global Camera System
camera_system = None

def get_camera():
    global camera_system
    if camera_system is None:
        camera_system = CameraSystem()
    return camera_system

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    cam = get_camera()
    return Response(cam.get_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    cam = get_camera()
    return jsonify(cam.status_data)

@app.route('/switch_camera', methods=['POST'])
def switch_camera():
    data = request.json
    cam_index = data.get('index', 0)
    cam = get_camera()
    cam.open_camera(int(cam_index))
    return jsonify({"success": True, "current_index": cam_index})

if __name__ == '__main__':
    # Ensure templates folder exists
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static/css'):
        os.makedirs('static/css')
    if not os.path.exists('static/js'):
        os.makedirs('static/js')
        
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
