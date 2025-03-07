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
                        background-color: #000;
                    }
                    .video-feed {
                        width: 100%;
                        border-radius: 5px;
                        display: block;
                    }
                    #videoOverlay {
                        position: absolute;
                        top: 0;
                        left: 0;
                        pointer-events: none;
                        z-index: 10;
                    }
                    .overlay-info {
                        position: absolute;
                        top: 10px;
                        left: 10px;
                        background: rgba(0,0,0,0.7);
                        padding: 10px;
                        border-radius: 5px;
                        font-family: monospace;
                        color: #00ff00;
                        z-index: 20;
                    }
                    .target-indicator {
                        position: absolute;
                        border: 2px solid #00ff00;
                        border-radius: 50%;
                        pointer-events: none;
                        z-index: 15;
                        transform: translate(-50%, -50%);
                    }
                    .vector-info {
                        position: absolute;
                        background: rgba(0,0,0,0.7);
                        color: #00ff00;
                        padding: 5px;
                        border-radius: 3px;
                        font-size: 12px;
                        font-family: monospace;
                        z-index: 20;
                    }
                    .detection-grid {
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 10px;
                        margin-top: 10px;
                    }
                    .stat-box {
                        background: #363636;
                        padding: 15px;
                        border-radius: 5px;
                        margin-top: 10px;
                    }
                    .stat-title {
                        color: #888;
                        font-size: 12px;
                        margin-bottom: 5px;
                    }
                    .stat-value {
                        color: #00ff00;
                        font-size: 18px;
                        font-family: monospace;
                    }
                    .stat-unit {
                        color: #666;
                        font-size: 12px;
                        margin-left: 5px;
                    }
                    .compass {
                        width: 150px;
                        height: 150px;
                        border-radius: 50%;
                        background: #363636;
                        position: relative;
                        margin: 20px auto;
                    }
                    .compass-arrow {
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        width: 4px;
                        height: 60px;
                        background: #00ff00;
                        transform-origin: bottom center;
                        transform: translate(-50%, -100%);
                    }
                    .compass-labels {
                        position: absolute;
                        width: 100%;
                        height: 100%;
                        top: 0;
                        left: 0;
                    }
                    .compass-label {
                        position: absolute;
                        color: #888;
                        font-size: 12px;
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
                    let lastFrameCenter = null;
                    let lastObjectCenter = null;

                    function updateOverlay(data) {
                        const wrapper = document.querySelector('.video-wrapper');
                        const video = document.querySelector('.video-feed');
                        const canvas = document.getElementById('videoOverlay');
                        
                        // Match canvas size to video
                        canvas.width = video.offsetWidth;
                        canvas.height = video.offsetHeight;
                        
                        const ctx = canvas.getContext('2d');
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        
                        if (data.detection_info) {
                            const info = data.detection_info;
                            const pos = info.position;
                            const center = info.center;
                            const frameCenter = info.frame_center;
                            
                            // Scale coordinates to match video size
                            const scaleX = canvas.width / frameCenter.x / 2;
                            const scaleY = canvas.height / frameCenter.y / 2;
                            
                            const scaledCenter = {
                                x: center.x * scaleX,
                                y: center.y * scaleY
                            };
                            
                            const scaledFrameCenter = {
                                x: frameCenter.x * scaleX,
                                y: frameCenter.y * scaleY
                            };
                            
                            // Draw targeting reticle
                            ctx.strokeStyle = '#00ff00';
                            ctx.lineWidth = 2;
                            
                            // Outer circle
                            ctx.beginPath();
                            ctx.arc(scaledCenter.x, scaledCenter.y, 30, 0, Math.PI * 2);
                            ctx.stroke();
                            
                            // Cross lines
                            ctx.beginPath();
                            ctx.moveTo(scaledCenter.x - 40, scaledCenter.y);
                            ctx.lineTo(scaledCenter.x + 40, scaledCenter.y);
                            ctx.moveTo(scaledCenter.x, scaledCenter.y - 40);
                            ctx.lineTo(scaledCenter.x, scaledCenter.y + 40);
                            ctx.stroke();
                            
                            // Draw vector from center to object
                            ctx.beginPath();
                            ctx.setLineDash([5, 5]);
                            ctx.moveTo(scaledFrameCenter.x, scaledFrameCenter.y);
                            ctx.lineTo(scaledCenter.x, scaledCenter.y);
                            ctx.stroke();
                            ctx.setLineDash([]);
                            
                            // Draw direction arrow
                            const angle = Math.atan2(scaledCenter.y - scaledFrameCenter.y, 
                                                   scaledCenter.x - scaledFrameCenter.x);
                            const arrowLength = 20;
                            
                            ctx.beginPath();
                            ctx.moveTo(scaledCenter.x, scaledCenter.y);
                            ctx.lineTo(scaledCenter.x - arrowLength * Math.cos(angle - Math.PI/6),
                                     scaledCenter.y - arrowLength * Math.sin(angle - Math.PI/6));
                            ctx.lineTo(scaledCenter.x - arrowLength * Math.cos(angle + Math.PI/6),
                                     scaledCenter.y - arrowLength * Math.sin(angle + Math.PI/6));
                            ctx.closePath();
                            ctx.fillStyle = '#00ff00';
                            ctx.fill();
                            
                            // Update compass
                            updateCompass(pos.angle_x);
                            
                            // Update stats
                            updateStats(info);
                            
                            // Save centers for animation
                            lastFrameCenter = scaledFrameCenter;
                            lastObjectCenter = scaledCenter;
                        }
                        
                        // Draw scanning effect
                        drawScanningEffect(ctx, canvas.width, canvas.height);
                    }
                    
                    function drawScanningEffect(ctx, width, height) {
                        const time = Date.now() / 1000;
                        const scanLineY = (Math.sin(time) + 1) * height / 2;
                        
                        ctx.strokeStyle = 'rgba(0, 255, 0, 0.2)';
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(0, scanLineY);
                        ctx.lineTo(width, scanLineY);
                        ctx.stroke();
                        
                        // Add scan line glow
                        const gradient = ctx.createLinearGradient(0, scanLineY - 10, 0, scanLineY + 10);
                        gradient.addColorStop(0, 'rgba(0, 255, 0, 0)');
                        gradient.addColorStop(0.5, 'rgba(0, 255, 0, 0.1)');
                        gradient.addColorStop(1, 'rgba(0, 255, 0, 0)');
                        
                        ctx.fillStyle = gradient;
                        ctx.fillRect(0, scanLineY - 10, width, 20);
                    }
                    
                    function updateCompass(angle) {
                        const compass = document.querySelector('.compass-arrow');
                        if (compass) {
                            compass.style.transform = `translate(-50%, -100%) rotate(${angle}deg)`;
                        }
                    }
                    
                    function updateStats(info) {
                        const stats = document.getElementById('statsContainer');
                        if (stats) {
                            stats.innerHTML = `
                                <div class="stat-box">
                                    <div class="stat-title">Distance</div>
                                    <div class="stat-value">
                                        ${info.position.distance.toFixed(2)}
                                        <span class="stat-unit">units</span>
                                    </div>
                                </div>
                                <div class="stat-box">
                                    <div class="stat-title">Angle X</div>
                                    <div class="stat-value">
                                        ${info.position.angle_x.toFixed(2)}
                                        <span class="stat-unit">degrees</span>
                                    </div>
                                </div>
                                <div class="stat-box">
                                    <div class="stat-title">Angle Y</div>
                                    <div class="stat-value">
                                        ${info.position.angle_y.toFixed(2)}
                                        <span class="stat-unit">degrees</span>
                                    </div>
                                </div>
                                <div class="stat-box">
                                    <div class="stat-title">Object Size</div>
                                    <div class="stat-value">
                                        ${info.object_size.width}x${info.object_size.height}
                                        <span class="stat-unit">px</span>
                                    </div>
                                </div>
                            `;
                        }
                    }

                    function updateStatus() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('processStatus').innerText = data.status;
                                
                                if (data.detection_info) {
                                    updateOverlay(data);
                                    
                                    if (data.last_detection_image) {
                                        const imgData = {
                                            image: data.last_detection_image,
                                            timestamp: data.detection_info.timestamp,
                                            info: data.detection_info
                                        };
                                        
                                        if (!detectionHistory.length || 
                                            detectionHistory[detectionHistory.length-1].timestamp !== imgData.timestamp) {
                                            detectionHistory.push(imgData);
                                            if (detectionHistory.length > MAX_HISTORY) {
                                                detectionHistory.shift();
                                            }
                                            updateDetectionHistory();
                                        }
                                        
                                        document.getElementById('mainDetectionImage').src = 
                                            'data:image/jpeg;base64,' + data.last_detection_image;
                                        document.getElementById('mainDetectionImage').style.display = 'block';
                                        document.getElementById('detectionTimestamp').innerText = 
                                            data.detection_info.timestamp;
                                    }
                                }
                            });
                    }
                    
                    // Update status every 100ms for smoother animation
                    setInterval(updateStatus, 100);
                    
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
                        
                        // Initial resize
                        resizeOverlay();
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
                            <div class="overlay-info">
                                <div id="scanStatus">Scanning...</div>
                            </div>
                        </div>
                        <div class="compass">
                            <div class="compass-arrow"></div>
                            <div class="compass-labels">
                                <div class="compass-label" style="top: 5px; left: 50%; transform: translateX(-50%);">0°</div>
                                <div class="compass-label" style="top: 50%; right: 5px; transform: translateY(-50%);">90°</div>
                                <div class="compass-label" style="bottom: 5px; left: 50%; transform: translateX(-50%);">180°</div>
                                <div class="compass-label" style="top: 50%; left: 5px; transform: translateY(-50%);">-90°</div>
                            </div>
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
                            <h2>Detection Stats</h2>
                            <div id="statsContainer"></div>
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