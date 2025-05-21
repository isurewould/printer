

### File: button_listener.py
#!/usr/bin/env python3
"""Listens for a press on GPIO 16 and tells Flask to save & print a photo."""
import signal
import requests
from gpiozero import Button

BUTTON_GPIO = 16  # change if wired differently
FLASK_CAPTURE_ENDPOINT = "http://localhost:5000/capture"


def on_press():
    try:
        r = requests.post(FLASK_CAPTURE_ENDPOINT, timeout=5)
        print("Button pressed – Flask replied:", r.status_code, r.text)
    except Exception as e:
        print("Failed to trigger capture:", e)


button = Button(BUTTON_GPIO, pull_up=True, bounce_time=0.1)
button.when_pressed = on_press

print("Button listener active (GPIO", BUTTON_GPIO, ")…")
signal.pause()
