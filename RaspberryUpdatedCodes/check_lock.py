import requests
import time
import RPi.GPIO as GPIO
import os

# ====== CONFIGURATION ======
RENDER_URL = "https://iot-lock-api.onrender.com/lock"
LED_PIN = 22
SERVO_PIN = 25  # Pin connected to servo signal wire
CAPTURE_FOLDER = "captured_faces"  # <--- folder to clear

# ====== GPIO SETUP ======
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# Setup PWM for Servo
servo_pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz for servo
servo_pwm.start(0)  # Initialize with 0% duty cycle


def set_servo_angle(angle):
    """Rotate servo to a specific angle and then stop PWM signal"""
    duty = 2 + (angle / 18)  # Convert angle (0–180) to duty cycle (approx)
    GPIO.output(SERVO_PIN, True)
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    GPIO.output(SERVO_PIN, False)
    servo_pwm.ChangeDutyCycle(0)


def control_lock(value):
    """Control LED and servo based on received command"""
    if value == 1:
        print("🔓 UNLOCK COMMAND RECEIVED")

        GPIO.output(LED_PIN, GPIO.HIGH)
        set_servo_angle(0)
        print("✅ Servo rotated to 90°")

        time.sleep(5)
        set_servo_angle(90)
        GPIO.output(LED_PIN, GPIO.LOW)

    elif value == 0:
        print("🔒 LOCK COMMAND RECEIVED (Blinking LED)")
        for _ in range(10):
            GPIO.output(LED_PIN, GPIO.HIGH)
            time.sleep(0.3)
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(0.3)
        print("✅ Finished blinking")


def clear_captured_images():
    """Delete all images from captured_faces/ folder"""
    if not os.path.exists(CAPTURE_FOLDER):
        return

    for file in os.listdir(CAPTURE_FOLDER):
        file_path = os.path.join(CAPTURE_FOLDER, file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"⚠️ Error deleting {file}: {e}")

    print("🧹 All images from 'captured_faces/' folder deleted!")


def poll_server():
    """Continuously poll server every 2 seconds for new commands"""
    print("⏳ Waiting for commands...")

    while True:
        try:
            response = requests.get(RENDER_URL, timeout=5)
            data = response.json()
            value = data.get('value')

            print(f"\n📡 Server Response: {value}")

            # Only process commands if value is 0 or 1
            if value in [0, 1]:
                print(f"✅ VALID COMMAND RECEIVED: {value}")
                control_lock(value)

                # Clear command on server
                requests.post(f"{RENDER_URL}/clear")

                # Delete images only for valid commands
                clear_captured_images()
            else:
                print("⚠️ Ignored: Command is not 0 or 1, folder not cleared.")

        except Exception as e:
            print(f"\n❌ Error: {e}")

        time.sleep(1)



# ====== MAIN PROGRAM ======
if __name__ == '__main__':
    print("\n" + "=" * 50)
    print("🔌 IoT Lock Controller Starting (GPIO MODE)")
    print(f"📡 Polling: {RENDER_URL}")
    print("💡 Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    try:
        poll_server()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down...")
    finally:
        servo_pwm.stop()
        GPIO.cleanup()
