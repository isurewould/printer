#!/usr/bin/env python3
"""
Flask server for the Pi photo booth:
• streams a full-screen preview
• retries camera acquisition if busy
• saves and prints each capture
• cleans up the camera on exit
"""

from flask import Flask, render_template, Response
from picamera2 import Picamera2
from escpos.printer import Usb
from PIL import Image, ImageOps, ImageEnhance
import threading
import time
import cv2
import os
import atexit
import signal
import sys

app = Flask(__name__)
PHOTOS_DIR = "photos"
os.makedirs(PHOTOS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Camera setup with retry logic
# ---------------------------------------------------------------------------

def open_camera(max_attempts: int = 5, delay: float = 1.5):
    for attempt in range(1, max_attempts + 1):
        try:
            return Picamera2()
        except RuntimeError as err:
            print(f"Camera busy (attempt {attempt}/{max_attempts}): {err}")
            if attempt == max_attempts:
                raise
            time.sleep(delay)

picam2 = open_camera()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "XRGB8888", "size": (640, 480)}
    )
)
picam2.start()

# ---------------------------------------------------------------------------
# Clean-up helpers
# ---------------------------------------------------------------------------

def close_camera():
    try:
        picam2.stop()
    except Exception:
        pass
    try:
        picam2.close()
    except Exception:
        pass

atexit.register(close_camera)

def handle_exit(signum, frame):
    close_camera()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

# ---------------------------------------------------------------------------
# Frame grabber thread
# ---------------------------------------------------------------------------

frame = None
lock = threading.Lock()

def capture_frames():
    global frame
    while True:
        arr = picam2.capture_array()
        ok, jpeg = cv2.imencode(".jpg", arr)
        if ok:
            with lock:
                frame = jpeg.tobytes()
        time.sleep(0.03)  # ~30 fps

# ---------------------------------------------------------------------------
# Photo helpers
# ---------------------------------------------------------------------------

def save_photo() -> str:
    with lock:
        if frame is None:
            return ""
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = os.path.join(PHOTOS_DIR, f"photo_{ts}.jpg")
        # Write raw JPEG first
        with open(path, "wb") as f:
            f.write(frame)
        # Reopen and enhance brightness
        try:
            img = Image.open(path).convert("RGB")
            enhancer = ImageEnhance.Brightness(img)
            brighter_img = enhancer.enhance(1.3)  # 30% brighter
            brighter_img.save(path)
        except Exception as e:
            print("Brightness adjustment failed:", e)
        print("Saved", path)
        return path

def print_photo(path: str) -> bool:
    try:
        img = Image.open(path).convert("L")
        img = ImageOps.autocontrast(img)
        max_w = 384
        img = img.resize((max_w, int(img.height * max_w / img.width)))
        img = img.convert("1")
        printer = Usb(0x0485, 0x5741)  # adjust VID/PID if needed
        printer.image(img)
        printer.cut()
        printer.close()
        print("Printed", path)
        return True
    except Exception as err:
        print("Print failed:", err)
        return False

# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/video_feed")
def video_feed():
    def gen():
        while True:
            with lock:
                buf = frame
            if buf is None:
                time.sleep(0.03)
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf + b"\r\n"
            time.sleep(0.03)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/capture", methods=["POST"])
def capture():
    path = save_photo()
    if not path:
        return "No frame yet", 500
    ok = print_photo(path)
    return ("Captured & printed" if ok else "Captured but print failed"), (200 if ok else 500)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    threading.Thread(target=capture_frames, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, threaded=True)
