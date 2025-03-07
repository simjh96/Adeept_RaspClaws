#!/usr/bin/env python3
import os
import sys
import threading
from flask import Flask, Response
from flask_cors import CORS

# Add server directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

# Import server modules
from camera_opencv import Camera

class VideoHost:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """Ensure only one instance of VideoHost exists (Singleton pattern)"""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(VideoHost, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, port=5000):
        if not hasattr(self, 'initialized'):
            self.app = Flask(__name__)
            CORS(self.app, supports_credentials=True)
            self.camera = None
            self.port = port
            self.camera_lock = threading.Lock()
            
            # Register routes
            self.app.route('/')(self.index)
            self.app.route('/video_feed')(self.video_feed)
            self.initialized = True
    
    def init_camera(self):
        """Initialize camera with lock to prevent conflicts"""
        with self.camera_lock:
            if self.camera is None:
                try:
                    self.camera = Camera()
                except Exception as e:
                    print(f"Error initializing camera: {e}")
                    return False
            return True
        
    def gen(self):
        """Video streaming generator function."""
        if not self.init_camera():
            return
            
        while True:
            with self.camera_lock:
                try:
                    frame = self.camera.get_frame()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                except Exception as e:
                    print(f"Error getting frame: {e}")
                    break

    def index(self):
        """Video streaming home page."""
        return """
        <html>
            <head>
                <title>Robot Camera Stream</title>
                <style>
                    body {
                        background-color: #f0f0f0;
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                    }
                    .container {
                        text-align: center;
                        background-color: white;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    }
                    h1 {
                        color: #333;
                    }
                    img {
                        max-width: 100%;
                        border-radius: 5px;
                        margin-top: 20px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Robot Camera Stream</h1>
                    <img src="/video_feed">
                </div>
            </body>
        </html>
        """

    def video_feed(self):
        """Video streaming route."""
        return Response(self.gen(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def get_frame_safe(self):
        """Thread-safe method to get a frame."""
        if not self.init_camera():
            return None
            
        with self.camera_lock:
            try:
                return self.camera.get_frame()
            except Exception as e:
                print(f"Error getting frame: {e}")
                return None
    
    def start(self):
        """Start the video hosting server in a separate thread."""
        def run_server():
            self.app.run(host='0.0.0.0', port=self.port, threaded=True)
            
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
    
    def cleanup(self):
        """Clean up camera resources."""
        with self.camera_lock:
            if self.camera:
                # Add any necessary camera cleanup here
                self.camera = None

if __name__ == '__main__':
    # Test the video host independently
    host = VideoHost()
    host.start()
    try:
        while True:
            pass  # Keep the main thread running
    except KeyboardInterrupt:
        print("\nShutting down...")
        host.cleanup() 