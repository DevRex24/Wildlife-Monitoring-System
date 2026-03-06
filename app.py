"""
Wildlife Monitoring System - Main Flask Application!
Real-time AI-powered surveillance for wildlife protection with multi-camera support, alerting, and analytics.
"""

from flask import Flask, render_template, Response, request, jsonify, send_from_directory
import cv2
import time
from datetime import datetime
import threading
import os
import config
from database.db_manager import init_database, log_alert, get_recent_alerts, get_alert_stats, get_chart_data
from utils.detection_logic import load_model, detect_objects, is_threat_detected, get_highest_confidence_detection, format_detection_summary, draw_alert_banner, calculate_severity_level
from utils.image_save import save_snapshot, get_relative_path
from utils.email_alert import send_alert_email
from utils.video_recorder import add_frame_to_buffer, record_video_async, get_video_relative_path

# Initialize Flask app
app = Flask(__name__)

# Global variables
cameras = {}  # Dictionary to hold multiple camera objects
camera_states = {}  # Track state for each camera
last_alert_time = 0
alert_cooldown = config.ALERT_COOLDOWN
current_detections = []
threat_active = False
system_active = True  # Toggle for enabling/disabling detection

# Detection persistence - keeps boxes visible for a few frames when flickering
last_valid_detections = []
last_annotated_frame = None
frames_since_detection = 0
DETECTION_PERSISTENCE_FRAMES = 8  # Keep showing detection for this many frames

class CameraManager:
    """Manages multiple camera instances"""
    
    def __init__(self, camera_config):
        self.id = camera_config['id']
        self.name = camera_config['name']
        self.source = camera_config['source']
        self.enabled = camera_config.get('enabled', True)
        self.camera = None
        self.last_alert_time = 0
        self.current_detections = []
        self.threat_active = False
        self.lock = threading.Lock()
        
    def initialize(self):
        """Initialize the camera"""
        try:
            self.camera = cv2.VideoCapture(self.source)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, config.FPS)
            
            if not self.camera.isOpened():
                print(f"✗ Error: Could not open camera {self.id} ({self.name})")
                return False
            
            print(f"✓ Camera {self.id} ({self.name}) initialized successfully")
            return True
        except Exception as e:
            print(f"✗ Error initializing camera {self.id}: {e}")
            return False
    
    def release(self):
        """Release camera resources"""
        if self.camera is not None:
            self.camera.release()
            self.camera = None
    
    def read_frame(self):
        """Read a frame from the camera"""
        if self.camera is None or not self.camera.isOpened():
            return False, None
        return self.camera.read()
    
    def is_opened(self):
        """Check if camera is opened"""
        return self.camera is not None and self.camera.isOpened()

def initialize_cameras():
    """Initialize all configured cameras"""
    global cameras, camera_states
    
    success_count = 0
    
    for cam_config in config.CAMERAS:
        if cam_config.get('enabled', True):
            cam_manager = CameraManager(cam_config)
            if cam_manager.initialize():
                cameras[cam_config['id']] = cam_manager
                camera_states[cam_config['id']] = {
                    'active': True,
                    'threat': False,
                    'detections': []
                }
                success_count += 1
    
    # Fallback to legacy single camera if no cameras configured
    if not cameras and hasattr(config, 'CAMERA_INDEX'):
        legacy_config = {
            'id': 'CAM_001',
            'name': 'Main Camera',
            'source': config.CAMERA_INDEX,
            'enabled': True
        }
        cam_manager = CameraManager(legacy_config)
        if cam_manager.initialize():
            cameras['CAM_001'] = cam_manager
            camera_states['CAM_001'] = {
                'active': True,
                'threat': False,
                'detections': []
            }
            success_count += 1
    
    return success_count > 0

# Keep legacy initialize_camera for backward compatibility
def initialize_camera():
    """Initialize the camera (legacy function)"""
    return initialize_cameras()

def trigger_alert_async(frame_copy, top_detection, detections_summary, camera_id="CAM_001", severity=None):
    """
    Handle alert actions in a background thread to prevent camera freeze.
    Saves snapshot, records video, sends email, and logs to database.
    """
    try:
        # Default severity if not provided
        if severity is None:
            severity = {'level': 'MEDIUM', 'score': 50}
        
        # Save snapshot
        snapshot_path = save_snapshot(frame_copy, top_detection['class'])
        relative_path = get_relative_path(snapshot_path)
        
        # Record video clip with camera ID
        record_video_async(top_detection['class'], frame_copy, camera_id)
        
        # Send email alert (this can be slow)
        email_sent = send_alert_email(
            detection_type=top_detection['class'],
            confidence=top_detection['confidence'],
            image_path=snapshot_path
        )
        
        # Log to database with camera ID and severity
        alert_id = log_alert(
            detection_type=top_detection['class'],
            confidence=top_detection['confidence'],
            image_path=relative_path,
            email_sent=email_sent,
            notes=f"[{camera_id}] [{severity['level']}] {detections_summary}"
        )
        
        print(f"⚠ ALERT #{alert_id} [{camera_id}] [{severity['level']}]: {top_detection['class']} detected (confidence: {top_detection['confidence']:.2f})")
        if email_sent:
            print(f"   ✓ Email alert sent successfully")
        else:
            print(f"   ⚠ Email alert not sent (check config)")
        print(f"   ✓ Snapshot saved: {snapshot_path}")
        
    except Exception as e:
        print(f"✗ Error in alert processing: {e}")

