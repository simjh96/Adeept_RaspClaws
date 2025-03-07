#!/usr/bin/env python3
import os
import sys
import threading
import json
from flask import Flask, Response, jsonify
from flask_cors import CORS
from datetime import datetime
import time

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
            self.app.route('/status')(self.get_status)
            self.initialized = True
    
    def init_camera(self):
        """Initialize camera with lock to prevent conflicts"""
        with self.camera_lock:
            if self.camera is None:
                try:
                    self.camera = Camera()
                    # Test camera capture
                    test_frame = self.camera.get_frame()
                    if test_frame is None:
                        print("Warning: Camera initialization succeeded but no frames captured")
                        return False
                    return True
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
        video_feed_url = '/video_feed'  # Direct URL instead of template
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
                        display: grid;
                        grid-template-columns: 2fr 1fr;
                        gap: 20px;
                        padding: 20px;
                        background: #1a1a1a;
                        color: #fff;
                    }
                    .video-section {
                        position: relative;
                    }
                    .video-wrapper {
                        position: relative;
                        width: 100%;
                    }
                    .video-feed {
                        width: 100%;
                        height: auto;
                    }
                    #videoOverlay {
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        pointer-events: none;
                    }
                    .detection-section {
                        display: flex;
                        flex-direction: column;
                        gap: 20px;
                        max-height: 100vh;
                        overflow-y: auto;
                    }
                    .main-detection {
                        background: #2a2a2a;
                        padding: 10px;
                        border-radius: 5px;
                    }
                    #mainDetectionImage {
                        width: 100%;
                        height: auto;
                        border-radius: 3px;
                    }
                    #detectionTimestamp {
                        display: block;
                        text-align: center;
                        margin-top: 10px;
                        color: #888;
                    }
                    .history-section {
                        background: #2a2a2a;
                        padding: 15px;
                        border-radius: 5px;
                    }
                    .history-title {
                        font-size: 16px;
                        margin-bottom: 10px;
                        color: #00ff00;
                    }
                    .history-grid {
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 15px;
                    }
                    .history-item {
                        background: #1a1a1a;
                        padding: 10px;
                        border-radius: 5px;
                    }
                    .history-image {
                        width: 100%;
                        height: auto;
                        border-radius: 3px;
                        margin-bottom: 10px;
                    }
                    .history-info {
                        font-size: 14px;
                        color: #888;
                    }
                    .stats-overlay {
                        position: absolute;
                        top: 10px;
                        left: 10px;
                        background: rgba(0, 0, 0, 0.7);
                        padding: 10px;
                        border-radius: 5px;
                        color: #00ff00;
                        font-family: monospace;
                        pointer-events: none;
                    }
                    .stat-row {
                        display: flex;
                        justify-content: space-between;
                        margin-bottom: 5px;
                    }
                    .stat-label {
                        margin-right: 10px;
                        color: #888;
                    }
                    .stat-value {
                        color: #00ff00;
                    }
                    .compass-container {
                        position: absolute;
                        bottom: 20px;
                        right: 20px;
                        width: 100px;
                        height: 100px;
                    }
                    .compass {
                        width: 100%;
                        height: 100%;
                        border-radius: 50%;
                        border: 2px solid #00ff00;
                        position: relative;
                        background: rgba(0, 0, 0, 0.5);
                    }
                    .compass-arrow {
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        width: 4px;
                        height: 40px;
                        background: #00ff00;
                        transform-origin: bottom center;
                        transform: translate(-50%, -100%);
                    }
                    .compass-labels span {
                        position: absolute;
                        color: #00ff00;
                        font-size: 12px;
                    }
                    .compass-n { top: 5px; left: 50%; transform: translateX(-50%); }
                    .compass-e { right: 5px; top: 50%; transform: translateY(-50%); }
                    .compass-s { bottom: 5px; left: 50%; transform: translateX(-50%); }
                    .compass-w { left: 5px; top: 50%; transform: translateY(-50%); }
                    .history-canvas-container {
                        position: relative;
                        width: 100%;
                        margin-bottom: 10px;
                    }
                    .history-timestamp {
                        font-size: 14px;
                        color: #00ff00;
                        margin-bottom: 5px;
                    }
                    .history-stat {
                        font-size: 12px;
                        color: #888;
                        margin: 2px 0;
                    }
                    .history-item {
                        background: #2a2a2a;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 15px;
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
                        
                        // Draw scanning effect
                        drawScanningEffect(ctx, canvas.width, canvas.height);
                        
                        if (data.detection_info) {
                            drawDetectionOverlay(ctx, data.detection_info, canvas.width, canvas.height);
                        }
                    }
                    
                    function drawDetectionOverlay(ctx, info, width, height) {
                        const pos = info.position;
                        const center = info.center;
                        const frameCenter = info.frame_center;
                        
                        // Scale coordinates to match video size
                        const scaleX = width / frameCenter.x / 2;
                        const scaleY = height / frameCenter.y / 2;
                        
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
                        updateLiveStats(info);
                        
                        return {
                            scaledCenter,
                            scaledFrameCenter,
                            angle
                        };
                    }

                    function updateDetectionHistory(newDetection) {
                        // Create history item with timestamp
                        const historyItem = {
                            ...newDetection,
                            timestamp: new Date().toISOString(),
                            overlayData: {
                                position: newDetection.info.position,
                                center: newDetection.info.center,
                                frame_center: newDetection.info.frame_center
                            }
                        };
                        
                        // Add to history array
                        detectionHistory.unshift(historyItem);
                        if (detectionHistory.length > MAX_HISTORY) {
                            detectionHistory.pop();
                        }
                        
                        // Update history display
                        const container = document.querySelector('.history-grid');
                        if (!container) return;
                        
                        container.innerHTML = detectionHistory.map((item, index) => `
                            <div class="history-item">
                                <div class="history-timestamp">${new Date(item.timestamp).toLocaleTimeString()}</div>
                                <div class="history-canvas-container">
                                    <canvas class="history-image" 
                                            width="320" height="240" 
                                            data-index="${index}"></canvas>
                                </div>
                                <div class="history-info">
                                    <div class="history-stat">Distance: ${item.info.position.distance.toFixed(2)} units</div>
                                    <div class="history-stat">Angle X: ${item.info.position.angle_x.toFixed(2)}°</div>
                                    <div class="history-stat">Angle Y: ${item.info.position.angle_y.toFixed(2)}°</div>
                                </div>
                            </div>
                        `).join('');
                        
                        // Draw images and overlays
                        detectionHistory.forEach((item, index) => {
                            const canvas = document.querySelector(`canvas[data-index="${index}"]`);
                            if (canvas) {
                                const ctx = canvas.getContext('2d');
                                const img = new Image();
                                img.onload = () => {
                                    // Clear canvas
                                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                                    // Draw image
                                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                                    // Draw overlay
                                    drawDetectionOverlay(ctx, item.info, canvas.width, canvas.height);
                                };
                                img.src = 'data:image/jpeg;base64,' + item.image;
                            }
                        });
                    }

                    function updateLiveStats(info) {
                        const stats = document.querySelector('.stats-overlay');
                        if (stats) {
                            stats.innerHTML = `
                                <div class="stat-row">
                                    <span class="stat-label">Distance:</span>
                                    <span class="stat-value">${info.position.distance.toFixed(2)} units</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Angle X:</span>
                                    <span class="stat-value">${info.position.angle_x.toFixed(2)}°</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Angle Y:</span>
                                    <span class="stat-value">${info.position.angle_y.toFixed(2)}°</span>
                                </div>
                                <div class="stat-row">
                                    <span class="stat-label">Size:</span>
                                    <span class="stat-value">${info.object_size.width}x${info.object_size.height}px</span>
                                </div>
                            `;
                        }
                    }

                    function updateCompass(angle) {
                        const compass = document.querySelector('.compass-arrow');
                        if (compass) {
                            compass.style.transform = `translate(-50%, -100%) rotate(${angle}deg)`;
                        }
                    }
                    
                    function updateStatus() {
                        fetch('/status')
                            .then(response => response.json())
                            .then(data => {
                                document.getElementById('processStatus').innerText = data.status;
                                
                                if (data.detection_info) {
                                    // Update live overlay
                                    updateOverlay(data);
                                    updateLiveStats(data.detection_info);
                                    
                                    if (data.last_detection_image) {
                                        const detection = {
                                            image: data.last_detection_image,
                                            info: data.detection_info
                                        };
                                        
                                        // Only add to history if it's a new detection
                                        const lastDetection = detectionHistory[0];
                                        if (!lastDetection || 
                                            lastDetection.info.timestamp !== detection.info.timestamp) {
                                            console.log("New detection added to history");
                                            updateDetectionHistory(detection);
                                        }
                                    }
                                } else {
                                    // Clear live overlay but keep scanning effect
                                    const canvas = document.getElementById('videoOverlay');
                                    if (canvas) {
                                        const ctx = canvas.getContext('2d');
                                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                                        drawScanningEffect(ctx, canvas.width, canvas.height);
                                    }
                                }
                            })
                            .catch(error => {
                                console.error('Error updating status:', error);
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
                    <div class="video-section">
                        <div class="video-wrapper">
                            <img class="video-feed" src="/video_feed">
                            <canvas id="videoOverlay"></canvas>
                            <div class="stats-overlay"></div>
                            <div class="compass-container">
                                <div class="compass">
                                    <div class="compass-arrow"></div>
                                    <div class="compass-labels">
                                        <span class="compass-n">N</span>
                                        <span class="compass-e">E</span>
                                        <span class="compass-s">S</span>
                                        <span class="compass-w">W</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="detection-section">
                        <div id="processStatus" class="status-box">Initializing...</div>
                        <div class="history-section">
                            <div class="history-title">Detection History</div>
                            <div class="history-grid">
                                <!-- Detection history will be populated here -->
                            </div>
                        </div>
                    </div>
                </div>
            </body>
        </html>
        """

    def video_feed(self):
        """Video streaming route."""
        def generate():
            if not self.init_camera():
                return
                
            while True:
                with self.camera_lock:
                    try:
                        frame = self.camera.get_frame()
                        if frame is not None:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                        else:
                            print("Warning: Empty frame received")
                            time.sleep(0.1)
                    except Exception as e:
                        print(f"Error in video feed: {e}")
                        time.sleep(0.1)
                        
        return Response(generate(),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    
    def get_frame_safe(self):
        """Thread-safe method to get a frame."""
        if not self.init_camera():
            return None
            
        with self.camera_lock:
            try:
                frame = self.camera.get_frame()
                if frame is None:
                    print("Warning: No frame captured from camera")
                return frame
            except Exception as e:
                print(f"Error getting frame: {e}")
                return None
    
    def get_status(self):
        """Get current process status and detection information."""
        status_data = {
            'status': self.current_status,
            'detection_info': None,
            'last_detection_image': None
        }
        
        if self.detector:
            if self.detector.detection_info:
                status_data['detection_info'] = self.detector.detection_info
                status_data['last_detection_image'] = self.detector.last_detection_image
        
        return status_data
    
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