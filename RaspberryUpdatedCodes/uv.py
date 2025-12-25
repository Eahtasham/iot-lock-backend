import RPi.GPIO as GPIO
import time
import os

# Pin setup
TRIG = 17
ECHO = 27

# GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def measure_distance():
    GPIO.output(TRIG, False)
    time.sleep(0.1)

    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if time.time() - timeout_start > 0.02:
            return None

    pulse_end = time.time()
    timeout_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if time.time() - timeout_start > 0.02:
            return None

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150
    return round(distance, 2)


def run_iotgrp6():
    print("Running iotgrp6.py ...")
    os.system("python3 iotgrp6.py")
    print("Completed running iotgrp6.py")


try:
    presence_counter = 0  # Counts consecutive detections

    while True:
        dist = measure_distance()
        if dist is not None:
            print(f"Distance: {dist} cm")

            if dist <= 70:
                presence_counter += 1
                print(f"Object detected. Counter: {presence_counter}")

                # 2 loops × 2 seconds = 4 seconds of presence
                if presence_counter >= 2:
                    run_iotgrp6()
                    print("Waiting 20 seconds before checking again...")
                    time.sleep(20)
                    presence_counter = 0  # Reset counter after running script

            else:
                print("Object moved out of range. Resetting counter.")
                presence_counter = 0

        else:
            print("Distance measurement failed.")

        time.sleep(2)

except KeyboardInterrupt:
    print("Measurement stopped by User")

finally:
    GPIO.cleanup()
