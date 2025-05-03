#!/usr/bin/env python3
from flask import Flask, render_template, Response, request, send_from_directory
from picamera2 import Picamera2
import threading
import time
import cv2
from gpiozero import Button
import os
import base64
import io
from PIL import Image, ImageEnhance, ImageOps
from escpos.printer import Usb

app = Flask(__name__)
PHOTOS_DIR = 'photos'
os.makedirs(PHOTOS_DIR, exist_ok=True)

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": "XRGB8888", "size": (640, 480)}))
picam2.start()

frame = None
last_captured_frame = None
lock = threading.Lock()

show_captured = False
capture_time = 0

BUTTON_GPIO = 16
button = Button(BUTTON_GPIO, pull_up=True, bounce_time=0.2)

def capture_frames():
    global frame
    while True:
        new_frame = picam2.capture_array()
        ret, jpeg = cv2.imencode('.jpg', new_frame)
        if ret:
            with lock:
                frame = jpeg.tobytes()
        time.sleep(0.03)

def save_photo():
    global frame, last_captured_frame, show_captured, capture_time
    with lock:
        if frame is not None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"photo_{timestamp}.jpg"
            filepath = os.path.join(PHOTOS_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(frame)
            print(f"Photo saved: {filepath}")
            last_captured_frame = frame
            show_captured = True
            capture_time = time.time()

def on_button_pressed():
    print("Button pressed!")
    save_photo()

button.when_pressed = on_button_pressed

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    def generate():
        global frame, last_captured_frame, show_captured, capture_time
        while True:
            with lock:
                current_time = time.time()
                if show_captured and current_time - capture_time < 5:
                    output_frame = last_captured_frame
                else:
                    show_captured = False
                    output_frame = frame
                if output_frame is None:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + output_frame + b'\r\n')
            time.sleep(0.03)
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture', methods=['POST'])
def capture():
    save_photo()
    return "Photo captured", 200

@app.route('/photos')
def photos():
    files = os.listdir(PHOTOS_DIR)
    files = sorted(files, reverse=True)
    return render_template('photos.html', photos=files)

@app.route('/photos/<filename>')
def photo_file(filename):
    return send_from_directory(PHOTOS_DIR, filename)

@app.route('/photos/<filename>/print', methods=['POST'])
def print_selected_photo(filename):
    if print_photo(filename):
        return "Printed", 200
    else:
        return "Failed to print", 500

@app.route('/preview-print', methods=['POST'])
def preview_print():
    try:
        data = request.get_json()
        image_data = data['image'].split(',')[1]
        img_bytes = base64.b64decode(image_data)
        img = Image.open(io.BytesIO(img_bytes)).convert("L")

        # Auto histogram-based contrast adjustment
        img = ImageOps.autocontrast(img)

        # Resize for 2-inch (384px wide) thermal printer
        img = img.resize((384, int(img.height * (384 / img.width))))

        # Apply user-controlled adjustments
        brightness = float(data.get('brightness', 1.0))
        contrast = float(data.get('contrast', 1.0))

        img = ImageEnhance.Brightness(img).enhance(brightness)
        img = ImageEnhance.Contrast(img).enhance(contrast)

        # Dither to 1-bit black and white
        img = img.convert('1')

        printer = Usb(0x0485, 0x5741)
        printer.image(img)
        printer.cut()
        printer.close()

        return "OK", 200
    except Exception as e:
        print(f"Print failed: {e}")
        return f"Print failed: {e}", 500

def print_photo(filename):
    try:
        filepath = os.path.join(PHOTOS_DIR, filename)
        img = Image.open(filepath).convert("L")

        # Auto contrast
        img = ImageOps.autocontrast(img)

        # Resize
        max_width = 384
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)))

        # Optional enhancement
        img = ImageEnhance.Brightness(img).enhance(1.0)
        img = ImageEnhance.Contrast(img).enhance(1.0)

        # Convert to 1-bit
        img = img.convert("1")

        p = Usb(0x0485, 0x5741)
        p.image(img)
        p.cut()
        p.close()
        return True
    except Exception as e:
        print("Print failed:", e)
        return False

if __name__ == '__main__':
    t = threading.Thread(target=capture_frames)
    t.daemon = True
    t.start()
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\nExiting cleanly...")
    finally:
        picam2.stop()
        print("Camera stopped.")
