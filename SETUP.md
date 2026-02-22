# Wildlife Monitoring System - Setup & Deployment Guide

##  Quick Start

### 1. Create Virtual Environment (Recommended)
```bash
python -m venv env
# Windows
.\env\Scripts\activate
# Linux/Mac
source env/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Settings
Edit `config.py` and update:

**Email Configuration:**
- `SENDER_EMAIL` - Your Gmail address
- `SENDER_PASSWORD` - Gmail App Password (16 chars)
- `OFFICER_EMAIL` - Alert recipient email

**Detection Settings:**
- `CONFIDENCE_THRESHOLD` - Detection sensitivity (0.0 to 1.0, default: 0.5)
- `DETECTION_CLASSES` - Objects to detect (persons, vehicles, animals)

**Camera Settings:**
- Webcam: Use integer index (0, 1, 2)
- IP Camera: Use RTSP URL
- Video file: Use file path

### 4. Run the System
```bash
python app.py
```

### 5. Access Dashboard
Open browser: http://localhost:5000

---

##  Gmail App Password Setup
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to https://myaccount.google.com/apppasswords
4. Create app password for "Mail"
5. Copy 16-character password to config.py

---

##  Features

### Live Camera Tab
- Multi-camera support
- Real-time object detection
- Live detection counts (Persons, Vehicles, Animals)
- Threat alerts with severity levels

### Image Detection Tab
- Upload images for analysis
- Drag & drop support

### Alerts Gallery
- View all captured threat images
- Filter by severity (Critical/High/Medium/Low)
- Filter by detection type

### Recordings
- Auto-recorded video clips
- Download and playback support

### Statistics
- Detection trends and charts
- Daily/Weekly/Monthly analysis

---

##  Deployment Options

### Option 1: Local Deployment
```bash
python app.py
```
Access at: http://localhost:5000

### Option 2: Production Deployment (Gunicorn)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 3: Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### Option 4: Cloud Deployment
- **Heroku**: Add Procfile with `web: python app.py`
- **AWS EC2**: Install dependencies & run with systemd
- **Railway/Render**: Connect GitHub repo

---

##  Testing

### Test Email Alerts
```bash
python utils/email_alert.py
```

### Test Database
```bash
python database/db_manager.py
```

### Test Detection
```bash
python utils/detection_logic.py
```

---

##  Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not working | Check camera index in config.py, try 0, 1, or 2 |
| Email fails | Verify Gmail App Password is correct |
| YOLO download fails | Check internet connection, model downloads on first run |
| Module not found | Run `pip install -r requirements.txt` |
| Port in use | Change port in app.py or kill existing process |

---

##  Project Structure

```
WILDLIFE PROJECT/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── yolov8n.pt            # YOLO model (auto-downloads)
├── database/
│   ├── db_manager.py     # SQLite database manager
│   └── alerts.db         # Alert database
├── utils/
│   ├── detection_logic.py # YOLO detection logic
│   ├── email_alert.py     # Email notification
│   ├── image_save.py      # Snapshot saving
│   └── video_recorder.py  # Video recording
├── templates/
│   └── index.html         # Main dashboard
├── static/
│   ├── script.js          # Frontend JavaScript
│   └── style.css          # Styling
├── snapshots/             # Saved detection images
└── alerts/                # Recorded video clips
```

---

##  Detection Classes

The system detects:
- **Humans**: person
- **Vehicles**: car, truck, bus, motorcycle, bicycle
- **Animals**: bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe

---

##  Support

For issues or questions, check the troubleshooting section above or review the application logs.
