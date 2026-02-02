# CrowdLumen Deployment Guide

This guide explains how to deploy the CrowdLumen crowd monitoring system on an Edge device (Raspberry Pi or Orange Pi).

## Hardware Connections
Connect your LEDs and Buzzer to the GPIO pins defined in `config.py` (BCM numbering by default):
*   **Red LED**: Pin 17
*   **Yellow/Green LED**: Pin 27
*   **Safe API/Green**: Pin 22
*   **Buzzer**: Pin 18
*   **GND**: Connect all component grounds to a GND pin on the Pi.

## Installation Steps
1.  **Clone/Copy Code**: Transfer all python files to the Pi.
2.  **Install Dependencies**:
    ```bash
    sudo apt-get update
    sudo apt-get install python3-pip python3-opencv
    pip3 install ultralytics flask RPi.GPIO
    ```
    *Note: Orange Pi users might need `OPi.GPIO` or a compatible library. You may need to adjust `hardware_controller.py` imports for Orange Pi.*

3.  **Connect Camera**: Ensure your USB webcam or Pi Camera is connected. Verify with `libcamera-hello` or `ls /dev/video*`.

4.  **Run**:
    ```bash
    python3 main.py
    ```

## Performance Tuning
If the FPS is too low on the Pi:
1.  Open `config.py`.
2.  Ensure `YOLO_MODEL_NAME = 'yolov8n.pt'` (Nano model).
3.  Reduce resolution: `FRAME_WIDTH = 320`, `FRAME_HEIGHT = 240`.
4.  In `vision_engine.py`, you can increase `conf` threshold or skip frames (only process every nth frame).
