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
from robotLight import RobotLight  # Direct import since server is in Python path

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
        self.is_moving = False  # Add flag to track movement state
        
    def reset_detection(self):
        """Reset the background model to start fresh detection."""
        self.avg = None
        self.last_motion = None
        self.motion_detected = False
        
    def detect_motion(self):
        """Detect motion and calculate object position relative to robot."""
        if self.is_moving:  # Skip detection if robot is moving
            return None
            
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
            time.sleep(0.2)  # Reduced from 0.5s to 0.2s for faster initialization
            return None

        # Accumulate weighted average with faster adaptation
        cv2.accumulateWeighted(gray, self.avg, 0.3)  # Increased from 0.5 to 0.3 for faster updates
        frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg))

        # Threshold and dilate with lower threshold for faster detection
        thresh = cv2.threshold(frameDelta, 3, 255, cv2.THRESH_BINARY)[1]  # Reduced threshold from 5 to 3
        thresh = cv2.dilate(thresh, None, iterations=2)

        # Find contours
        contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

        # Process largest contour with reduced area threshold
        if len(contours) > 0:
            largest_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest_contour) > 2000:  # Reduced from 5000 to 2000
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
        time.sleep(0.05)  # Add small delay between servo movements

def safe_look(direction, steps=None):
    """Thread-safe wrapper for look commands with step control."""
    with servo_lock:
        if direction == 'up':
            move.look_up(steps)
        elif direction == 'down':
            move.look_down(steps)
        elif direction == 'left':
            move.look_left(steps)
        elif direction == 'right':
            move.look_right(steps)
        elif direction == 'home':
            move.look_home()
        time.sleep(0.1)  # Add delay after head movement

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
        
    # Set moving flag
    detector.is_moving = True
    
    # Calculate turn angle needed
    turn_angle = position['angle_x']
    distance = position['distance']
    
    # Create detailed movement plan
    movement_plan = {
        'turn': {
            'angle': turn_angle,
            'direction': 'right' if turn_angle > 0 else 'left',
            'steps': min(abs(int(turn_angle / 10)), 4)
        },
        'forward': {
            'distance': distance,
            'duration': 2.0
        }
    }
    
    # Initialize position tracking
    current_position = {'x': 0, 'y': 0, 'angle': 0}
    
    # Log movement plan
    movement_info = {
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'initial_position': position,
        'movement_plan': movement_plan,
        'status': 'Calculating movement path...',
        'position': current_position
    }
    host.update_movement_info(movement_info)
    
    # Turn towards object
    if abs(turn_angle) > 5:
        direction = movement_plan['turn']['direction']
        steps = movement_plan['turn']['steps']
        
        movement_info['status'] = f"Turning {direction}: {abs(turn_angle):.1f}° in {steps} steps"
        host.update_movement_info(movement_info)
        
        for step in range(steps):
            with servo_lock:
                # Execute full step sequence atomically with reduced delays
                move.move(1, 35, direction)
                time.sleep(0.02)
                move.move(2, 35, direction)
                time.sleep(0.02)
                move.move(3, 35, direction)
                time.sleep(0.02)
                move.move(4, 35, direction)
                time.sleep(0.02)
            
            # Reduced delay between steps
            time.sleep(0.05)
            
            # Update position and progress
            current_position['angle'] += (turn_angle/steps) * (1 if direction == 'left' else -1)
            movement_info['position'] = current_position
            movement_info['status'] = f"Turn progress: {step + 1}/{steps} steps ({((step + 1)/steps * 100):.0f}%)"
            host.update_movement_info(movement_info)
    
    # Move forward
    start_time = time.time()
    step_count = 0
    
    movement_info['status'] = f"Moving forward for {movement_plan['forward']['duration']} seconds"
    host.update_movement_info(movement_info)
    
    while time.time() - start_time < 2:
        with servo_lock:
            # Execute full step sequence atomically with reduced delays
            move.move(1, 35, 'no')
            time.sleep(0.02)
            move.move(2, 35, 'no')
            time.sleep(0.02)
            move.move(3, 35, 'no')
            time.sleep(0.02)
            move.move(4, 35, 'no')
            time.sleep(0.02)
        
        # Reduced delay between steps
        time.sleep(0.05)
        
        step_count += 1
        progress = min((time.time() - start_time) / 2.0 * 100, 100)
        
        # Update position based on movement
        angle_rad = math.radians(current_position['angle'])
        step_distance = distance / 5  # Divide total distance into 5 steps
        current_position['x'] += step_distance * math.cos(angle_rad)
        current_position['y'] += step_distance * math.sin(angle_rad)
        
        movement_info['position'] = current_position
        movement_info['status'] = f"Forward progress: {progress:.0f}% ({step_count} steps)"
        host.update_movement_info(movement_info)
    
    # Stop and stand
    with servo_lock:
        move.stand()
        movement_info['status'] = "Movement complete. Standing by."
        movement_info['position'] = current_position
        host.update_movement_info(movement_info)
    
    # Reset moving flag
    detector.is_moving = False
    
    # Clear detection history after movement
    detector.last_detection_image = None
    detector.detection_info = None

