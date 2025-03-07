#!/usr/bin/env python3
import os
import sys
import threading
import json
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
                        margin: 0;
                        padding: 20px;
                    }
                    .container {
                        display: flex;
                        gap: 20px;
                        max-width: 1200px;
                        margin: 0 auto;
                    }
                    .video-container {
                        flex: 1;
                        background-color: white;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    }
                    .info-container {
                        flex: 1;
                        background-color: white;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    }
                    h1, h2 {
                        color: #333;
                        margin-top: 0;
                    }
                    img {
                        max-width: 100%;
                        border-radius: 5px;
                    }
                    .status {
                        padding: 10px;
                        margin: 5px 0;
                        border-radius: 5px;
                        background-color: #f8f9fa;
                    }
                    .detection-info {
                        margin-top: 20px;
                    }
                    .detection-image {
                        margin-top: 10px;
                        max-width: 320px;
                        border: 1px solid #ddd;
                    }
                    #processStatus {
                        font-family: monospace;
                        white-space: pre-wrap;
                    }
                </style>
                <script>
                    function updateStatus() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('processStatus').innerText = data.status;
                                if (data.detection_info) {
                                    document.getElementById('detectionInfo').innerHTML = 
                                        '<h3>Detection Details:</h3>' +
                                        '<p>Time: ' + data.detection_info.timestamp + '</p>' +
                                        '<p>Position: ' + JSON.stringify(data.detection_info.position, null, 2) + '</p>' +
                                        '<p>Object Size: ' + JSON.stringify(data.detection_info.object_size, null, 2) + '</p>' +
                                        '<p>Center: ' + JSON.stringify(data.detection_info.center, null, 2) + '</p>';
                                    
                                    if (data.last_detection_image) {
                                        document.getElementById('detectionImage').src = 
                                            'data:image/jpeg;base64,' + data.last_detection_image;
                                        document.getElementById('detectionImage').style.display = 'block';
                                    }
                                }
                            });
                    }
                    
                    // Update status every second
                    setInterval(updateStatus, 1000);
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="video-container">
                        <h1>Live Camera Feed</h1>
                        <img src="/video_feed">
                    </div>
                    <div class="info-container">
                        <h2>Process Status</h2>
                        <div id="processStatus" class="status">
                            Initializing...
                        </div>
                        <div class="detection-info">
                            <div id="detectionInfo"></div>
                            <img id="detectionImage" class="detection-image" style="display: none;">
                        </div>
                    </div>
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
    
    def get_status(self):
        """Get current process status and detection information."""
        if hasattr(self, 'detector'):
            return {
                'status': self.current_status,
                'detection_info': self.detector.detection_info,
                'last_detection_image': self.detector.last_detection_image
            }
        return {'status': 'Initializing...'}
    
    def set_detector(self, detector):
        """Set the motion detector instance for status updates."""
        self.detector = detector
        
    def update_status(self, status):
        """Update the current process status."""
        self.current_status = status

    def start(self):
        """Start the video hosting server in a separate thread."""
        # Add status route
        @self.app.route('/status')
        def get_status_route():
            status_data = self.get_status()
            return Response(
                json.dumps(status_data),
                mimetype='application/json'
            )
        
        def run_server():
            self.app.run(host='0.0.0.0', port=self.port, threaded=True)
            
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        # Initialize status
        self.current_status = "Server started"
    
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