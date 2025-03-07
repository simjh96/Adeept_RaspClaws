#!/usr/bin/env python3
import os
import sys
import time
import threading
import math
import datetime
import cv2
import numpy as np
import base64  # Add base64 import

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
        self.last_detection_image = None
        self.detection_info = None
        
    def reset_detection(self):
        """Reset the background model to start fresh detection."""
        self.avg = None
        self.last_motion = None
        self.motion_detected = False
        
    def detect_motion(self):
        """Detect motion and calculate object position relative to robot."""
        frame = self.camera.get_frame_safe()
        if frame is None:
            return None
            
        # Convert bytes to numpy array
        nparr = np.frombuffer(frame, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            print("Failed to decode image")
            return None
            
        # Make a copy for drawing
        display_img = img.copy()
            
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
                
                # Draw rectangle and center point on the display image
                cv2.rectangle(display_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(display_img, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Calculate relative position from center of frame
                frame_center_x = display_img.shape[1] // 2
                frame_center_y = display_img.shape[0] // 2
                
                # Draw vector from center to object
                cv2.line(display_img, 
                        (frame_center_x, frame_center_y),
                        (center_x, center_y),
                        (0, 255, 0), 2)
                
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
                
                # Save detection information with base64 encoded image
                _, buffer = cv2.imencode('.jpg', display_img)
                self.last_detection_image = base64.b64encode(buffer).decode('utf-8')
                self.detection_info = {
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'position': self.object_position,
                    'object_size': {'width': w, 'height': h},
                    'center': {'x': center_x, 'y': center_y},
                    'frame_center': {'x': frame_center_x, 'y': frame_center_y}
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

def initialize_robot():
    """Initialize robot's legs and camera position."""
    print("Initializing robot position...")
    with servo_lock:
        move.clean_all()  # Reset all servos
        time.sleep(1)
        move.init_all()   # Initialize to standing position
        time.sleep(1)
        move.look_home()  # Center the camera
        time.sleep(1)
    print("Robot initialized.")

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
            # Check right leg (leg 2) movement
            with servo_lock:
                move.move(1, 35, direction)
                time.sleep(0.1)
                try:
                    move.move(2, 35, direction)  # Add extra error handling for right leg
                except Exception as e:
                    print(f"Error moving right leg: {e}")
                time.sleep(0.1)
                move.move(3, 35, direction)
                time.sleep(0.1)
                move.move(4, 35, direction)
                time.sleep(0.1)
    
    # Move forward for exactly 2 seconds
    start_time = time.time()
    while time.time() - start_time < 2:
        with servo_lock:
            move.move(1, 35, 'no')
            time.sleep(0.1)
            try:
                move.move(2, 35, 'no')  # Add extra error handling for right leg
            except Exception as e:
                print(f"Error moving right leg: {e}")
            time.sleep(0.1)
            move.move(3, 35, 'no')
            time.sleep(0.1)
            move.move(4, 35, 'no')
            time.sleep(0.1)
    
    # Stop and stand
    with servo_lock:
        move.stand()

def sequence_with_status():
    try:
        host.update_status("Initializing robot position...")
        initialize_robot()
        
        # Store last known position
        last_position = None
        last_head_position = None
        
        while True:  # Main loop
            host.update_status("Starting detection sequence...")
            
            # Turn on red LED for detection mode
            LED.setup()  # Initialize LED
            LED.ledIndex(0, 255, 0, 0)  # Red LED for detection
            LED.ledIndex(1, 0, 0, 0)    # Turn off second LED
            
            # Reset motion detector for new detection sequence
            detector.reset_detection()
            
            # If we have a last position, try to look there first
            if last_position and last_head_position:
                host.update_status("Returning to last detected position...")
                with servo_lock:
                    # Restore head position
                    move.move_head(last_head_position['x'], last_head_position['y'])
                    time.sleep(0.5)
            
            # Wait for background model to initialize
            time.sleep(1)
            
            position = None
            while not position:  # Detection loop
                position = detector.detect_motion()
                if position:
                    host.update_status("Motion detected! Moving to target...")
                    
                    # Store current head position before moving
                    with servo_lock:
                        last_head_position = {
                            'x': move.get_head_x(),
                            'y': move.get_head_y()
                        }
                    last_position = position
                    
                    # Turn on blue LED for movement
                    LED.ledIndex(0, 0, 0, 255)  # Blue LED for movement
                    LED.ledIndex(1, 0, 0, 0)    # Turn off second LED
                    
                    # Move towards object for 2 seconds
                    move_to_object(position)
                    
                    # Turn off LEDs
                    LED.ledIndex(0, 0, 0, 0)
                    LED.ledIndex(1, 0, 0, 0)
                    
                    # Wait before starting next detection
                    time.sleep(1)
                    break  # Break detection loop to start new sequence
                
                time.sleep(0.1)  # Small delay between detection attempts
            
    except Exception as e:
        error_msg = f"Error in main sequence: {e}"
        print(error_msg)
        host.update_status(error_msg)
        # Turn off LEDs safely
        try:
            LED.ledIndex(0, 0, 0, 0)
            LED.ledIndex(1, 0, 0, 0)
        except:
            pass
        with servo_lock:
            move.clean_all()

if __name__ == '__main__':
    try:
        # Start video host (singleton ensures only one instance)
        host = VideoHost(port=5000)
        
        # Initialize camera first
        if not host.init_camera():
            print("Failed to initialize camera. Exiting...")
            sys.exit(1)
            
        print("Camera initialized successfully")
        
        # Initialize motion detector with the camera instance
        detector = MotionDetector(host)
        
        # Set detector in video host for status updates
        host.set_detector(detector)
        
        # Start the server
        host.start()
        print("Video host started on port 5000")
        
        # Update status
        host.update_status("Server initialized, waiting to start main sequence...")
        
        # Start main sequence in a separate thread
        main_thread = threading.Thread(target=sequence_with_status)
        main_thread.daemon = True
        main_thread.start()
        
        # Keep the main thread running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        host.update_status("Shutting down...")
        with servo_lock:
            move.clean_all()
        host.cleanup()
    except Exception as e:
        print(f"\nError during startup: {e}")
        if 'host' in locals():
            host.cleanup()
        sys.exit(1) 