# CrowdLumen Audio Intelligence Module

## Overview
A standalone, professional audio surveillance dashboard designed for the CrowdLumen project. This system monitors real-time audio input, detects anomalies (screams, explosions, panic), and displays threat levels on a matte-black professional UI.

## Features
- **Real-time Audio Capture**: Supports system microphones.
- **Threat Detection**:
    - **Rule-Based**: Thresholds for RMS energy (Volume) and Zero-Crossing Rate (Pitch/Chaos).
    - **Statistical**: Detects sudden spikes relative to background noise.
    - **Pattern**: Identifies specific "Panic" signatures (High Volume + High Frequency).
- **Dashboard**:
    - Streamlit-based web interface.
    - Live Waveform visualization.
    - Live Status (NORMAL / WARNING / CRITICAL).
    - Explanation/Reasoning for alerts.

## Installation

1. Ensure Python 3.9+ is installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *Note: On Windows, you might need to install PyAudio binary wheels manually if pip fails. Usually `pip install pipwin && pipwin install pyaudio` captures it, or just standard pip.*

## Usage

1. Navigate to the directory:
   ```bash
   cd e:\CrowdLumen\Audio_Intelligence
   ```
2. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```
3. The dashboard will open in your browser (usually `http://localhost:8501`).

## Module Structure
- `app.py`: Main Streamlit dashboard script.
- `audio_processor.py`: Backend logic for audio capture, feature extraction, and threat classification.
- `requirements.txt`: Python dependencies.

## Customization
- **Thresholds**: Adjust `RMS_WARNING` or thresholds in `audio_processor.py`.
- **Devices**: Select input device from the Sidebar in the dashboard.
