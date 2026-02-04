Visual Intelligence Module - Run Instructions
===========================================

SETUP:
1. Ensure Python is installed.
2. Install dependencies:
   pip install -r requirements.txt

RUNNING:
1. Run the main monitor script:
   python visual_monitor.py

OPERATION:
- The script will access your default webcam.
- It will open a video window showing the live feed with an overlay.
- Motion analysis is performed in real-time.
- Status (NORMAL / WARNING / CRITICAL) is displayed on top of the video and in the terminal.
- Press 'q' or 'ESC' to exit the video window.

TROUBLESHOOTING:
- If "Video source not found", ensure your webcam is plugged in and allowed for Python usage.
