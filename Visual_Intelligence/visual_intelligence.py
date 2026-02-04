import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
import time
import numpy as np
from detector import HumanDetector
from tracker import CentroidTracker
import sys

# --- CONFIGURATION ---
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
THEME_COLOR = "dark-blue"  # CustomTkinter theme
APPEARANCE_MODE = "Dark"

# Threat Thresholds
THREAT_NORMAL = 0
THREAT_WARNING = 1
THREAT_CRITICAL = 2

# Analysis Tuning
SPEED_HISTORY_LEN = 10
CHAOS_THRESHOLD_WARNING = 15.0  # Avg pixel movement needed for warning
CHAOS_THRESHOLD_CRITICAL = 30.0 # Avg pixel movement needed for critical
DENSITY_THRESHOLD_WARNING = 8   # Number of people
DENSITY_THRESHOLD_CRITICAL = 15

class VisualIntelligenceApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Setup Window ---
        self.title("CrowdLumen - Visual Intelligence Module")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        ctk.set_appearance_mode(APPEARANCE_MODE)
        ctk.set_default_color_theme(THEME_COLOR)
        
        # --- State ---
        self.running = True
        self.current_camera_index = 0
        self.cap = None
        self.detector = None
        self.tracker = None
        self.frame_count = 0
        
        # Analysis State
        self.object_speeds = {} # {objID: [speed1, speed2...]}
        self.prev_centroids = {}
        self.current_threat = "NORMAL"
        self.threat_color = "green"
        self.current_reason = "System Initializing..."
        self.person_count = 0
        self.chaos_metric = 0.0

        # --- Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (Controls & Stats)
        self.sidebar_frame = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self._build_sidebar()

        # Main Video Area
        self.video_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#000000")
        self.video_frame.grid(row=0, column=1, sticky="nsew")
        
        self.video_label = ctk.CTkLabel(self.video_frame, text="", bg_color="black")
        self.video_label.pack(expand=True, fill="both", padx=10, pady=10)

        # --- Initialization ---
        # --- Initialization ---
        self.reason_text.delete("0.0", "end")
        self.reason_text.insert("0.0", "LOADING MODEL...")
        self.update()
        
        # Load AI in background to not freeze UI
        self.after(100, self._init_ai)

    def _build_sidebar(self):
        # Title
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="CrowdLumen\nVisual Intelligence", 
                                     font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Camera Selection
        self.cam_label = ctk.CTkLabel(self.sidebar_frame, text="Video Source:", anchor="w")
        self.cam_label.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.camera_option_menu = ctk.CTkOptionMenu(self.sidebar_frame, 
                                                    values=["Camera 0 (Laptop)", "Camera 1 (USB)"],
                                                    command=self.change_camera)
        self.camera_option_menu.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        # Threat Level Indicator
        self.threat_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="gray20", corner_radius=10)
        self.threat_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.threat_title = ctk.CTkLabel(self.threat_frame, text="THREAT LEVEL", 
                                       font=ctk.CTkFont(size=12, weight="bold"))
        self.threat_title.pack(pady=(10, 0))
        
        self.threat_val_label = ctk.CTkLabel(self.threat_frame, text="NORMAL", 
                                           font=ctk.CTkFont(size=24, weight="bold"),
                                           text_color="green")
        self.threat_val_label.pack(pady=(5, 10))

        # Status / Reason
        self.reason_label = ctk.CTkLabel(self.sidebar_frame, text="Status Reasoning:", anchor="w")
        self.reason_label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.reason_text = ctk.CTkTextbox(self.sidebar_frame, height=80, fg_color="gray15")
        self.reason_text.grid(row=5, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.reason_text.insert("0.0", "Initializing...")

        # Metrics
        self.metric_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.metric_frame.grid(row=6, column=0, padx=20, pady=10, sticky="ew")
        
        # Person Count
        self.count_label = ctk.CTkLabel(self.metric_frame, text="Person Count: 0", anchor="w", font=ctk.CTkFont(size=14))
        self.count_label.pack(fill="x", pady=5)
        
        # Chaos Metric
        self.chaos_label = ctk.CTkLabel(self.metric_frame, text="Movement Intensity / Chaos", anchor="w")
        self.chaos_label.pack(fill="x", pady=(10, 0))
        
        self.chaos_progress = ctk.CTkProgressBar(self.metric_frame)
        self.chaos_progress.pack(fill="x", pady=(5, 5))
        self.chaos_progress.set(0)

        # Footer
        self.footer_label = ctk.CTkLabel(self.sidebar_frame, text="v1.0.0 | Offline Mode", 
                                       text_color="gray50", font=ctk.CTkFont(size=10))
        self.footer_label.grid(row=9, column=0, padx=20, pady=10)

    def _init_ai(self):
        try:
            self.detector = HumanDetector(confidence=0.35)
            self.tracker = CentroidTracker(max_disappeared=10)
            self.start_camera(0)
            self.update_video_loop()
        except Exception as e:
            print(f"Error init AI: {e}")
            self.reason_text.delete("0.0", "end")
            self.reason_text.insert("0.0", f"Critical Error: {e}")

    def start_camera(self, index):
        if self.cap is not None:
            self.cap.release()
        
        print(f"Opening camera {index}...")
        self.cap = cv2.VideoCapture(index)
        
        # Set resolution to reasonable HD for performance
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not self.cap.isOpened():
            print(f"Failed to open camera {index}")
            self.reason_text.delete("0.0", "end")
            self.reason_text.insert("0.0", f"Camera {index} failed to open.")

    def change_camera(self, selection):
        idx = 0
        if "Camera 1" in selection:
            idx = 1
        self.current_camera_index = idx
        self.start_camera(idx)

    def update_video_loop(self):
        start_time = time.time()
        
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                # 1. Detection
                rects = self.detector.detect(frame)
                
                # 2. Tracking
                objects = self.tracker.update(rects)
                
                # 3. Analytics
                self.analyze_crowd(objects)
                
                # 4. Visualization
                frame = self.draw_hud(frame, rects, objects)
                
                # 5. Convert to Tkinter Image
                # Convert BGR to RGB
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize to fit the label if needed (keep aspect ratio)
                # But for now let's just use the frame size or stretch slightly
                # To make it look "Matte" and fit, we usually resize to container.
                # Just using simple resize for performance/simplicity in this step.
                
                display_h = self.video_label.winfo_height()
                display_w = self.video_label.winfo_width()
                
                # Simple aspect ratio keep
                if display_w > 10 and display_h > 10:
                    img_pil = Image.fromarray(img_rgb)
                    # Resize nicely
                    img_pil = self._resize_image_keep_aspect(img_pil, display_w, display_h)
                    ctk_img = ctk.CTkImage(light_image=img_pil, dark_image=img_pil, size=img_pil.size)
                    self.video_label.configure(image=ctk_img)
                    self.video_label.image = ctk_img # Keep ref

        # Schedule next update (aim for ~30 FPS -> 33ms, but process takes time)
        # Adaptive delay
        elapsed = time.time() - start_time
        delay = max(5, int(33 - (elapsed * 1000)))
        self.after(delay, self.update_video_loop)

    def _resize_image_keep_aspect(self, img, max_w, max_h):
        w, h = img.size
        ratio = min(max_w/w, max_h/h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        return img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    def analyze_crowd(self, objects):
        # objects is {ID: (centerX, centerY)}
        
        total_speed = 0
        count = len(objects)
        moving_people = 0
        
        current_ids = list(objects.keys())
        
        # Calculate speeds
        for obj_id, centroid in objects.items():
            if obj_id in self.prev_centroids:
                prev_c = self.prev_centroids[obj_id]
                dist = np.linalg.norm(np.array(centroid) - np.array(prev_c))
                
                # Update speed history
                if obj_id not in self.object_speeds:
                    self.object_speeds[obj_id] = []
                self.object_speeds[obj_id].append(dist)
                if len(self.object_speeds[obj_id]) > SPEED_HISTORY_LEN:
                    self.object_speeds[obj_id].pop(0)
                    
                # Smooth speed
                avg_speed = np.mean(self.object_speeds[obj_id])
                total_speed += avg_speed
                if avg_speed > 2.0: # threshold for "moving"
                    moving_people += 1
            
            # Store current as prev for next frame
            self.prev_centroids[obj_id] = centroid

        # Cleanup old IDs
        for old_id in list(self.prev_centroids.keys()):
            if old_id not in current_ids:
                del self.prev_centroids[old_id]
                if old_id in self.object_speeds:
                    del self.object_speeds[old_id]

        # Metric Logic
        avg_crowd_speed = total_speed / count if count > 0 else 0
        self.chaos_metric = avg_crowd_speed # Use speed as chaos proxy for now
        self.person_count = count
        
        # --- Threat Classification ---
        # Heuristics:
        # 1. High Density + Any Movement -> WARNING
        # 2. High Speed (Surge) -> CRITICAL
        # 3. Very High Density -> WARNING/CRITICAL
        
        status = "NORMAL"
        color = "green"
        reason = "Stable Conditions"
        
        # Chaos Progress Bar (Scale 0-50 pixels avg speed)
        norm_chaos = min(avg_crowd_speed / 20.0, 1.0) 
        self.chaos_progress.set(norm_chaos)
        
        # Logic
        if avg_crowd_speed > CHAOS_THRESHOLD_CRITICAL:
            status = "CRITICAL"
            color = "#ff3333" # Bright Red
            reason = "CRITICAL: Detected sudden crowd surge/panic!"
        
        elif avg_crowd_speed > CHAOS_THRESHOLD_WARNING:
            status = "WARNING"
            color = "#ffff33" # Yellow
            reason = "WARNING: Increasing crowd movement speed."
            
        elif count > DENSITY_THRESHOLD_CRITICAL:
            status = "CRITICAL"
            color = "#ff3333"
            reason = "CRITICAL: Extreme overcrowding detected."
            
        elif count > DENSITY_THRESHOLD_WARNING:
            if status != "CRITICAL": # Don't downgrade
                status = "WARNING"
                color = "#ffff33"
                reason = "WARNING: Crowd density is high."
        
        self.current_threat = status
        self.threat_color = color
        self.current_reason = reason
        
        # Update Sidebar
        self.threat_val_label.configure(text=status, text_color=color)
        self.reason_text.delete("0.0", "end")
        self.reason_text.insert("0.0", reason)
        self.count_label.configure(text=f"Person Count: {count}")

    def draw_hud(self, frame, rects, objects):
        # Draw bounding boxes (subtle)
        # Use simple CV2 drawing on the frame
        
        overlay = frame.copy()
        
        for (x1, y1, x2, y2) in rects:
            # Box Color based on threat
            color = (0, 255, 0) # BGR
            if self.current_threat == "WARNING": color = (0, 255, 255)
            if self.current_threat == "CRITICAL": color = (0, 0, 255)
            
            # Use corner brackets or thin lines for "Professional"
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Optional: Add ID
            # Find closest centroid (skip for performance clean look)

        # Draw "HUD" lines or tracking vectors
        for obj_id, centroid in objects.items():
            if obj_id in self.prev_centroids:
                prev = self.prev_centroids[obj_id]
                # Draw small movement vector
                cv2.line(frame, (prev[0], prev[1]), (centroid[0], centroid[1]), (0, 255, 255), 2)
                cv2.circle(frame, (centroid[0], centroid[1]), 3, (0, 0, 255), -1)

        # Add timestamp/fps? Clean dashboard has that info on side.
        # Maybe just a "REC" indicator or "LIVE"
        cv2.circle(frame, (30, 30), 5, (0, 0, 255), -1)
        cv2.putText(frame, "LIVE", (45, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)

        return frame

    def on_close(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = VisualIntelligenceApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
