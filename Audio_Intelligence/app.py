import streamlit as st
import numpy as np
import time
import pandas as pd
from audio_processor import AudioProcessor

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="CrowdLumen Audio Intelligence",
    page_icon="🔊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        .stApp { background-color: #0E1117; color: #E0E0E0; }
        
        /* Metric Cards */
        div[data-testid="stMetric"] {
            background-color: #1A1C24;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #333;
        }
        
        /* Status Banner */
        .status-header {
            font-size: 20px;
            font-weight: bold;
            color: #888;
            margin-bottom: 5px;
        }
        .status-value {
            font-size: 48px;
            font-weight: 900;
            padding: 15px;
            border-radius: 12px;
            text-align: center;
            letter-spacing: 2px;
        }
        .status-NORMAL {
            background: rgba(14, 255, 100, 0.1);
            color: #0EFF64;
            border: 1px solid #0EFF64;
            box-shadow: 0 0 15px rgba(14, 255, 100, 0.2);
        }
        .status-WARNING {
            background: rgba(255, 170, 0, 0.1);
            color: #FFAA00;
            border: 1px solid #FFAA00;
            box-shadow: 0 0 15px rgba(255, 170, 0, 0.2);
        }
        .status-CRITICAL {
            background: rgba(255, 50, 50, 0.1);
            color: #FF3232;
            border: 1px solid #FF3232;
            box-shadow: 0 0 25px rgba(255, 50, 50, 0.4);
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0.4); }
            70% { box-shadow: 0 0 0 10px rgba(255, 50, 50, 0); }
            100% { box-shadow: 0 0 0 0 rgba(255, 50, 50, 0); }
        }
        
        .reason-box {
            font-family: 'Consolas', monospace;
            color: #BBB;
            margin-top: 10px;
            font-size: 14px;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# --- SINGLETON AUDIO PROCESSOR ---
@st.cache_resource
def get_audio_processor():
    """Returns a singleton instance of the AudioProcessor."""
    processor = AudioProcessor()
    # Auto-start with default settings (will be updated by sidebar)
    processor.start(input_gain=5.0) 
    return processor

processor = get_audio_processor()

# --- SIDEBAR CONTROL ---
with st.sidebar:
    st.title("CrowdLumen 🔊")
    st.markdown("### Audio Intelligence")
    
    # Device Selector
    devices = processor.get_devices()
    
    # Store selected device index in session state to persistent
    if "device_index" not in st.session_state:
        st.session_state.device_index = 0
        
    device_options = {d.split(':')[0]: d for d in devices}
    sorted_indices = sorted([int(k) for k in device_options.keys()])
    
    selected_idx = st.selectbox(
        "Input Device", 
        sorted_indices, 
        format_func=lambda i: device_options[str(i)],
        index=0 if 0 in sorted_indices else 0
    )
    
    # Gain Control
    gain = st.slider("Mic Sensitivity (Gain)", 1.0, 50.0, 5.0, help="Increase if waveform is flat")
    
    # Update processor if changed
    if selected_idx != st.session_state.device_index:
        processor.stop()
        processor.start(device_index=selected_idx, input_gain=gain)
        st.session_state.device_index = selected_idx
    else:
        # Just update gain
        processor.input_gain = gain

    st.divider()
    
    # Debug
    with st.expander("System Health"):
        st.write(f"Frames: {processor.frames_processed}")
        st.write(f"Buffer: {len(processor.audio_buffer)}")
        st.write(f"Gain: {processor.input_gain}x")
        if st.button("RESTART ENGINE", type="primary"):
            processor.stop()
            processor.start(device_index=selected_idx, input_gain=gain)
            st.rerun()

# --- MAIN LAYOUT ---
st.header("Audio Intelligence Dashboard")

# Top: Status
status_col, metrics_col = st.columns([1, 2])

with status_col:
    # Placeholder for Status
    status_placeholder = st.empty()

with metrics_col:
    # Placeholders for Metrics
    m1, m2, m3, m4 = st.columns(4)
    rm_metric = m1.empty()
    db_metric = m2.empty()
    zc_metric = m3.empty()
    fx_metric = m4.empty()

# Middle: Waveform
st.subheader("Live Audio Waveform")
chart_placeholder = st.empty()

# Bottom: Spectrogram / History (Optional, just use reason text for now)
reason_placeholder = st.empty()


# --- LIVE LOOP ---
# In Streamlit, a `while True` loop blocks the script but allows elements to update.
# This requires the user to NOT be interacting with other UI elements (buttons which trigger reruns).
# For a dashboard, this is standard behavior.

FPS = 10
FRAME_DELAY = 1.0 / FPS

if st.button("Stop Monitoring"):
    st.stop()

while True:
    # 1. Get Data
    wave, metrics = processor.get_data()
    
    # 2. Update Status
    status = metrics["status"]
    reason = metrics["reason"]
    
    status_html = f"""
    <div>
        <div class='status-header'>CURRENT STATUS</div>
        <div class='status-value status-{status}'>{status}</div>
        <div class='reason-box'>[{reason}]</div>
    </div>
    """
    status_placeholder.markdown(status_html, unsafe_allow_html=True)
    
    # 3. Update Metrics
    rm_metric.metric("RMS Energy", f"{metrics['rms']:.3f}")
    db_metric.metric("Intensity (dB)", f"{metrics['db']:.1f}")
    zc_metric.metric("Zero-Crossing", f"{metrics['zcr']:.3f}")
    fx_metric.metric("Spectral Flux", f"{metrics['flux']:.3f}")
    
    # 4. Update Waveform
    # Downsample for performance (N samples to ~500 points)
    if len(wave) > 0:
        # Take last N samples to show "Live" window
        display_wave = wave[-4096:] # Last 0.1s approx
        
        # Simple decimation for plotting speed
        decimated = display_wave[::8]
        
        # Use Area Chart for 'tech' look
        chart_data = pd.DataFrame(decimated, columns=["Amplitude"])
        chart_placeholder.area_chart(chart_data, height=300, color="#00ADB5")
    
    time.sleep(FRAME_DELAY)
