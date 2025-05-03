from picamera2 import Picamera2, Preview
import RPi.GPIO as GPIO
import time, os

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration())
picam2.start_preview(Preview.QTGL)
picam2.start()

