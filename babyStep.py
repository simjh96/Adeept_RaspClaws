#!/usr/bin/env python3
import os
import sys
import time
import threading
import math
import datetime
import cv2
import numpy as np

# Add server directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# Import server modules
import move
import LED
from babyHost import VideoHost

# Global servo lock to prevent competing servo control
servo_lock = threading.Lock()

class MotionDetector:
    def __init__(self, camera):
        self.camera = camera
        self.avg = None
        self.last_motion = None
        self.motion_detected = False
        self.object_position = None
        
    def detect_motion(self):
        """Detect motion and calculate object position relative to robot."""
        frame = self.camera.get_frame_safe()  # Use thread-safe method
        if frame is None:
            return None
            
        # Convert bytes to numpy array
        nparr = np.frombuffer(frame, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert to grayscale and blur
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        # Initialize background model if needed
        if self.avg is None:
            self.avg = gray.copy().astype("float")
            return None

        # Accumulate weighted average
        cv2.accumulateWeighted(gray, self.avg, 0.5)
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg))

        # Threshold and dilate
        thresh = cv2.threshold(frameDelta, 5, 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Find contours
        contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

        # Process largest contour
        if len(contours) > 0:
            largest_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest_contour) > 5000:  # Min area threshold
                (x, y, w, h) = cv2.boundingRect(largest_contour)
                center_x = x + w//2
                center_y = y + h//2
                
                # Calculate relative position from center of frame
                frame_center_x = img.shape[1] // 2
                frame_center_y = img.shape[0] // 2
                
                # Calculate angles (assuming 60° FOV for the camera)
                angle_x = ((center_x - frame_center_x) / frame_center_x) * 30
                angle_y = ((center_y - frame_center_y) / frame_center_y) * 30
                
                # Get current head position
                head_x = 300  # Default center position
                head_y = 300  # Default center position
                
                # Calculate total angles including head position
                total_angle_x = angle_x + (head_x - 300) / 10
                total_angle_y = angle_y + (head_y - 300) / 10
                
                # Estimate distance based on object size
                distance = 1000 / math.sqrt(w * h)
                
                self.object_position = {
                    'angle_x': total_angle_x,
                    'angle_y': total_angle_y,
                    'distance': distance
                }
                self.motion_detected = True
                return self.object_position
                
        return None

def safe_move(step, speed, direction):
    """Thread-safe wrapper for move commands."""
    with servo_lock:
        move.move(step, speed, direction)

def safe_look(direction):
    """Thread-safe wrapper for look commands."""
    with servo_lock:
        if direction == 'up':
            move.look_up()
        elif direction == 'down':
            move.look_down()
        elif direction == 'left':
            move.look_left()
        elif direction == 'right':
            move.look_right()
        elif direction == 'home':
            move.look_home()

def perform_movement_sequence():
    """Perform the predefined movement sequence."""
    # Initialize movement
    with servo_lock:
        move.init_all()
    time.sleep(1)
    
    # Move forward 2 steps
    for _ in range(2):
        safe_move(1, 35, 'no')
        time.sleep(0.1)
        safe_move(2, 35, 'no')
        time.sleep(0.1)
        safe_move(3, 35, 'no')
        time.sleep(0.1)
        safe_move(4, 35, 'no')
        time.sleep(0.1)
    
    # Turn left 2 steps
    for _ in range(2):
        safe_move(1, 35, 'left')
        time.sleep(0.1)
        safe_move(2, 35, 'left')
        time.sleep(0.1)
        safe_move(3, 35, 'left')
        time.sleep(0.1)
        safe_move(4, 35, 'left')
        time.sleep(0.1)
    
    # Move head
    safe_look('up')
    time.sleep(0.5)
    safe_look('down')
    time.sleep(0.5)
    safe_look('left')
    time.sleep(0.5)
    safe_look('right')
    time.sleep(0.5)
    safe_look('home')

def move_to_object(position):
    """Move towards detected object based on calculated position."""
    if not position:
        return
        
    # Calculate turn angle needed
    turn_angle = position['angle_x']
    
    # Turn towards object
    if abs(turn_angle) > 5:
        direction = 'left' if turn_angle > 0 else 'right'
        steps = min(abs(int(turn_angle / 10)), 4)
        
        for _ in range(steps):
            safe_move(1, 35, direction)
            time.sleep(0.1)
            safe_move(2, 35, direction)
            time.sleep(0.1)
            safe_move(3, 35, direction)
            time.sleep(0.1)
            safe_move(4, 35, direction)
            time.sleep(0.1)
    
    # Move forward for 5 seconds
    start_time = time.time()
    while time.time() - start_time < 5:
        safe_move(1, 35, 'no')
        time.sleep(0.1)
        safe_move(2, 35, 'no')
        time.sleep(0.1)
        safe_move(3, 35, 'no')
        time.sleep(0.1)
        safe_move(4, 35, 'no')
        time.sleep(0.1)
    
    # Stop
    with servo_lock:
        move.stand()

def main_sequence():
    """Main sequence that runs movement and motion detection sequentially."""
    try:
        print("Starting initial movement sequence...")
        perform_movement_sequence()
        print("Movement sequence completed.")
        
        time.sleep(2)
        
        print("Starting motion detection...")
        position = None
        while not position:
            position = detector.detect_motion()
            time.sleep(0.1)
        
        print(f"Object detected at: {position}")
        move_to_object(position)
        print("Movement to object completed.")
        
    except Exception as e:
        print(f"Error in main sequence: {e}")
        with servo_lock:
            move.clean_all()

if __name__ == '__main__':
    try:
        # Start video host (singleton ensures only one instance)
        host = VideoHost(port=5000)
        host.start()
        print("Video host started on port 5000")
        
        # Initialize motion detector
        detector = MotionDetector(host)
        
        # Start main sequence in a separate thread
        main_thread = threading.Thread(target=main_sequence)
        main_thread.daemon = True
        main_thread.start()
        
        # Keep the main thread running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        with servo_lock:
            move.clean_all()
        host.cleanup() 