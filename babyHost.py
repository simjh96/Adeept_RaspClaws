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
    
    def __init__(self, port=5000, debug=True):
        if not hasattr(self, 'initialized'):
            self.app = Flask(__name__)
            CORS(self.app, supports_credentials=True)
            self.camera = None
            self.port = port
            self.debug = debug
            self.camera_lock = threading.Lock()
            self.current_status = "Initializing..."
            self.movement_info = None
            self.head_movement_info = None
            self.status_history = []  # Keep track of status history
            
            # Register routes
            self.app.route('/')(self.index)
            self.app.route('/video_feed')(self.video_feed)
            self.app.route('/status')(self.get_status)
            self.app.route('/favicon.ico')(self.favicon)
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
                    .map-section {
                        background: #2a2a2a;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 15px;
                    }
                    #mapCanvas {
                        width: 100%;
                        height: 300px;
                        background: #1a1a1a;
                        border-radius: 3px;
                    }
                    .status-box {
                        background: #2a2a2a;
                        padding: 15px;
                        border-radius: 5px;
                        margin-bottom: 15px;
                        font-family: monospace;
                        white-space: pre-wrap;
                        max-height: 200px;
                        overflow-y: auto;
                    }
                    .movement-log {
                        color: #00ff00;
                        margin: 5px 0;
                    }
                    .head-movement-log {
                        color: #00ffff;
                        margin: 5px 0;
                    }
                    .progress-log {
                        color: #ffff00;
                        margin: 5px 0;
                    }
                </style>
                <script>
                    let detectionHistory = [];
                    let robotPosition = { x: 0, y: 0, angle: 0 };
                    let mapScale = 50; // pixels per unit
                    let pathHistory = [];
                    let lastFrameCenter = null;
                    let lastObjectCenter = null;
                    let overlayTimeout = null;
                    let mapPadding = 50; // padding around the content
                    let initialMapScale = 50; // Initial scale for empty map
                    const MAX_HISTORY = 10; // Maximum number of history items to keep

                    function updateOverlay(data) {
                        const wrapper = document.querySelector('.video-wrapper');
                        const video = document.querySelector('.video-feed');
                        const canvas = document.getElementById('videoOverlay');
                        
                        if (!canvas || !video) return;
                        
                        // Match canvas size to video
                        canvas.width = video.offsetWidth;
                        canvas.height = video.offsetHeight;
                        
                        const ctx = canvas.getContext('2d');
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                        
                        if (data.detection_info) {
                            drawDetectionOverlay(ctx, data.detection_info, canvas.width, canvas.height);
                            
                            // Clear overlay after 2 seconds
                            if (overlayTimeout) {
                                clearTimeout(overlayTimeout);
                            }
                            overlayTimeout = setTimeout(() => {
                                ctx.clearRect(0, 0, canvas.width, canvas.height);
                            }, 2000);
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
                        if (!newDetection || !newDetection.info) {
                            console.warn('Invalid detection data received');
                            return;
                        }
                        
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
                                const statusBox = document.getElementById('processStatus');
                                let statusText = '';
                                
                                // Add status history
                                if (data.status_history && data.status_history.length > 0) {
                                    statusText = data.status_history.join('\n') + '\n\n';
                                }
                                
                                statusText += `Current Status: ${data.status}\n`;
                                
                                if (data.movement_info) {
                                    statusText += `\nMovement Info:\n${data.movement_info.status}\n`;
                                    if (data.movement_info.progress) {
                                        statusText += `Progress: ${data.movement_info.progress}%\n`;
                                    }
                                    if (data.movement_info.details) {
                                        statusText += `Details: ${data.movement_info.details}\n`;
                                    }
                                    
                                    // Update robot position and map
                                    if (data.movement_info.position) {
                                        const newPos = data.movement_info.position;
                                        if (robotPosition.x !== newPos.x || 
                                            robotPosition.y !== newPos.y || 
                                            robotPosition.angle !== newPos.angle) {
                                            robotPosition = {...newPos};
                                            pathHistory.push({...newPos});
                                            updateMap(data);
                                        }
                                    }
                                }
                                
                                if (data.head_movement_info) {
                                    statusText += `\nHead Movement:\n`;
                                    statusText += `Position: X=${data.head_movement_info.x}, Y=${data.head_movement_info.y}\n`;
                                    if (data.head_movement_info.target) {
                                        statusText += `Target: X=${data.head_movement_info.target.x}, Y=${data.head_movement_info.target.y}\n`;
                                    }
                                }
                                
                                statusBox.innerText = statusText;
                                
                                if (data.detection_info && data.last_detection_image) {
                                    updateOverlay(data);
                                    
                                    const detection = {
                                        image: data.last_detection_image,
                                        info: data.detection_info
                                    };
                                    
                                    const lastDetection = detectionHistory[0];
                                    if (!lastDetection || 
                                        lastDetection.info.timestamp !== detection.info.timestamp) {
                                        console.log("New detection added to history");
                                        updateDetectionHistory(detection);
                                    }
                                }
                            })
                            .catch(error => {
                                console.error('Error updating status:', error);
                            });
                    }
                    
                    // Start when page loads
                    window.onload = function() {
                        const video = document.querySelector('.video-feed');
                        const canvas = document.getElementById('videoOverlay');
                        
                        function resizeOverlay() {
                            if (canvas && video) {
                                canvas.width = video.offsetWidth;
                                canvas.height = video.offsetHeight;
                            }
                        }
                        
                        // Resize overlay when video size changes
                        if (video) {
                            new ResizeObserver(resizeOverlay).observe(video);
                        }
                        
                        // Initial resize
                        resizeOverlay();
                        
                        // Update status every 100ms
                        setInterval(updateStatus, 100);
                    }

                    function calculateMapBounds() {
                        // Start with robot's current position
                        let bounds = {
                            minX: robotPosition.x,
                            maxX: robotPosition.x,
                            minY: robotPosition.y,
                            maxY: robotPosition.y
                        };
                        
                        // Include path history
                        pathHistory.forEach(pos => {
                            bounds.minX = Math.min(bounds.minX, pos.x);
                            bounds.maxX = Math.max(bounds.maxX, pos.x);
                            bounds.minY = Math.min(bounds.minY, pos.y);
                            bounds.maxY = Math.max(bounds.maxY, pos.y);
                        });
                        
                        // Include detection points
                        detectionHistory.forEach(detection => {
                            const info = detection.info;
                            const distance = info.position.distance;
                            const angle = info.position.angle_x * Math.PI / 180;
                            const x = distance * Math.cos(angle);
                            const y = distance * Math.sin(angle);
                            
                            bounds.minX = Math.min(bounds.minX, x);
                            bounds.maxX = Math.max(bounds.maxX, x);
                            bounds.minY = Math.min(bounds.minY, y);
                            bounds.maxY = Math.max(bounds.maxY, y);
                        });
                        
                        // Add padding
                        const padding = 1; // 1 unit padding
                        bounds.minX -= padding;
                        bounds.maxX += padding;
                        bounds.minY -= padding;
                        bounds.maxY += padding;

                        // Ensure minimum view size
                        const minSize = 2; // Minimum 2x2 units view
                        if (bounds.maxX - bounds.minX < minSize) {
                            const center = (bounds.maxX + bounds.minX) / 2;
                            bounds.minX = center - minSize/2;
                            bounds.maxX = center + minSize/2;
                        }
                        if (bounds.maxY - bounds.minY < minSize) {
                            const center = (bounds.maxY + bounds.minY) / 2;
                            bounds.minY = center - minSize/2;
                            bounds.maxY = center + minSize/2;
                        }
                        
                        return bounds;
                    }

                    function initMap() {
                        const canvas = document.getElementById('mapCanvas');
                        const ctx = canvas.getContext('2d');
                        
                        // Set canvas size to match container
                        const container = canvas.parentElement;
                        canvas.width = container.clientWidth;
                        canvas.height = container.clientHeight;
                        
                        const width = canvas.width;
                        const height = canvas.height;
                        
                        // Clear canvas
                        ctx.fillStyle = '#1a1a1a';
                        ctx.fillRect(0, 0, width, height);
                        
                        // Calculate bounds and scale
                        const bounds = calculateMapBounds();
                        const contentWidth = Math.max(2, bounds.maxX - bounds.minX);
                        const contentHeight = Math.max(2, bounds.maxY - bounds.minY);
                        
                        // Calculate scale to fit content
                        const scaleX = (width - mapPadding * 2) / contentWidth;
                        const scaleY = (height - mapPadding * 2) / contentHeight;
                        mapScale = Math.min(scaleX, scaleY, initialMapScale);
                        
                        // Calculate center offset
                        const centerX = width / 2;
                        const centerY = height / 2;
                        
                        // Draw grid
                        ctx.strokeStyle = '#333';
                        ctx.lineWidth = 1;
                        
                        // Draw grid lines based on scale
                        const gridSize = 0.5; // 0.5 unit grid
                        const gridCount = Math.max(width, height) / mapScale;
                        const startX = -gridCount/2;
                        const endX = gridCount/2;
                        const startY = -gridCount/2;
                        const endY = gridCount/2;
                        
                        for(let x = startX; x <= endX; x += gridSize) {
                            const screenX = centerX + x * mapScale;
                            ctx.beginPath();
                            ctx.moveTo(screenX, mapPadding);
                            ctx.lineTo(screenX, height - mapPadding);
                            ctx.stroke();
                        }
                        
                        for(let y = startY; y <= endY; y += gridSize) {
                            const screenY = centerY - y * mapScale;
                            ctx.beginPath();
                            ctx.moveTo(mapPadding, screenY);
                            ctx.lineTo(width - mapPadding, screenY);
                            ctx.stroke();
                        }
                        
                        // Draw axes
                        ctx.strokeStyle = '#00ff00';
                        ctx.lineWidth = 2;
                        
                        // X axis
                        ctx.beginPath();
                        ctx.moveTo(mapPadding, centerY);
                        ctx.lineTo(width - mapPadding, centerY);
                        ctx.stroke();
                        
                        // Y axis
                        ctx.beginPath();
                        ctx.moveTo(centerX, mapPadding);
                        ctx.lineTo(centerX, height - mapPadding);
                        ctx.stroke();
                        
                        // Draw origin marker
                        ctx.beginPath();
                        ctx.arc(centerX, centerY, 5, 0, Math.PI * 2);
                        ctx.stroke();
                        
                        return { ctx, width, height, centerX, centerY };
                    }
                    
                    function updateMap(data) {
                        const canvas = document.getElementById('mapCanvas');
                        if (!canvas) return;
                        
                        const { ctx, width, height, centerX, centerY } = initMap();
                        
                        // Draw path history
                        if (pathHistory.length > 0) {
                            ctx.strokeStyle = '#004400';
                            ctx.lineWidth = 2;
                            ctx.beginPath();
                            pathHistory.forEach((pos, index) => {
                                const x = centerX + pos.x * mapScale;
                                const y = centerY - pos.y * mapScale;
                                if (index === 0) {
                                    ctx.moveTo(x, y);
                                } else {
                                    ctx.lineTo(x, y);
                                }
                            });
                            ctx.stroke();
                        }
                        
                        // Draw detection points
                        detectionHistory.forEach(detection => {
                            const info = detection.info;
                            const distance = info.position.distance;
                            const angle = info.position.angle_x * Math.PI / 180;
                            
                            const x = centerX + distance * Math.cos(angle) * mapScale;
                            const y = centerY - distance * Math.sin(angle) * mapScale;
                            
                            // Draw detection point
                            ctx.fillStyle = '#ff0000';
                            ctx.beginPath();
                            ctx.arc(x, y, 5, 0, Math.PI * 2);
                            ctx.fill();
                            
                            // Draw line from origin to detection point
                            ctx.strokeStyle = '#440000';
                            ctx.setLineDash([5, 5]);
                            ctx.beginPath();
                            ctx.moveTo(centerX, centerY);
                            ctx.lineTo(x, y);
                            ctx.stroke();
                            ctx.setLineDash([]);
                        });
                        
                        // Draw current robot position
                        const robotX = centerX + robotPosition.x * mapScale;
                        const robotY = centerY - robotPosition.y * mapScale;
                        
                        // Draw robot triangle
                        ctx.save();
                        ctx.translate(robotX, robotY);
                        ctx.rotate(-robotPosition.angle * Math.PI / 180);
                        
                        ctx.fillStyle = '#00ff00';
                        ctx.beginPath();
                        ctx.moveTo(0, -10);
                        ctx.lineTo(-7, 10);
                        ctx.lineTo(7, 10);
                        ctx.closePath();
                        ctx.fill();
                        
                        ctx.restore();
                        
                        // Draw scale indicator
                        ctx.fillStyle = '#888';
                        ctx.font = '12px monospace';
                        ctx.fillText(`Scale: ${(1/mapScale).toFixed(2)} units/pixel`, 10, height - 10);
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
                        <div class="map-section">
                            <canvas id="mapCanvas"></canvas>
                        </div>
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
            'last_detection_image': None,
            'movement_info': self.movement_info,
            'head_movement_info': self.head_movement_info,
            'status_history': self.status_history[-10:]  # Last 10 status updates
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
        if self.debug:
            print(f"Status Update: {status}")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_history.append(f"[{timestamp}] {status}")
        self.current_status = status

    def update_movement_info(self, info):
        """Update current movement information."""
        if not isinstance(info, dict):
            info = {'status': str(info)}
        
        # Ensure we have all required fields
        if 'status' not in info:
            info['status'] = 'Moving'
        if 'position' not in info:
            info['position'] = {'x': 0, 'y': 0, 'angle': 0}
        if 'progress' not in info:
            info['progress'] = None
        if 'details' not in info:
            info['details'] = None
            
        if self.debug:
            print(f"Movement Update: {info}")
            
        self.movement_info = info
        self.update_status(info['status'])

    def update_head_movement(self, info):
        """Update head movement information."""
        if not isinstance(info, dict):
            info = {'status': str(info)}
            
        # Ensure we have all required fields
        if 'x' not in info:
            info['x'] = 0
        if 'y' not in info:
            info['y'] = 0
        if 'target' not in info:
            info['target'] = None
            
        if self.debug:
            print(f"Head Movement Update: {info}")
            
        self.head_movement_info = info
        self.update_status(info['status'])

    def start(self):
        """Start the video hosting server in a separate thread."""
        def run_server():
            self.app.run(
                host='0.0.0.0',
                port=self.port,
                threaded=True,
                debug=self.debug,
                use_reloader=False,  # Disable reloader in debug mode
                log_level='ERROR'  # Suppress most Flask logging
            )
            
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

    def favicon(self):
        """Return a transparent favicon to prevent 404 errors."""
        return Response(status=204)

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