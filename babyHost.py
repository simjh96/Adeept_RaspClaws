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
                    .history-container {
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                        gap: 10px;
                        background: #2a2a2a;
                        padding: 10px;
                        border-radius: 5px;
                    }
                    .history-image {
                        width: 100%;
                        height: auto;
                        border-radius: 3px;
                        cursor: pointer;
                        transition: transform 0.2s;
                    }
                    .history-image:hover {
                        transform: scale(1.05);
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
                        updateStats(info);
                        
                        return {
                            scaledCenter,
                            scaledFrameCenter,
                            angle
                        };
                    }

                    function updateDetectionHistory() {
                        const container = document.getElementById('historyContainer');
                        container.innerHTML = detectionHistory.map((item, index) => {
                            const canvas = document.createElement('canvas');
                            canvas.width = 120;
                            canvas.height = 90;
                            canvas.className = 'history-image';
                            canvas.onclick = () => showHistoryDetail(index);
                            canvas.title = item.info.timestamp;
                            
                            // Draw the image
                            const img = new Image();
                            img.onload = () => {
                                const ctx = canvas.getContext('2d');
                                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                                
                                // Draw overlay on historical image
                                if (item.overlay_data) {
                                    drawDetectionOverlay(ctx, item.info, canvas.width, canvas.height);
                                }
                            };
                            img.src = 'data:image/jpeg;base64,' + item.image;
                            
                            return canvas.outerHTML;
                        }).join('');
                    }

                    function showHistoryDetail(index) {
                        const item = detectionHistory[index];
                        const detailCanvas = document.createElement('canvas');
                        const img = new Image();
                        
                        img.onload = () => {
                            detailCanvas.width = img.width;
                            detailCanvas.height = img.height;
                            const ctx = detailCanvas.getContext('2d');
                            
                            // Draw the base image
                            ctx.drawImage(img, 0, 0);
                            
                            // Draw the overlay
                            if (item.overlay_data) {
                                drawDetectionOverlay(ctx, item.info, detailCanvas.width, detailCanvas.height);
                            }
                            
                            // Convert to base64 and display
                            document.getElementById('mainDetectionImage').src = detailCanvas.toDataURL();
                            document.getElementById('mainDetectionImage').style.display = 'block';
                            document.getElementById('detectionTimestamp').innerText = item.info.timestamp;
                            
                            // Update stats
                            updateStats(item.info);
                        };
                        
                        img.src = 'data:image/jpeg;base64,' + item.image;
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
                                    // Update overlay with new detection
                                    updateOverlay(data);
                                    
                                    if (data.last_detection_image) {
                                        const imgData = {
                                            image: data.last_detection_image,
                                            info: data.detection_info,
                                            overlay_data: {
                                                position: data.detection_info.position,
                                                center: data.detection_info.center,
                                                frame_center: data.detection_info.frame_center
                                            }
                                        };
                                        
                                        // Only add to history if it's a new detection
                                        if (!detectionHistory.length || 
                                            detectionHistory[detectionHistory.length-1].info.timestamp !== imgData.info.timestamp) {
                                            detectionHistory.push(imgData);
                                            if (detectionHistory.length > MAX_HISTORY) {
                                                detectionHistory.shift();
                                            }
                                            updateDetectionHistory();
                                            
                                            // Show the latest detection
                                            document.getElementById('mainDetectionImage').src = 
                                                'data:image/jpeg;base64,' + data.last_detection_image;
                                            document.getElementById('mainDetectionImage').style.display = 'block';
                                            document.getElementById('detectionTimestamp').innerText = 
                                                data.detection_info.timestamp;
                                        }
                                    }
                                } else {
                                    // Clear current overlay when no detection
                                    const canvas = document.getElementById('videoOverlay');
                                    const ctx = canvas.getContext('2d');
                                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                                    drawScanningEffect(ctx, canvas.width, canvas.height);
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
                    <div class="video-section">
                        <div class="video-wrapper">
                            <img class="video-feed" src="/video_feed">
                            <canvas id="videoOverlay"></canvas>
                        </div>
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
                    
                    <div class="detection-section">
                        <div id="processStatus" class="status-box">Initializing...</div>
                        <div class="main-detection">
                            <img id="mainDetectionImage" style="display: none;">
                            <span id="detectionTimestamp"></span>
                        </div>
                        <div class="history-container" id="historyContainer">
                            <!-- Detection history will be populated here -->
                        </div>
                        <div id="statsContainer" class="stats-section">
                            <!-- Stats content -->
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