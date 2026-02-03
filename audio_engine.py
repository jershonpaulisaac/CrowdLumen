import numpy as np
import threading
import time
import math
from collections import deque

try:
    import pyaudio
except ImportError:
    pyaudio = None
    print("PyAudio not found. Audio will be in SIMULATION ONLY mode.")

class AudioMonitor:
    def __init__(self, simulate=False):
        self.simulate = simulate
        self.running = False
        self.audio_thread = None
        
        # Audio Params
        self.CHUNK = 2048 # Larger chunk for better frequency resolution
        self.FORMAT = pyaudio.paInt16 if pyaudio else None
        self.CHANNELS = 1
        self.RATE = 44100
        
        # Risk thresholds
        self.current_db = 45.0
        self.db_history = deque(maxlen=50)
        self.variance = 0.0
        
        # Frequency Bands (Bass, LowMid, Mid, HighMid, Treble)
        self.bands = [0, 0, 0, 0, 0]
        
        # Simulation triggers
        self.sim_mode = 'NORMAL' 
        
        # Results
        self.lock = threading.Lock()
        self.stats = {
            "db_level": 45.0,
            "risk_score": 0.0,
            "anomaly": False,
            "status": "Calm",
            "bands": [10, 10, 10, 10, 10], # Default for viz
            "source": "Simulation"
        }

    def start(self):
        self.running = True
        self.audio_thread = threading.Thread(target=self._monitor_loop)
        self.audio_thread.daemon = True
        self.audio_thread.start()
        print("Audio Monitor Started.")

    def stop(self):
        self.running = False
        if self.audio_thread:
            self.audio_thread.join()

    def set_simulation_mode(self, mode):
        self.sim_mode = mode # Maintained for fallback, but User wants Real Mic primarily.

    def _monitor_loop(self):
        pa = None
        stream = None
        
        if not self.simulate and pyaudio:
            try:
                pa = pyaudio.PyAudio()
                # List devices to debug if needed
                # for i in range(pa.get_device_count()): print(pa.get_device_info_by_index(i))
                
                stream = pa.open(format=self.FORMAT,
                                 channels=self.CHANNELS,
                                 rate=self.RATE,
                                 input=True,
                                 frames_per_buffer=self.CHUNK)
                print("Microphone Successfully Opened.")
                with self.lock: self.stats["source"] = "Microphone"
            except Exception as e:
                print(f"Error opening microphone: {e}. Switching to SIMULATION.")
                self.simulate = True
                with self.lock: self.stats["source"] = "Simulation (Mic Failed)"
        else:
             with self.lock: self.stats["source"] = "Simulation (Requested)"
        
        while self.running:
            if self.simulate or not stream:
                self._process_simulation()
                time.sleep(0.05) # Faster updates for viz
            else:
                try:
                    data = stream.read(self.CHUNK, exception_on_overflow=False)
                    self._process_stream(data)
                except Exception as e:
                    print(f"Audio read error: {e}")
                    time.sleep(0.1)
                    
            self._analyze_patterns()
            
        if stream:
            stream.stop_stream()
            stream.close()
        if pa:
            pa.terminate()

    def _process_stream(self, data):
        # 1. Decode
        audio_data = np.frombuffer(data, dtype=np.int16)
        
        # 2. RMS / dB
        rms = np.sqrt(np.mean(audio_data.astype(np.float64)**2))
        try:
            db = 20 * math.log10(rms) if rms > 0 else 0
        except:
             db = 0
             
        # Normalize dB (Approximate scaling for visualization)
        # Typically int16 audio: Quiet ~40dB, Loud ~90dB
        self.current_db = max(30.0, db)
        self.db_history.append(self.current_db)
        
        # 3. FFT (Frequency Analysis)
        windowed = audio_data * np.hanning(len(audio_data))
        fft_vals = np.abs(np.fft.rfft(windowed))
        freqs = np.fft.rfftfreq(len(windowed), 1.0/self.RATE)
        
        # Studio Style: 32 Bands
        # Logarithmic binning from 20Hz to 20kHz
        # We can just do linear interpolation or simple block averaging for now for speed
        
        self.bands = []
        num_bands = 32
        
        # Split FFT into 32 chunks (linear/log hybrid)
        # For simplicity in this lightweight engine, we use linear grouping of FFT bins
        # But low freqs need fewer bins, high freqs need more.
        
        # Simple approach: Resample FFT array to length 32
        # Or just average blocks.
        
        chunk_size = len(fft_vals) // num_bands
        for i in range(num_bands):
             start = i * chunk_size
             end = (i + 1) * chunk_size
             if start >= len(fft_vals): break
             
             segment = fft_vals[start:end]
             if len(segment) == 0: 
                 val = 0
             else:
                 val = np.mean(segment)
             
             # Log scale for dB view
             if val > 1:
                 db_val = 10 * np.log10(val)
             else: 
                 db_val = 0
                 
             # Normalize 0-100 roughly
             # Typically values might be 0-100dB
             norm_val = min(100, max(0, db_val * 2)) # scaling factor
             self.bands.append(norm_val)

    def _process_simulation(self):
        # Fake bands for simulation
        base = 45.0
        if self.sim_mode == 'LOUD': base = 75.0
        elif self.sim_mode == 'PANIC': base = 95.0
        
        noise = np.random.normal(0, 5.0)
        self.current_db = base + noise
        self.db_history.append(self.current_db)
        
        # Fake FFT
        # Panic has more high freq?
        # Fake FFT
        # Generate 32 bands
        self.bands = [np.random.randint(10, 60) for _ in range(32)]
        
        if self.sim_mode == 'PANIC': # Boost highs (last 8 bands)
             for i in range(24, 32):
                 self.bands[i] += np.random.randint(20, 40)

    def _analyze_patterns(self):
        if len(self.db_history) < 10: return

        recent = list(self.db_history)[-20:]
        variance = np.var(recent)
        avg_db = np.mean(recent)
        
        risk_score = 0.0
        anomaly = False
        status = "Calm"
        
        if avg_db > 95:
            status = "PANIC / SCREAM"
            risk_score = 1.0
            anomaly = True
        elif avg_db > 85:
            if variance > 25:
                 status = "CHAOTIC NOISE"
                 risk_score = 0.9
                 anomaly = True
            else:
                 status = "High Volume"
                 risk_score = 0.6
        elif avg_db > 75:
            status = "Elevated"
            risk_score = 0.3
        else:
            status = "Normal"
            risk_score = 0.1
            
        with self.lock:
            # Preserve source info
            src = self.stats.get("source", "Unknown")
            self.stats = {
                "db_level": float(avg_db),
                "risk_score": float(risk_score),
                "anomaly": bool(anomaly),
                "status": status,
                "variance": float(variance),
                "bands": self.bands,
                "source": src
            }

    def get_stats(self):
        with self.lock:
            return self.stats

if __name__ == "__main__":
    am = AudioMonitor(simulate=False)
    am.start()
    try:
        while True:
            s = am.get_stats()
            print(f"dB: {s['db_level']:.1f} Bands: {[int(b) for b in s['bands']]} Src: {s['source']}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        am.stop()
