import config
import time
import platform

# Mock GPIO class to prevent errors on Windows/Non-Pi
class MockGPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    LOW = 0
    HIGH = 1
    
    @staticmethod
    def setmode(mode):
        print(f"[MOCK HARDWARE] GPIOMode set to {mode}")
        
    @staticmethod
    def setup(pin, mode):
        print(f"[MOCK HARDWARE] Setup Pin {pin} as {mode}")
        
    @staticmethod
    def output(pin, state):
        state_str = "ON" if state == 1 else "OFF"
        # Only print meaningful state changes or important pins to avoid clutter
        # print(f"[MOCK HARDWARE] Pin {pin} -> {state_str}")
        pass
        
    @staticmethod
    def cleanup():
        print("[MOCK HARDWARE] Cleanup")
        
    @staticmethod
    def setwarnings(flag):
        pass

# Try to import RPi.GPIO, fall back to Mock if failed or on Windows
try:
    if config.SIMULATE_HARDWARE or platform.system() == "Windows":
        raise ImportError("Forcing Mock Mode")
    import RPi.GPIO as GPIO
    print("RPi.GPIO detected. Using real hardware.")
except (ImportError, RuntimeError):
    GPIO = MockGPIO
    print("RPi.GPIO not found or Windows detected. Using MOCK hardware.")

class AlertSystem:
    def __init__(self):
        self.red_pin = config.RED_LED_PIN
        self.yellow_pin = config.YELLOW_LED_PIN
        self.green_pin = config.GREEN_LED_PIN
        self.buzzer_pin = config.BUZZER_PIN
        
        self._setup_gpio()
        self.current_risk = None
        
    def _setup_gpio(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            pins = [self.red_pin, self.yellow_pin, self.green_pin, self.buzzer_pin]
            for pin in pins:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW) # Start off
        except Exception as e:
            print(f"Error setting up GPIO: {e}")

    def trigger_alert(self, risk_level):
        """
        Updates the LED/Buzzer state based on risk level.
        """
        if risk_level == self.current_risk:
            return # No change needed

        self.current_risk = risk_level
        # Reset all first
        GPIO.output(self.red_pin, GPIO.LOW)
        GPIO.output(self.yellow_pin, GPIO.LOW)
        GPIO.output(self.green_pin, GPIO.LOW)
        GPIO.output(self.buzzer_pin, GPIO.LOW)
        
        print(f"--- ALERT SYSTEM: {risk_level} RISK ---")

        if risk_level == 'HIGH':
            GPIO.output(self.red_pin, GPIO.HIGH)
            GPIO.output(self.buzzer_pin, GPIO.HIGH)
        elif risk_level == 'MEDIUM':
            GPIO.output(self.yellow_pin, GPIO.HIGH)
        else: # LOW
            GPIO.output(self.green_pin, GPIO.HIGH)

    def cleanup(self):
        GPIO.cleanup()

if __name__ == "__main__":
    # Test
    alert = AlertSystem()
    print("Testing Low...")
    alert.trigger_alert('LOW')
    time.sleep(1)
    print("Testing Medium...")
    alert.trigger_alert('MEDIUM')
    time.sleep(1)
    print("Testing High...")
    alert.trigger_alert('HIGH')
    time.sleep(1)
    alert.cleanup()
