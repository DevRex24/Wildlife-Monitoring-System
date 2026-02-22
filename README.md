#  Wildlife Monitoring System

Real-time AI-powered surveillance system for wildlife protection using YOLOv8 object detection.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

##  Features

- **Live Camera Monitoring** - Multi-camera support with real-time video streaming
- **AI Object Detection** - YOLOv8-powered detection for humans, vehicles, and wildlife
- **Threat Alerts** - Automatic email alerts with severity levels (Critical/High/Medium/Low)
- **Video Recording** - Automatic clip recording when threats are detected
- **Image Upload** - Manual image analysis for offline detection
- **Statistics Dashboard** - Charts and analytics for detection trends
- **Responsive Web UI** - Modern dashboard accessible from any device

##  Prerequisites

- Python 3.11 or higher
- Webcam or IP camera
- Gmail account (for email alerts)

##  Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/wildlife-monitoring-system.git
cd wildlife-monitoring-system
```

### 2. Create Virtual Environment
```bash
python -m venv env

# Windows
.\env\Scripts\activate

# Linux/Mac
source env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Settings

Copy the example environment file and update with your settings:
```bash
cp .env.example .env
```

Or edit `config.py` directly:
- `SENDER_EMAIL` - Your Gmail address
- `SENDER_PASSWORD` - Gmail App Password
- `OFFICER_EMAIL` - Alert recipient email

### 5. Run the Application
```bash
python app.py
```

### 6. Access Dashboard
Open your browser: http://localhost:5000

##  Project Structure

```
wildlife-monitoring-system/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── database/
│   ├── db_manager.py      # Database operations
│   └── mongo.py           # MongoDB integration
├── utils/
│   ├── detection_logic.py # YOLO detection logic
│   ├── email_alert.py     # Email notification system
│   ├── image_save.py      # Snapshot management
│   └── video_recorder.py  # Video clip recording
├── static/
│   ├── script.js          # Frontend JavaScript
│   └── style.css          # Stylesheet
├── templates/
│   └── index.html         # Dashboard template
├── snapshots/             # Captured threat images
└── recordings/            # Video clip recordings
```

##  Configuration

### Email Setup (Gmail)
1. Enable 2-Step Verification at https://myaccount.google.com/security
2. Create App Password at https://myaccount.google.com/apppasswords
3. Use the 16-character password in `config.py`

### Camera Configuration
```python
CAMERAS = [
    {
        "id": "CAM_001",
        "name": "Main Camera",
        "source": 0,  # Webcam index
        "enabled": True
    },
    {
        "id": "CAM_002",
        "name": "IP Camera",
        "source": "rtsp://user:pass@192.168.1.100:554/stream",
        "enabled": True
    }
]
```

### Detection Classes
The system detects:
- **Humans**: person
- **Vehicles**: car, truck, bus, motorcycle, bicycle
- **Wildlife**: elephant, bear, zebra, giraffe, bird, cat, dog, etc.

##  API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/video_feed` | GET | Live video stream |
| `/video_feed/<camera_id>` | GET | Specific camera stream |
| `/cameras` | GET | List all cameras |
| `/alerts` | GET | Get recent alerts |
| `/stats` | GET | Get statistics |
| `/current_status` | GET | Current detection status |
| `/toggle_system` | POST | Enable/disable detection |
| `/upload` | POST | Upload image for analysis |