def process_frame_for_camera(frame, camera_id):
    """Process a single frame for detection for a specific camera"""
    global system_active, camera_states
    
    cam_manager = cameras.get(camera_id)
    if not cam_manager:
        return frame
    
    # If system is inactive, just return the frame without detection
    if not system_active:
        camera_states[camera_id]['detections'] = []
        camera_states[camera_id]['threat'] = False
        camera_states[camera_id]['severity'] = {'level': 'NONE', 'score': 0}
        return frame
    
    # Run detection
    annotated_frame, detections = detect_objects(frame)
    camera_states[camera_id]['detections'] = detections
    
    # Calculate severity level
    severity = calculate_severity_level(detections)
    camera_states[camera_id]['severity'] = severity
    
    # Check for threats
    if is_threat_detected(detections):
        camera_states[camera_id]['threat'] = True
        current_time = time.time()
        
        # Check if we should trigger a new alert (cooldown period)
        if current_time - cam_manager.last_alert_time >= alert_cooldown:
            cam_manager.last_alert_time = current_time
            
            # Get highest confidence detection
            top_detection = get_highest_confidence_detection(detections)
            detections_summary = format_detection_summary(detections)
            
            # Make a copy of the frame for the background thread
            frame_copy = annotated_frame.copy()
            
            # Run alert actions in background thread to prevent camera freeze
            alert_thread = threading.Thread(
                target=trigger_alert_async,
                args=(frame_copy, top_detection, detections_summary, camera_id, severity),
                daemon=True
            )
            alert_thread.start()
            
            print(f"📸 [{camera_id}] {severity['level']} Alert - {severity['description']}")
        
        # Draw alert banner with severity color
        summary = format_detection_summary(detections)
        annotated_frame = draw_alert_banner(annotated_frame, summary, detections)
    else:
        camera_states[camera_id]['threat'] = False
        camera_states[camera_id]['severity'] = {'level': 'NONE', 'score': 0}
    
    return annotated_frame

def process_frame(frame):
    """Process a single frame for detection (legacy - uses first camera)"""
    global current_detections, threat_active
    
    # Get the first camera ID for backward compatibility
    first_cam_id = list(cameras.keys())[0] if cameras else 'CAM_001'
    result = process_frame_for_camera(frame, first_cam_id)
    
    # Update legacy global variables
    current_detections = camera_states.get(first_cam_id, {}).get('detections', [])
    threat_active = camera_states.get(first_cam_id, {}).get('threat', False)
    
    return result

