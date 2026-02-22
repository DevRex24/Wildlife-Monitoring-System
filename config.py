"""
Configuration file for Wildlife Monitoring System
Update the email settings with your credentials before running the application
"""

# EMAIL SETTINGS
# IMPORTANT: Set up Gmail App Password
# 1. Go to https://myaccount.google.com/security
# 2. Enable 2-Step Verification
# 3. Go to App Passwords: https://myaccount.google.com/apppasswords
# 4. Create new app password for "Mail"
# 5. Copy the 16-character password below

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@gmail.com"  # TODO: Replace with your Gmail address
SENDER_PASSWORD = "your-app-password"  # TODO: Replace with Gmail App Password (16 chars)
OFFICER_EMAIL = "officer-email@gmail.com"  # TODO: Replace with officer's email

# DETECTION SETTINGS
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence score (0.0 to 1.0)
CAMERA_ID = "CAM_001"  # Camera identifier for logging

# YOLO classes to detect (COCO dataset class names)
DETECTION_CLASSES = [
    # Humans
    "person",
    # Vehicles
    "car", "truck", "bus", "motorcycle", "bicycle",
    # Animals (Wildlife)
    "bird", "cat", "dog", "horse", "sheep", "cow", 
    "elephant", "bear", "zebra", "giraffe"
]

# Animal classes for special handling
ANIMAL_CLASSES = ["bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"]

# Vehicle classes
VEHICLE_CLASSES = ["car", "truck", "bus", "motorcycle", "bicycle"]

# YOLO model path (will auto-download if not present)
YOLO_MODEL = "yolov8n.pt"  # Options: yolov8n.pt (nano), yolov8s.pt (small), yolov8m.pt (medium)

# ============================================
# ALERT SETTINGS
# ============================================
ALERT_COOLDOWN = 10  # Seconds between consecutive alerts (prevents spam)
ENABLE_SOUND = True  # Play alert sound on detection
ENABLE_EMAIL = True  # Send email alerts

# CAMERA SETTINGS
# Multiple Camera Configuration
# Each camera can be a webcam index (0, 1, 2) or an IP camera URL
# Examples:
#   - Webcam: 0, 1, 2 (integer index)
#   - IP Camera: "rtsp://username:password@192.168.1.100:554/stream"
#   - Video file: "path/to/video.mp4"

CAMERAS = [
    {
        "id": "CAM_001",
        "name": "Main Camera",
        "source": 0,  # Webcam index or URL
        "enabled": True
    },
    # Add more cameras as needed:
    # {
    #     "id": "CAM_002",
    #     "name": "Back Entrance",
    #     "source": 1,
    #     "enabled": True
    # },
    # {
    #     "id": "CAM_003",
    #     "name": "IP Camera",
    #     "source": "rtsp://192.168.1.100:554/stream",
    #     "enabled": True
    # },
]

# Legacy single camera settings (for backward compatibility)
CAMERA_INDEX = 0  # Webcam index (0 for default camera)
FRAME_WIDTH = 640  # Camera frame width
FRAME_HEIGHT = 480  # Camera frame height
FPS = 30  # Frames per second

# STORAGE SETTINGS

SNAPSHOT_DIR = "snapshots"  # Directory to save detection images
DATABASE_PATH = "database/alerts.db"  # SQLite database path
IMAGE_RETENTION_DAYS = 30  # Days to keep old snapshots (0 = keep forever)

# FLASK SETTINGS
FLASK_HOST = "0.0.0.0"  # Host address (0.0.0.0 = accessible from network)
FLASK_PORT = 5000  # Port number
DEBUG_MODE = True  # Enable Flask debug mode (set False for production)