def sequence_with_status():
    try:
        host.update_status("Initializing robot position...")
        initialize_robot()
        
        # Store last known position with more detail
        last_position = None
        last_head_position = None
        head_movement_info = None
        
        while True:  # Main loop
            host.update_status("Starting detection sequence...")
            
            # Detection mode - Red LED
            RL.red()
            
            # Reset motion detector for new detection sequence
            detector.reset_detection()
            
            # If we have a last position, try to look there first
            if last_position and last_head_position:
                host.update_status("Calculating head movement to last position...")
                
                # Calculate head movement
                head_movement_info = {
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'from': {
                        'x': move.Left_Right_input,
                        'y': move.Up_Down_input
                    },
                    'to': last_head_position,
                    'delta': {
                        'x': last_head_position['x'] - move.Left_Right_input,
                        'y': last_head_position['y'] - move.Up_Down_input
                    },
                    'status': 'Calculating head movement...',
                    'x': move.Left_Right_input,
                    'y': move.Up_Down_input,
                    'target': last_head_position
                }
                
                host.update_head_movement(head_movement_info)
                host.update_status("Moving head to last detected position...")
                
                with servo_lock:
                    # Move head with progress updates and reduced delays
                    if head_movement_info['delta']['x'] != 0:
                        direction = 'right' if head_movement_info['delta']['x'] > 0 else 'left'
                        steps = abs(head_movement_info['delta']['x'])
                        host.update_status(f"Adjusting head {direction} by {steps} steps...")
                        safe_look(direction, steps)
                    
                    if head_movement_info['delta']['y'] != 0:
                        direction = 'up' if head_movement_info['delta']['y'] > 0 else 'down'
                        steps = abs(head_movement_info['delta']['y'])
                        host.update_status(f"Adjusting head {direction} by {steps} steps...")
                        safe_look(direction, steps)
                    time.sleep(0.2)  # Reduced delay
            
            # Reduced delay for background model initialization
            time.sleep(0.5)
            
            position = None
            while not position and not detector.is_moving:  # Only detect when not moving
                position = detector.detect_motion()
                if position:
                    host.update_status("Motion detected! Moving to target...")
                    
                    # Store current head position before moving
                    with servo_lock:
                        last_head_position = {
                            'x': move.Left_Right_input,
                            'y': move.Up_Down_input
                        }
                    last_position = position
                    
                    # Movement mode - Blue LED
                    RL.blue()
                    
                    # Move towards object
                    move_to_object(position)
                    
                    # Turn off LEDs after sequence
                    RL.both_off()
                    
                    # Reduced delay before next detection
                    time.sleep(0.5)
                    break
                
                time.sleep(0.05)  # Reduced delay between detection attempts
            
    except Exception as e:
        error_msg = f"Error in main sequence: {e}"
        print(error_msg)
        host.update_status(error_msg)
        RL.both_off()  # Ensure LEDs are off even if error occurs
        with servo_lock:
            move.clean_all()
    finally:
        RL.pause()  # Clean up LED thread

if __name__ == '__main__':
    try:
        # Start video host (singleton ensures only one instance)
        host = VideoHost(port=5000, debug=True)
        
        # Initialize LED control first
        RL = RobotLight()
        RL.start()
        RL.both_off()  # Start with LEDs off
        
        # Initialize camera first
        host.update_status("Initializing camera...")
        if not host.init_camera():
            print("Failed to initialize camera. Exiting...")
            RL.both_off()
            sys.exit(1)
            
        print("Camera initialized successfully")
        
        # Initialize motion detector with the camera instance
        host.update_status("Initializing motion detector...")
        detector = MotionDetector(host)
        
        # Set detector in video host for status updates
        host.set_detector(detector)
        
        # Start the server
        host.start()
        print("Video host started on port 5000")
        
        # Update status
        host.update_status("Server initialized, starting main sequence...")
        
        # Start main sequence in a separate thread
        main_thread = threading.Thread(target=sequence_with_status)
        main_thread.daemon = True
        main_thread.start()

        # Indicate system is ready with green LED
        RL.green()
        host.update_status("System ready - Motion detection active")
        
        # Keep the main thread running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        host.update_status("Shutting down...")
        with servo_lock:
            move.clean_all()
        RL.both_off()
        host.cleanup()
    except Exception as e:
        print(f"\nError during startup: {e}")
        if 'RL' in locals():
            RL.both_off()
        if 'host' in locals():
            host.cleanup()
        sys.exit(1) 