def generate_frames_for_camera(camera_id):
    """Generate frames for a specific camera"""
    global cameras, current_detections, threat_active
    
    cam_manager = cameras.get(camera_id)
    if not cam_manager:
        return
    
    while True:
        if not cam_manager.is_opened():
            # Try to reconnect
            time.sleep(1)
            cam_manager.initialize()
            continue
        
        success, frame = cam_manager.read_frame()
        if not success:
            time.sleep(0.1)
            continue
        
        # Add frame to buffer for video recording (only for main camera)
        if camera_id == list(cameras.keys())[0]:
            add_frame_to_buffer(frame.copy())
        
        # Process frame for detection
        processed_frame = process_frame_for_camera(frame, camera_id)
        
        # Update global threat status for ANY camera detecting a threat
        # This ensures the /current_status endpoint returns correct threat_active
        any_threat = any(state.get('threat', False) for state in camera_states.values())
        threat_active = any_threat
        
        # Update current_detections from all cameras
        all_detections = []
        for state in camera_states.values():
            all_detections.extend(state.get('detections', []))
        current_detections = all_detections
        
        # Encode frame as JPEG
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        frame_bytes = buffer.tobytes()
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def generate_frames():
    """Generate frames for video streaming (legacy - uses first camera)"""
    first_cam_id = list(cameras.keys())[0] if cameras else 'CAM_001'
    return generate_frames_for_camera(first_cam_id)

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route (legacy - first camera)"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed/<camera_id>')
def video_feed_camera(camera_id):
    """Video streaming route for specific camera"""
    if camera_id not in cameras:
        return "Camera not found", 404
    return Response(generate_frames_for_camera(camera_id),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/cameras')
def list_cameras():
    """Get list of all configured cameras"""
    try:
        camera_list = []
        for cam_id, cam_manager in cameras.items():
            camera_list.append({
                'id': cam_id,
                'name': cam_manager.name,
                'source': str(cam_manager.source),
                'enabled': cam_manager.enabled,
                'active': cam_manager.is_opened(),
                'threat': camera_states.get(cam_id, {}).get('threat', False),
                'detections': camera_states.get(cam_id, {}).get('detections', [])
            })
        return jsonify({
            'success': True,
            'cameras': camera_list,
            'total': len(camera_list)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/cameras/add', methods=['POST'])
def add_camera():
    """Add a new camera dynamically"""
    try:
        data = request.get_json()
        cam_id = data.get('id', f"CAM_{len(cameras) + 1:03d}")
        name = data.get('name', f"Camera {len(cameras) + 1}")
        source = data.get('source', 0)
        
        # Convert source to int if it's a digit string
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        
        # Check if camera ID already exists
        if cam_id in cameras:
            return jsonify({
                'success': False,
                'error': 'Camera ID already exists'
            }), 400
        
        # Create and initialize new camera
        cam_config = {
            'id': cam_id,
            'name': name,
            'source': source,
            'enabled': True
        }
        
        cam_manager = CameraManager(cam_config)
        if cam_manager.initialize():
            cameras[cam_id] = cam_manager
            camera_states[cam_id] = {
                'active': True,
                'threat': False,
                'detections': []
            }
            return jsonify({
                'success': True,
                'message': f'Camera {name} added successfully',
                'camera': {
                    'id': cam_id,
                    'name': name,
                    'source': str(source)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to initialize camera'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/cameras/<camera_id>/remove', methods=['POST'])
def remove_camera(camera_id):
    """Remove a camera"""
    try:
        if camera_id not in cameras:
            return jsonify({
                'success': False,
                'error': 'Camera not found'
            }), 404
        
        # Release camera resources
        cameras[camera_id].release()
        del cameras[camera_id]
        del camera_states[camera_id]
        
        return jsonify({
            'success': True,
            'message': f'Camera {camera_id} removed successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/cameras/<camera_id>/status')
def camera_status(camera_id):
    """Get status of a specific camera"""
    try:
        if camera_id not in cameras:
            return jsonify({
                'success': False,
                'error': 'Camera not found'
            }), 404
        
        cam_manager = cameras[camera_id]
        state = camera_states.get(camera_id, {})
        
        return jsonify({
            'success': True,
            'camera': {
                'id': camera_id,
                'name': cam_manager.name,
                'active': cam_manager.is_opened(),
                'threat': state.get('threat', False),
                'detections': state.get('detections', [])
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/snapshots/<path:filename>')
def serve_snapshot(filename):
    """Serve snapshot images"""
    return send_from_directory(os.path.join(os.getcwd(), 'snapshots'), filename)

@app.route('/recordings/<path:filename>')
def serve_recording(filename):
    """Serve video recordings"""
    return send_from_directory(os.path.join(os.getcwd(), 'recordings'), filename)

@app.route('/recordings')
def list_recordings():
    """Get list of recorded videos"""
    try:
        recordings = []
        recordings_dir = os.path.join(os.getcwd(), 'recordings')
        
        if os.path.exists(recordings_dir):
            for date_folder in sorted(os.listdir(recordings_dir), reverse=True):
                folder_path = os.path.join(recordings_dir, date_folder)
                if os.path.isdir(folder_path):
                    for video_file in sorted(os.listdir(folder_path), reverse=True):
                        if video_file.endswith('.mp4'):
                            video_path = f"recordings/{date_folder}/{video_file}"
                            # Extract info from filename: clip_HHMMSS_CAM_XXX_detection.mp4
                            parts = video_file.replace('.mp4', '').split('_')
                            
                            # Parse based on filename format
                            time_str = parts[1] if len(parts) > 1 else ''
                            
                            # Check if camera ID is in the filename (new format)
                            camera_id = 'CAM_001'  # Default
                            detection_type = 'unknown'
                            
                            if len(parts) >= 4 and parts[2] == 'CAM':
                                # New format: clip_HHMMSS_CAM_XXX_detection.mp4
                                camera_id = f"CAM_{parts[3]}"
                                detection_type = parts[4] if len(parts) > 4 else 'unknown'
                            elif len(parts) >= 3:
                                # Old format: clip_HHMMSS_detection.mp4
                                detection_type = parts[-1]
                            
                            recordings.append({
                                'path': video_path,
                                'filename': video_file,
                                'date': date_folder,
                                'time': f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}" if len(time_str) == 6 else time_str,
                                'detection_type': detection_type,
                                'camera_id': camera_id
                            })
        
        return jsonify({
            'success': True,
            'recordings': recordings[:20]  # Return last 20 recordings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/alerts')
def alerts():
    """Get recent alerts as JSON"""
    try:
        limit = request.args.get('limit', 50, type=int)
        alerts_list = get_recent_alerts(limit)
        
        # Get total count for stats
        stats = get_alert_stats()
        total_count = stats.get('total_alerts', len(alerts_list))
        
        return jsonify({
            'success': True,
            'alerts': alerts_list,
            'total_count': total_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stats')
def stats():
    """Get alert statistics as JSON"""
    try:
        statistics = get_alert_stats()
        return jsonify({
            'success': True,
            'stats': statistics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/stats/charts')
def stats_charts():
    """Get chart data for statistics dashboard"""
    try:
        time_range = request.args.get('range', 'daily')
        print(f"📊 Chart data requested for range: {time_range}")
        chart_data = get_chart_data(time_range)
        print(f"📊 Chart data retrieved successfully")
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        print(f"📊 Chart data error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/current_status')
def current_status():
    """Get current detection status with severity information"""
    global current_detections, threat_active, system_active, camera_states
    
    # Calculate overall severity from all cameras
    all_detections = []
    for state in camera_states.values():
        all_detections.extend(state.get('detections', []))
    
    severity = calculate_severity_level(all_detections)
    
    return jsonify({
        'threat_active': threat_active,
        'detections': current_detections,
        'detection_count': len(current_detections),
        'system_active': system_active,
        'severity': severity
    })

@app.route('/toggle_system', methods=['POST'])
def toggle_system():
    """Toggle the detection system on/off"""
    global system_active, threat_active
    
    system_active = not system_active
    
    # Reset threat status when disabling
    if not system_active:
        threat_active = False
    
    status = "activated" if system_active else "deactivated"
    print(f"🔄 System {status}")
    
    return jsonify({
        'success': True,
        'system_active': system_active,
        'message': f'Detection system {status}'
    })

@app.route('/upload', methods=['POST'])
def upload_image():
    """Handle image upload for manual detection"""
    try:
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Read image
        import numpy as np
        file_bytes = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({
                'success': False,
                'error': 'Invalid image file'
            }), 400
        
        # Run detection
        annotated_frame, detections = detect_objects(frame)
        
        # If threat detected, save and alert
        if is_threat_detected(detections):
            top_detection = get_highest_confidence_detection(detections)
            
            # Save snapshot
            snapshot_path = save_snapshot(annotated_frame, top_detection['class'])
            relative_path = get_relative_path(snapshot_path)
            
            # Send email
            email_sent = send_alert_email(
                detection_type=top_detection['class'],
                confidence=top_detection['confidence'],
                image_path=snapshot_path
            )
            
            # Log to database
            alert_id = log_alert(
                detection_type=top_detection['class'],
                confidence=top_detection['confidence'],
                image_path=relative_path,
                email_sent=email_sent,
                notes=f"Manual upload: {format_detection_summary(detections)}"
            )
            
            return jsonify({
                'success': True,
                'threat_detected': True,
                'alert_id': alert_id,
                'detections': detections,
                'message': format_detection_summary(detections)
            })
        else:
            return jsonify({
                'success': True,
                'threat_detected': False,
                'message': 'No threats detected in uploaded image'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def cleanup_on_exit():
    """Cleanup resources on exit"""
    global cameras
    for cam_id, cam_manager in cameras.items():
        cam_manager.release()
        print(f"   ✓ Camera {cam_id} released")
    cv2.destroyAllWindows()
    print("\n✓ All resources cleaned up")

if __name__ == '__main__':
    print("=" * 60)
    print("Wildlife Monitoring System - Multi-Camera Support")
    print("=" * 60)
    
    # Initialize database
    print("\n[1/4] Initializing database...")
    init_database()
    
    # Load YOLO model
    print("\n[2/4] Loading YOLO model...")
    load_model()
    
    # Initialize cameras
    print("\n[3/4] Initializing cameras...")
    if not initialize_cameras():
        print("✗ Failed to initialize any camera. Exiting...")
        exit(1)
    
    # Start Flask server
    print("\n[4/4] Starting web server...")
    print(f"\n✓ System ready!")
    print(f"   Dashboard: http://localhost:{config.FLASK_PORT}")
    print(f"   Active cameras: {len(cameras)}")
    for cam_id, cam in cameras.items():
        print(f"      - {cam_id}: {cam.name}")
    print(f"   Detection threshold: {config.CONFIDENCE_THRESHOLD}")
    print(f"   Alert cooldown: {config.ALERT_COOLDOWN}s")
    print("\nPress Ctrl+C to stop\n")
    
    try:
        app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.DEBUG_MODE, threaded=True)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        cleanup_on_exit()
