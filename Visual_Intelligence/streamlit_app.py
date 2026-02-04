import streamlit as st
import cv2
import numpy as np
import time
from camera_system import CameraSystem

# --- Page Configuration ---
st.set_page_config(
    page_title="CrowdLumen | Visual Intelligence",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS / Theme Injection ---
st.markdown("""
    <style>
        /* General Background */
        .stApp {
            background-color: #0e1117;
            color: #ffffff;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #161b22;
        }
        
        /* Metric Cards */
        div[data-testid="metric-container"] {
            background-color: #21262d;
            border: 1px solid #30363d;
            padding: 10px 15px;
            border-radius: 10px;
            color: #ffffff;
        }
        
        /* Headers */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            color: #ffffff !important;
        }
        
        /* Custom Threat Indicator */
        .threat-box {
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 20px;
            font-weight: bold;
            border: 1px solid rgba(255,255,255,0.1);
        }
        
        .reason-text {
            color: #8b949e;
            font-size: 14px;
            margin-top: 10px;
        }

        /* Video Container */
        .video-container {
            border: 2px solid #30363d;
            border-radius: 15px;
            overflow: hidden;
        }
    </style>
""", unsafe_allow_html=True)

# --- Session State ---
if 'camera_system' not in st.session_state:
    st.session_state.camera_system = CameraSystem()
    st.session_state.run_loop = True

cam = st.session_state.camera_system

# --- Sidebar ---
with st.sidebar:
    st.title("CrowdLumen")
    st.markdown("### Visual Intelligence Unit")
    st.divider()
    
    # Camera Control
    st.subheader("Video Source")
    cam_options = ["Camera 0 (Laptop)", "Camera 1 (USB)"]
    selected_cam = st.selectbox("Select Input", cam_options, index=cam.camera_index)
    
    # Handle Switching
    desired_index = 0 if "Camera 0" in selected_cam else 1
    if desired_index != cam.camera_index:
        cam.open_camera(desired_index)
        st.rerun()

    # Confidence Control (User "Training" via Sensitivity)
    st.subheader("AI Sensitivity")
    conf_val = st.slider("Detection Confidence", 0.1, 0.9, cam.detector.confidence, 0.05)
    if conf_val != cam.detector.confidence:
        cam.detector.confidence = conf_val
        cam.detector.model.conf = conf_val # Update model config if accessible directly or just used in predict

    if st.button("Reload System Logic", use_container_width=True):
        st.cache_resource.clear()
        if 'camera_system' in st.session_state:
            del st.session_state['camera_system']
        st.rerun()

    st.divider()
    
    # Threat Display (Sidebar Version)
    st.subheader("Current Threat Level")
    threat = cam.status_data["threat_level"]
    t_color = cam.status_data["threat_color"]
    
    # Map var css to actual hex for python usage if needed, or inline style
    color_map = {
        "var(--status-normal)": "#238636", # Green
        "var(--status-warning)": "#dbab09", # Yellow
        "var(--status-critical)": "#da3633"  # Red
    }
    hex_color = color_map.get(t_color, "#238636")
    
    st.markdown(f"""
        <div class="threat-box" style="background-color: {hex_color}20; border-color: {hex_color}; color: {hex_color}; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 24px; letter-spacing: 2px;">{threat}</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Reason
    st.markdown(f"**Reasoning:**")
    st.info(cam.status_data["reason"])
    
    st.divider()
    st.markdown('<div style="text-align:center; color:#444; font-size:12px;">v3.1 Professional</div>', unsafe_allow_html=True)

# --- Main Content ---
col1, col2 = st.columns([0.7, 0.3]) # Adjust ratio for professional look

with col1:
    st.subheader("Live Monitoring Feed")
    video_placeholder = st.empty()

with col2:
    st.subheader("Real-Time Metrics")
    
    # Metric Layout
    m1 = st.container()
    
    with m1:
        count_placeholder = st.empty()
    
    st.markdown("---")
        
    with m1:
        chaos_placeholder = st.empty()
        chaos_bar = st.progress(0)
    
    st.markdown("### Chaos Trends")
    chart_placeholder = st.empty()


# --- Video Loop ---
try:
    while True:
        frame, status = cam.read_processed_frame()
        
        if frame is not None:
            # Update Video
            video_placeholder.image(frame, channels="RGB", use_container_width=True)
            
            # Update Metrics
            count_placeholder.metric("Person Count", status["person_count"])
            
            c_val = status["chaos_metric"]
            chaos_placeholder.metric("Chaos / Flux", f"{c_val:.1f}")
            chaos_bar.progress(min(int(c_val), 100))
            
            # Update Chart
            if "history" in status:
                chart_placeholder.area_chart(status["history"], height=150)
                
        else:
            video_placeholder.error("No Video Signal. Check Camera.")
            time.sleep(1)

        time.sleep(0.01) # Faster loop, threaded camera handles FPS

except Exception as e:
    st.error(f"An error occurred: {e}")
