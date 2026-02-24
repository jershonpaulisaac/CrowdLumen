# CrowdLumen Safety & Security | Full Project Report

## 1. Project Overview
**CrowdLumen Safety & Security** is an advanced Industrial IoT solution designed for real-time occupancy monitoring and emergency management across multiple venues. The system uses a combination of RFID/NFC technology, a centralized Python backend, and a premium web-based dashboard to ensure personnel safety and site security.

---

## 2. Technical Stack

### **Hardware**
- **Microcontroller**: ESP32 (WROOM-32)
- **Sensors**: 2x MFRC522 RFID/NFC Readers (Entry & Exit)
- **Feedback**: Active Buzzer, WS2812B / Standard LEDs (Act G/R, Sys G/R)
- **Communication**: 2.4GHz WiFi (REST API over HTTP)

### **Backend (Software)**
- **Language**: Python 3.x
- **Framework**: Flask (with Flask-CORS)
- **Database**: SQLite (for User Identity Mapping)
- **State Management**: In-memory global state for multi-venue real-time counts.

### **Frontend (Dashboard)**
- **Core**: HTML5, Vanilla CSS3 (Custom Glassmorphism theme)
- **Typography**: Inter (Google Fonts)
- **Visualization**: Chart.js (Line trends and Doughnut gauges)
- **Real-time**: AJAX Polling (1.5s interval)

---

## 3. System Architecture & Working

### **A. Firmware Logic (ESP32)**
The firmware acts as the "Edge Device." It handles hardware interrupts from two RFID readers.
- **Entry Reader**: Taps are sent to the backend as `type: entry`.
- **Exit Reader**: Taps are sent to the backend as `type: exit`.
- **Feedback Loop**: After every tap, the device waits for a response from the server.
    - `allowed`: Green LED flash + Short beep.
    - `denied`: Red LED flash + Multi-beep.
- **Background Checks**: Every 2 seconds, the device polls `/hw_status` to check for global alarms (Evacuation or Over-Capacity).

### **B. Backend Logic (Flask API)**
The backend is the "Brain" of the system.
- **Multi-Venue Management**: Supports multiple zones (e.g., Main Hall, VIP Lounge) with independent capacity limits.
- **Identity Resolution**: Maps incoming RFID UIDs to human-readable names using the SQLite database. If a tag is unknown, it defaults to `Guest [UID]`.
- **Safety Overlays**: 
    - **Over-Capacity**: Detects when `count > limit` and triggers a warning state.
    - **Evacuation Protocol**: Tracks "Danger Zones" (people inside) vs "Muster Points" (people safe).

### **C. Command Dashboard (Frontend)**
A professional UI for security officers.
- **Main View**: Dashboard showing current occupancy, gauges, and live trend charts.
- **Venue Picker**: Sidelist to switch between different monitored zones.
- **Management Drawer**: Allows changing venue names, setting capacity limits, or resetting counts.
- **Emergency Protocol**: A high-contrast, strobe-red interface with real-time "Missing Personnel" tracking.

---

## 4. Key Features

1.  **Dual-Reader Occupancy**: Precise entry/exit tracking using separate readers for directional accuracy.
2.  **Over-Capacity Alarm**: 
    - **Visual**: Dashboard banner with a "Silence" option.
    - **Physical**: ESP32 triggers a repeated 1-second pulse beep.
3.  **Emergency Evacuation**: 
    - One-click trigger from the dashboard.
    - Triggers a continuous strobe buzzer on all hardware.
    - Live list of "Missing" personnel (those who haven't tapped "Exit" yet).
4.  **Live Activity Logs**: Real-time toast notifications for every tap, including user names and timestamps.

---

## 5. System Workflow

1.  **Detection**: Personnel taps an RFID/NFC tag on the **Entry Reader**.
2.  **Request**: ESP32 sends UID and Reader Info to `POST /api/tap`.
3.  **Processing**: 
    - Backend looks up name in `database.db`.
    - Updates `VENUES[current_id].count` and adds UID to the `occupants` set.
    - Logs the event in the history.
4.  **Feedback**: Server returns JSON response; ESP32 flashes **Green LED**.
5.  **Sync**: The web dashboard (polling every 1.5s) updates the **Gauge Chart** and adds a **Live Toast**.
6.  **Alerting**: If the limit is 10 and the new count is 11:
    - Dashboard shows **⚠️ OVER CAPACITY**.
    - ESP32 starts a pulsing alarm.
7.  **Emergency**: Security triggers "Evacuation." 
    - Hardware enters **Continuous Alarm Mode**.
    - Dashboard moves to the **Evacuation Page**, listing all UIDs currently inside.

---

## 6. Directory Structure
```
/safety_project_v2
├── /firmware
│   ├── platformio.ini      # Project config
│   └── src/main.cpp        # Dual RFID & Alarm Logic
├── /backend
│   ├── app.py              # Flask Server & Logic
│   ├── database.db         # User Database
│   └── add_user.py         # Utility to register tags
└── /frontend
    ├── index.html          # Main Monitoring Dashboard
    ├── evacuation.html     # Emergency Protocol Page
    └── style.css           # Premium Glassmorphism UI
```
