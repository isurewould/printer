import RPi.GPIO as GPIO
import time

BUTTON_GPIO = 16

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

last_state = GPIO.HIGH  # Assume button is unpressed initially

try:
    print("Running... Press Ctrl+C to exit.")
    while True:
        current_state = GPIO.input(BUTTON_GPIO)
        if current_state == GPIO.LOW and last_state == GPIO.HIGH:
            print("Button pressed!")
            time.sleep(0.05)  # small debounce
        last_state = current_state
        time.sleep(0.01)  # check every 10ms
except KeyboardInterrupt:
    print("\nExiting cleanly...")
finally:
    GPIO.cleanup()
