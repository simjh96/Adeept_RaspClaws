#!/usr/bin/env python3
from importlib import import_module
import os
import time
import threading
from flask import Flask, render_template, Response
from flask_cors import CORS
import cv2
import move
import LED
from camera_opencv import Camera

# Initialize Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True)
camera = Camera()

def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(camera),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

def perform_movement_sequence():
    """Perform the predefined movement sequence."""
    # Initialize movement
    move.init_all()
    time.sleep(1)  # Wait for initialization
    
    # Move forward 2 steps
    for _ in range(2):
        move.move(1, 35, 'no')  # Step 1
        time.sleep(0.1)
        move.move(2, 35, 'no')  # Step 2
        time.sleep(0.1)
        move.move(3, 35, 'no')  # Step 3
        time.sleep(0.1)
        move.move(4, 35, 'no')  # Step 4
        time.sleep(0.1)
    
    # Turn left 2 steps
    for _ in range(2):
        move.move(1, 35, 'left')  # Step 1
        time.sleep(0.1)
        move.move(2, 35, 'left')  # Step 2
        time.sleep(0.1)
        move.move(3, 35, 'left')  # Step 3
        time.sleep(0.1)
        move.move(4, 35, 'left')  # Step 4
        time.sleep(0.1)
    
    # Move head
    # Up 30 degrees
    move.look_up()
    time.sleep(0.5)
    # Down 30 degrees
    move.look_down()
    time.sleep(0.5)
    # Left 30 degrees
    move.look_left()
    time.sleep(0.5)
    # Right 30 degrees
    move.look_right()
    time.sleep(0.5)
    # Return to home position
    move.look_home()

def movement_thread():
    """Thread function to run the movement sequence."""
    time.sleep(2)  # Wait for server to start
    perform_movement_sequence()

if __name__ == '__main__':
    try:
        # Start movement sequence in a separate thread
        movement = threading.Thread(target=movement_thread)
        movement.daemon = True
        movement.start()
        
        # Start the Flask server
        app.run(host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        # Clean up on exit
        move.clean_all() 