import pyaudio
import numpy as np
import time
import os
import sys

# --- CONFIGURATION ---
CHUNK = 1024 * 4  # Number of audio samples per frame
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
UPDATE_INTERVAL = 0.5  # Seconds between status updates
HISTORY_SIZE = 50     # How many frames to keep for background noise averaging

# Thresholds (tunable)
RMS_WARNING_THRESHOLD = 0.05  # Relative amplitude (0-1)
RMS_CRITICAL_THRESHOLD = 0.15 
VARIANCE_THRESHOLD = 0.01     # For chaotic noise detection

class AudioMonitor:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.running = False
        self.history = []
        self.status = "NORMAL"
        self.reason = "Stable sound environment"
        self.confidence = "HIGH"
        
        # Stat tracking
        self.sustained_abnormal_start = None

    def start(self):
        try:
            self.stream = self.p.open(format=FORMAT,
                                      channels=CHANNELS,
                                      rate=RATE,
                                      input=True,
                                      frames_per_buffer=CHUNK)
            self.running = True
            print("Microphone initialized. Listening...")
        except Exception as e:
            print(f"Error initializing audio: {e}")
            sys.exit(1)

    def process_audio(self):
        try:
            data = self.stream.read(CHUNK, exception_on_overflow=False)
            # Convert raw bytes to numpy array
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Normalize to -1.0 to 1.0
            normalized_data = audio_data / 32768.0
            
            # 1. Calculate RMS Energy (Loudness)
            rms = np.sqrt(np.mean(normalized_data**2))
            
            # 2. Calculate Spectral Flux (sudden changes) - simplified to variance for prototype
            # High variance in a short window implies chaotic noise
            variance = np.var(normalized_data)
            
            return rms, variance
            
        except Exception as e:
            return 0, 0

    def analyze_metrics(self, rms, variance):
        # Update history for adaptive background (could implement adaptive thresholds here)
        self.history.append(rms)
        if len(self.history) > HISTORY_SIZE:
            self.history.pop(0)
            
        # Decision Logic
        current_status = "NORMAL"
        running_reason = "Environment stable"
        
        # Check Critical Conditions
        if rms > RMS_CRITICAL_THRESHOLD:
            current_status = "CRITICAL"
            running_reason = "EXTREME LOUDNESS DETECTED"
        elif variance > 0.1: # Extremely chaotic
            current_status = "CRITICAL"
            running_reason = "Chaotic signal pattern"
            
        # Check Warning Conditions (if not critical)
        elif rms > RMS_WARNING_THRESHOLD:
            current_status = "WARNING"
            running_reason = "High volume spike"
        elif variance > VARIANCE_THRESHOLD:
            current_status = "WARNING"
            running_reason = "Irregular noise pattern"
            
        # Sustained check
        if current_status != "NORMAL":
            if self.sustained_abnormal_start is None:
                self.sustained_abnormal_start = time.time()
            elif time.time() - self.sustained_abnormal_start > 3.0:
                # If sustained for > 3 seconds, escalate or confirm critical
                if current_status == "WARNING":
                    current_status = "CRITICAL"
                    running_reason = "Sustained abnormal noise"
        else:
            self.sustained_abnormal_start = None

        self.status = current_status
        self.reason = running_reason

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_status(self, rms, variance):
        self.clear_screen()
        print("==========================================")
        print("   CROWDLUMEN AUDIO INTELLIGENCE LOOP     ")
        print("==========================================\n")
        
        print(f"STATUS:     [{self.get_colored_status(self.status)}]")
        print(f"REASON:     {self.reason}")
        print(f"CONFIDENCE: {self.confidence}\n")
        
        print("-" * 30)
        print("LIVE METRICS:")
        print(f"RMS Energy: {rms:.4f}  |  Threshold: {RMS_WARNING_THRESHOLD}")
        print(f"Variance:   {variance:.4f}  |  Threshold: {VARIANCE_THRESHOLD}")
        print("-" * 30)
        
        # Simple visualizer bar
        bar_length = 40
        fill = int(min(1.0, rms / (RMS_CRITICAL_THRESHOLD * 1.5)) * bar_length)
        bar = '|' * fill + '.' * (bar_length - fill)
        print(f"\nLEVEL: [{bar}]")

    def get_colored_status(self, status):
        # ANSI colors might not work in all Windows terminals without init, 
        # but modern Windows terminal supports it.
        # Fallback to plain text if needed.
        if status == "NORMAL":
            return "NORMAL"
        elif status == "WARNING":
            return "WARNING"
        elif status == "CRITICAL":
            return "! CRITICAL !"
        return status

    def run(self):
        self.start()
        print("System Live. Monitoring...")
        
        try:
            while self.running:
                rms, variance = self.process_audio()
                self.analyze_metrics(rms, variance)
                self.display_status(rms, variance)
                # Sleep is not needed for loop timing as stream.read is blocking/timed by rate
                # but for screen refresh rate we might want to skip some print cycles
                # However, stream.read(CHUNK) takes about 0.09s for 4096 samples at 44100Hz
                # So the loop runs ~10 times a second. That's fine for TUI updates.
        except KeyboardInterrupt:
            print("\nStopping...")
        finally:
            self.stream.stop_stream()
            self.stream.close()
            self.p.terminate()

if __name__ == "__main__":
    monitor = AudioMonitor()
    monitor.run()
