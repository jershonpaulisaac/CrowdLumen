import pyaudio
import numpy as np
import threading
import time
# import librosa - Removed to prevent threading/performance crashes in callback
from collections import deque

# --- CONFIGURATION ---
CHUNK = 4096 # Larger chunk for better freq resolution
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
BUFFER_SECONDS = 5
BUFFER_SECONDS = 5
HISTORY_LEN = 100
BUFFER_SECONDS = 5
HISTORY_LEN = 100
SMOOTHING_WINDOW = 3 # Reduced for faster response

class AudioProcessor:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.lock = threading.Lock()
        
        # Audio Buffer (Circular)
        # Store raw float data for processing
        self.buffer_size = int(RATE / CHUNK * BUFFER_SECONDS)
        self.audio_buffer = deque(maxlen=self.buffer_size)
        
        # Metrics History
        self.metrics_history = deque(maxlen=HISTORY_LEN)
        
        # State
        self.frames_processed = 0
        self.input_gain = 5.0 # Default gain boost
        
        # ML / Baseline State
        # We will maintain a 'normal' MFCC profile
        self.baseline_mfcc = None
        self.calibration_frames = 0
        
        # Results
        self.latest_metrics = {
            "rms": 0.0,
            "db": -90.0,
            "zcr": 0.0,
            "flux": 0.0,
            "threat_score": 0.0,
            "status": "NORMAL",
            "reason": "Initializing..."
        }
        
        # Metric buffering for smoothing
        self.metric_buffer = deque(maxlen=SMOOTHING_WINDOW)
        self.last_error = None

    def get_devices(self):
        """Return list of input devices."""
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        devices = []
        for i in range(0, numdevices):
            d_info = self.p.get_device_info_by_host_api_device_index(0, i)
            if d_info.get('maxInputChannels') > 0:
                devices.append(f"{i}: {d_info.get('name')}")
        return devices

    def start(self, device_index=None, input_gain=None):
        if input_gain is not None:
            self.input_gain = input_gain
            
        if self.running:
            return

        try:
            self.stream = self.p.open(format=FORMAT,
                                      channels=CHANNELS,
                                      rate=RATE,
                                      input=True,
                                      input_device_index=device_index,
                                      frames_per_buffer=CHUNK,
                                      stream_callback=self._audio_callback)
            self.stream.start_stream()
            self.running = True
            print(f"Audio started on device {device_index} with gain {self.input_gain}")
        except Exception as e:
            print(f"Error starting audio: {e}")
            self.latest_metrics["reason"] = f"Device Error: {str(e)}"
            self.latest_metrics["status"] = "CRITICAL"

    def stop(self):
        if self.stream:
            if self.stream.is_active():
                self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        self.running = False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        try:
            # 1. Convert Bytes to Int16
            audio_data_int = np.frombuffer(in_data, dtype=np.int16)
            
            # 2. Normalize to Float (-1.0 to 1.0)
            audio_data_float = audio_data_int / 32768.0
            
            # 3. Apply Gain
            audio_data_float = audio_data_float * self.input_gain
            audio_data_float = np.clip(audio_data_float, -1.0, 1.0)
            
            # 4. Remove DC Offset
            audio_data_float = audio_data_float - np.mean(audio_data_float)
            
            # 5. Thread-safe storage
            with self.lock:
                self.audio_buffer.append(audio_data_float)
                self.frames_processed += 1
            
            # 6. Compute Metrics Async (or sync here since it's fast enough for 4096 samples)
            self._compute_metrics(audio_data_float)
            
        except Exception as e:
            self.last_error = str(e)
            print(f"Callback Error: {e}")
            
        return (in_data, pyaudio.paContinue)

    def _compute_metrics(self, y):
        """
        Compute rigorous audio features using pure NumPy for stability.
        """
        # RMS
        rms = np.sqrt(np.mean(y**2))
        # Convert to roughly SPL (Sound Pressure Level) with offset
        # -90dBFS (silence) becomes 30dB, 0dBFS (max) becomes 120dB
        db = (20 * np.log10(rms + 1e-9)) + 120
        db = max(0.0, db) # Ensure positive
        
        # ZCR
        zcr = ((y[:-1] * y[1:]) < 0).sum() / len(y)
        
        # Spectral Flux (Using numpy FFT)
        spectrum = np.abs(np.fft.rfft(y))
        # Use standard deviation of spectrum as a proxy for "complexity/energy spread"
        flux = np.std(spectrum)
        
        # --- NOISE GATE ---
        # If audio is very quiet, zero out complex metrics to prevent static noise readings
        if rms < 0.02:
            zcr = 0.0
            flux = 0.0
            db = max(30.0, db) # Floor dB at ambient room level
        
        # --- DETECTION LOGIC ---
        status = "NORMAL"
        reason = "Environment stable"
        threat_score = 0.0
        
        # 1. Volume Threshold
        if rms > 0.5:
            status = "CRITICAL"
            reason = "High intensity event (Explosion/Scream)"
        elif rms > 0.2:
            status = "WARNING"
            reason = "Elevated volume detected"
            
        # 2. Panic Analysis (High ZCR + Volume)
        if zcr > 0.25 and rms > 0.1:
            status = "CRITICAL"
            reason = "High-frequency panic noise"

        # 3. Impact Analysis (Flux)
        if flux > 5.0 and rms > 0.1:
             if status == "NORMAL":
                 status = "WARNING"
                 reason = "Sudden transient impact"
        
        # Update State
        with self.lock:
            self.latest_metrics = {
                "rms": rms,
                "db": db,
                "zcr": zcr,
                "flux": flux,
                "threat_score": threat_score,
                "status": status,
                "reason": reason
            }
            
            # Add to smoothing buffer
            self.metric_buffer.append(self.latest_metrics)

    def get_data(self):
        """Get latest buffer and smoothed metrics for UI."""
        with self.lock:
            if not self.audio_buffer:
                return np.zeros(CHUNK), self.latest_metrics
            
            # Flatten buffer
            wave = np.concatenate(self.audio_buffer)
            
            # Compute Smoothed Metrics for UI stability
            if len(self.metric_buffer) > 0:
                smoothed = self.latest_metrics.copy()
                smoothed['rms'] = np.mean([m['rms'] for m in self.metric_buffer])
                smoothed['db'] = np.mean([m['db'] for m in self.metric_buffer])
                smoothed['zcr'] = np.mean([m['zcr'] for m in self.metric_buffer])
                smoothed['flux'] = np.mean([m['flux'] for m in self.metric_buffer])
                return wave, smoothed
            
            return wave, self.latest_metrics
