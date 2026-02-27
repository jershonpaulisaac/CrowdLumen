CrowdLumen Safety & Security
Project Overview

CrowdLumen Safety & Security is an Industrial IoT solution for real-time occupancy monitoring and emergency management. It combines RFID/NFC tracking, a Python backend, and a web-based dashboard to ensure personnel safety and site security across multiple venues.

This system is ideal for monitoring halls, VIP zones, classrooms, or any controlled environment with safety-critical requirements.

Technical Stack
Hardware

Microcontroller: ESP32 (WROOM-32)

Sensors: 2x MFRC522 RFID/NFC Readers (Entry & Exit)

Feedback: Active buzzer, WS2812B / standard LEDs

Communication: WiFi (REST API over HTTP)

Backend (Software)

Language: Python 3.x

Framework: Flask + Flask-CORS

Database: SQLite for User Identity Mapping

State Management: In-memory for real-time multi-venue occupancy

Frontend (Dashboard)

Core: HTML5 + CSS3 (Custom Glassmorphism theme)

Typography: Inter (Google Fonts)

Visualization: Chart.js (Line trends and Doughnut gauges)

Real-time: AJAX polling every 1.5 seconds

System Architecture
Firmware (ESP32)

Handles hardware interrupts from dual RFID readers.

Entry Reader → sends type: entry to backend.

Exit Reader → sends type: exit to backend.

Feedback to user via LEDs and buzzer.

Polls /hw_status every 2 seconds to check global alerts.

Backend (Flask API)

Manages multi-venue occupancy with independent capacity limits.

Maps RFID UIDs to names; defaults to Guest [UID] if unknown.

Monitors safety overlays:

Over-capacity alerts

Evacuation tracking

Frontend Dashboard

Displays live occupancy, gauges, and trends.

Provides venue switching, capacity management, and reset functions.

Emergency interface highlights missing personnel and triggers alerts.

Key Features

Dual-Reader Occupancy: Accurate entry/exit tracking.

Over-Capacity Alarm:

Visual dashboard alert with silence option

Physical buzzer and LED pulse

Emergency Evacuation:

One-click dashboard trigger

Continuous alarm mode

Real-time missing personnel tracking

Live Activity Logs: Timestamped notifications for each tap

System Workflow

User taps RFID/NFC tag on Entry Reader.

ESP32 sends POST /api/tap with UID and reader info.

Backend updates venue count, occupants list, and logs event.

ESP32 receives response → flashes Green/Red LED accordingly.

Dashboard syncs every 1.5s → updates gauges and live logs.

Over-capacity detected → dashboard alert + buzzer pulse.

Evacuation mode → continuous alarms + list of people still inside.

Directory Structure
/safety_project_v2
├── /firmware
│   ├── platformio.ini      # Project configuration
│   └── src/main.cpp        # Dual RFID & alarm logic
├── /backend
│   ├── app.py              # Flask server & API
│   ├── database.db         # User identity database
│   └── add_user.py         # Utility to register RFID tags
└── /frontend
    ├── index.html          # Main monitoring dashboard
    ├── evacuation.html     # Emergency interface
    └── style.css           # Glassmorphism UI styling
Setup Instructions

Firmware: Upload /firmware/src/main.cpp to ESP32 using PlatformIO.

Backend:

Install Python dependencies:

pip install flask flask-cors

Run server:

python app.py

Frontend: Open /frontend/index.html in a browser (works locally).

Connect ESP32 to WiFi → server API endpoint for real-time sync.

Future Enhancements

Integrate video-based crowd counting and density analysis.

Add AI-based predictive alerts for crowd congestion or chaos.

Link with audio sensors for real-time panic detection.

Combine with RFID/NFC identity system for full hybrid monitoring.
