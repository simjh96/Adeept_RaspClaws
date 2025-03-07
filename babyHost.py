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
                        background-color: #1a1a1a;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        color: #fff;
                    }
                    .container {
                        display: flex;
                        gap: 20px;
                        max-width: 1400px;
                        margin: 0 auto;
                    }
                    .video-container {
                        flex: 1.5;
                        background-color: #2d2d2d;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                    }
                    .info-container {
                        flex: 1;
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                    }
                    .status-box, .detection-box {
                        background-color: #2d2d2d;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                    }
                    h1, h2 {
                        color: #fff;
                        margin-top: 0;
                        border-bottom: 2px solid #444;
                        padding-bottom: 10px;
                    }
                    .video-wrapper {
                        position: relative;
                        width: 100%;
                        margin-top: 10px;
                    }
                    .video-feed {
                        width: 100%;
                        border-radius: 5px;
                    }
                    #videoOverlay {
                        position: absolute;
                        top: 0;
                        left: 0;
                        pointer-events: none;
                    }
                    .status {
                        padding: 10px;
                        margin: 5px 0;
                        border-radius: 5px;
                        background-color: #363636;
                        color: #00ff00;
                        font-family: monospace;
                        font-size: 14px;
                    }
                    .detection-info {
                        margin-top: 20px;
                    }
                    .detection-grid {
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 10px;
                        margin-top: 10px;
                    }
                    .detection-cell {
                        background-color: #363636;
                        padding: 10px;
                        border-radius: 5px;
                    }
                    .detection-label {
                        color: #888;
                        font-size: 12px;
                        margin-bottom: 5px;
                    }
                    .detection-value {
                        color: #00ff00;
                        font-family: monospace;
                        font-size: 14px;
                    }
                    .detection-image-container {
                        margin-top: 20px;
                        position: relative;
                    }
                    .detection-image {
                        width: 100%;
                        border-radius: 5px;
                        border: 2px solid #444;
                    }
                    .detection-timestamp {
                        position: absolute;
                        bottom: 10px;
                        right: 10px;
                        background-color: rgba(0,0,0,0.7);
                        color: #fff;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-size: 12px;
                    }
                    .history-container {
                        display: flex;
                        gap: 10px;
                        overflow-x: auto;
                        padding: 10px 0;
                    }
                    .history-image {
                        width: 120px;
                        height: 90px;
                        object-fit: cover;
                        border-radius: 5px;
                        border: 2px solid #444;
                        cursor: pointer;
                        transition: border-color 0.3s;
                    }
                    .history-image:hover {
                        border-color: #00ff00;
                    }
                </style>
                <script>
                    let detectionHistory = [];
                    const MAX_HISTORY = 5;

                    function updateOverlay(data) {
                        const canvas = document.getElementById('videoOverlay');
                        const ctx = canvas.getContext('2d');
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        
                        if (data.detection_info) {
                            const pos = data.detection_info.position;
                            const center = data.detection_info.center;
                            const frameCenter = data.detection_info.frame_center;
                            
                            // Draw direction arrow
                            ctx.strokeStyle = '#00ff00';
                            ctx.lineWidth = 2;
                            ctx.beginPath();
                            ctx.moveTo(frameCenter.x, frameCenter.y);
                            ctx.lineTo(center.x, center.y);
                            ctx.stroke();
                            
                            // Draw arrowhead
                            const angle = Math.atan2(center.y - frameCenter.y, center.x - frameCenter.x);
                            ctx.beginPath();
                            ctx.moveTo(center.x, center.y);
                            ctx.lineTo(center.x - 15 * Math.cos(angle - Math.PI/6), 
                                     center.y - 15 * Math.sin(angle - Math.PI/6));
                            ctx.lineTo(center.x - 15 * Math.cos(angle + Math.PI/6),
                                     center.y - 15 * Math.sin(angle + Math.PI/6));
                            ctx.closePath();
                            ctx.fillStyle = '#00ff00';
                            ctx.fill();
                            
                            // Add distance indicator
                            ctx.font = '14px monospace';
                            ctx.fillStyle = '#00ff00';
                            ctx.fillText(`Distance: ${pos.distance.toFixed(2)}`, 10, 20);
                            ctx.fillText(`Angle X: ${pos.angle_x.toFixed(2)}°`, 10, 40);
                            ctx.fillText(`Angle Y: ${pos.angle_y.toFixed(2)}°`, 10, 60);
                        }
                    }

                    function updateStatus() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                // Update status
                                document.getElementById('processStatus').innerText = data.status;
                                
                                if (data.detection_info) {
                                    // Update detection info grid
                                    const info = data.detection_info;
                                    document.getElementById('detectionInfo').innerHTML = `
                                        <div class="detection-grid">
                                            <div class="detection-cell">
                                                <div class="detection-label">Angle X</div>
                                                <div class="detection-value">${info.position.angle_x.toFixed(2)}°</div>
                                            </div>
                                            <div class="detection-cell">
                                                <div class="detection-label">Angle Y</div>
                                                <div class="detection-value">${info.position.angle_y.toFixed(2)}°</div>
                                            </div>
                                            <div class="detection-cell">
                                                <div class="detection-label">Distance</div>
                                                <div class="detection-value">${info.position.distance.toFixed(2)}</div>
                                            </div>
                                            <div class="detection-cell">
                                                <div class="detection-label">Object Size</div>
                                                <div class="detection-value">${info.object_size.width}x${info.object_size.height}</div>
                                            </div>
                                        </div>
                                    `;
                                    
                                    // Update detection image
                                    if (data.last_detection_image) {
                                        const imgData = {
                                            image: data.last_detection_image,
                                            timestamp: info.timestamp,
                                            info: info
                                        };
                                        
                                        // Add to history if it's a new detection
                                        if (!detectionHistory.length || 
                                            detectionHistory[detectionHistory.length-1].timestamp !== info.timestamp) {
                                            detectionHistory.push(imgData);
                                            if (detectionHistory.length > MAX_HISTORY) {
                                                detectionHistory.shift();
                                            }
                                            updateDetectionHistory();
                                        }
                                        
                                        document.getElementById('mainDetectionImage').src = 
                                            'data:image/jpeg;base64,' + data.last_detection_image;
                                        document.getElementById('mainDetectionImage').style.display = 'block';
                                        document.getElementById('detectionTimestamp').innerText = info.timestamp;
                                    }
                                }
                            });
                    }
                    
                    function updateDetectionHistory() {
                        const container = document.getElementById('historyContainer');
                        container.innerHTML = detectionHistory.map((item, index) => `
                            <img src="data:image/jpeg;base64,${item.image}" 
                                 class="history-image" 
                                 onclick="showHistoryDetail(${index})"
                                 title="${item.timestamp}">
                        `).join('');
                    }
                    
                    function showHistoryDetail(index) {
                        const item = detectionHistory[index];
                        document.getElementById('mainDetectionImage').src = 
                            'data:image/jpeg;base64,' + item.image;
                        document.getElementById('detectionTimestamp').innerText = item.timestamp;
                        
                        // Update detection info grid with historical data
                        const info = item.info;
                        document.getElementById('detectionInfo').innerHTML = `
                            <div class="detection-grid">
                                <div class="detection-cell">
                                    <div class="detection-label">Angle X</div>
                                    <div class="detection-value">${info.position.angle_x.toFixed(2)}°</div>
                                </div>
                                <div class="detection-cell">
                                    <div class="detection-label">Angle Y</div>
                                    <div class="detection-value">${info.position.angle_y.toFixed(2)}°</div>
                                </div>
                                <div class="detection-cell">
                                    <div class="detection-label">Distance</div>
                                    <div class="detection-value">${info.position.distance.toFixed(2)}</div>
                                </div>
                                <div class="detection-cell">
                                    <div class="detection-label">Object Size</div>
                                    <div class="detection-value">${info.object_size.width}x${info.object_size.height}</div>
                                </div>
                            </div>
                        `;
                    }
                    
                    // Update status every second
                    setInterval(updateStatus, 1000);
                    
                    // Initialize video overlay when page loads
                    window.onload = function() {
                        const video = document.querySelector('.video-feed');
                        const canvas = document.getElementById('videoOverlay');
                        
                        function resizeOverlay() {
                            canvas.width = video.offsetWidth;
                            canvas.height = video.offsetHeight;
                        }
                        
                        // Resize overlay when video size changes
                        new ResizeObserver(resizeOverlay).observe(video);
                    }
                </script>
            </head>
            <body>
                <div class="container">
                    <div class="video-container">
                        <h1>Live Camera Feed</h1>
                        <div class="video-wrapper">
                            <img class="video-feed" src="/video_feed">
                            <canvas id="videoOverlay"></canvas>
                        </div>
                    </div>
                    <div class="info-container">
                        <div class="status-box">
                            <h2>Process Status</h2>
                            <div id="processStatus" class="status">
                                Initializing...
                            </div>
                        </div>
                        <div class="detection-box">
                            <h2>Detection Details</h2>
                            <div id="detectionInfo"></div>
                            <div class="detection-image-container">
                                <img id="mainDetectionImage" class="detection-image" style="display: none;">
                                <div id="detectionTimestamp" class="detection-timestamp"></div>
                            </div>
                            <h2>Detection History</h2>
                            <div id="historyContainer" class="history-container"></div>
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