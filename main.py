import argparse
import app
import time
import threading

def main():
    parser = argparse.ArgumentParser(description="CrowdLumen: Real-time Crowd Risk Monitoring")
    parser.add_argument('--headless', action='store_true', help='Run in headless mode (no dashboard)')
    args = parser.parse_args()

    if args.headless:
        print("Starting in HEADLESS mode...")
        # Start only the camera loop
        t = threading.Thread(target=app.camera_loop)
        t.daemon = True
        t.start()
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")
            if app.alert_system:
                app.alert_system.cleanup()
    else:
        print("Starting Dashboard...")
        print("Open http://localhost:5000 in your browser.")
        app.start_app()

if __name__ == "__main__":
    main()
