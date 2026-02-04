# CrowdLumen: Visual Intelligence Module (Streamlit Edition)

## Overview
The **Visual Intelligence Module** is a professional, standalone computer vision dashboard designed for real-time crowd monitoring. It uses **Streamlit** for a sleek, dark-themed UI and **YOLOv8** for state-of-the-art human detection.

## Features
- **Professional Dashboard**: Dark matte theme, rounded corners, clean metrics.
- **Improved Detection**: Uses YOLOv8 (COCO-trained) for robust multi-person detection.
- **Smart Threat Logic**: 
  - Ignores minor fidgeting/walking.
  - Detects **Crowd Surges** (Collective high-speed movement).
  - Detects **Overcrowding** (Density thresholds).
- **Dual Camera Support**: Live switching between Laptop and USB webcams.

## Requirements
- Python 3.9+
- Webcam

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Dashboard

Launch the Streamlit app:

```bash
streamlit run streamlit_app.py
```

The dashboard will open automatically in your browser (usually `http://localhost:8501`).

*Note: The first run will download the YOLO model weights (~6MB).*

## Controls
- **Sidebar**: Use the dropdown to switch cameras.
- **Main View**: Live video with threat analytics overlays.

---
**CrowdLumen Safety Systems**
