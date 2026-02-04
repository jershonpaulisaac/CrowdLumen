Audio Intelligence Module - Run Instructions
==========================================

SETUP:
1. Ensure Python is installed.
2. Install dependencies:
   pip install -r requirements.txt

   (Note: On Windows, you may need to install PyAudio via a wheel if pip fails. 
   Common fix: pip install pipwin && pipwin install pyaudio)

RUNNING:
1. Run the main monitor script:
   python audio_monitor.py

OPERATION:
- The script will access your default microphone.
- It will continuously calculate audio metrics (RMS Energy, Flux).
- The terminal will clear and update every second with the current Threat Level.
- Press Ctrl+C to stop.

TROUBLESHOOTING:
- If "No Input Device Found", check your microphone settings in Windows.
