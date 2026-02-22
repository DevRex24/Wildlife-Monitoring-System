"""
Video Recording Utility for Wildlife Monitoring System
Records short video clips when threats are detected
"""

import cv2
import os
import threading
from datetime import datetime
from collections import deque
import config

# Global frame buffer to store recent frames
frame_buffer = deque(maxlen=90)  # Store ~3 seconds at 30fps
buffer_lock = threading.Lock()
is_recording = False
recording_lock = threading.Lock()

# Video settings
VIDEO_DIR = "recordings"
PRE_RECORD_SECONDS = 10  # Seconds to include before detection
POST_RECORD_SECONDS = 15  # Seconds to record after detection
FPS = 30

def ensure_video_directory():
    """Create video directory if it doesn't exist"""
    if not os.path.exists(VIDEO_DIR):
        os.makedirs(VIDEO_DIR)
        print(f"✓ Created video directory: {VIDEO_DIR}")

def add_frame_to_buffer(frame):
    """Add a frame to the circular buffer"""
    with buffer_lock:
        frame_buffer.append(frame.copy())

def get_buffer_frames():
    """Get all frames from the buffer"""
    with buffer_lock:
        return list(frame_buffer)

def record_video_clip(detection_type: str, camera=None) -> str:
    """
    Record a video clip when threat is detected.
    Uses buffered frames for pre-detection footage and records post-detection.
    
    Args:
        detection_type: Type of detection (e.g., "person", "car")
        camera: OpenCV camera object for recording post-detection frames
    
    Returns:
        Path to saved video file, or empty string if recording failed
    """
    global is_recording
    
    # Check if already recording
    with recording_lock:
        if is_recording:
            return ""
        is_recording = True
    
    try:
        ensure_video_directory()
        
        # Generate filename with timestamp
        timestamp = datetime.now()
        date_folder = timestamp.strftime("%Y-%m-%d")
        
        # Create date subfolder
        date_path = os.path.join(VIDEO_DIR, date_folder)
        if not os.path.exists(date_path):
            os.makedirs(date_path)
        
        # Create filename
        time_str = timestamp.strftime("%H%M%S")
        safe_detection = detection_type.replace(" ", "_").replace(",", "")
        filename = f"clip_{time_str}_{safe_detection}.mp4"
        filepath = os.path.join(date_path, filename)
        
        # Get pre-detection frames from buffer
        pre_frames = get_buffer_frames()
        
        if not pre_frames:
            print("⚠ No buffered frames available for video recording")
            return ""
        
        # Get frame dimensions from buffer
        height, width = pre_frames[0].shape[:2]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filepath, fourcc, FPS, (width, height))
        
        if not out.isOpened():
            print("✗ Failed to create video writer")
            return ""
        
        # Write pre-detection frames (last PRE_RECORD_SECONDS worth)
        pre_frame_count = min(len(pre_frames), PRE_RECORD_SECONDS * FPS)
        for frame in pre_frames[-pre_frame_count:]:
            out.write(frame)
        
        # Record post-detection frames if camera is available
        if camera is not None and camera.isOpened():
            post_frame_count = POST_RECORD_SECONDS * FPS
            for _ in range(post_frame_count):
                ret, frame = camera.read()
                if ret:
                    out.write(frame)
                else:
                    break
        
        out.release()
        
        # Convert to relative path for storage
        relative_path = filepath.replace("\\", "/")
        
        print(f"🎬 Video recorded: {filepath}")
        return relative_path
        
    except Exception as e:
        print(f"✗ Video recording error: {e}")
        return ""
    
    finally:
        with recording_lock:
            is_recording = False

def record_video_async(detection_type: str, frame_copy=None, camera_id: str = "CAM_001") -> None:
    """
    Start video recording in a background thread.
    This version uses only buffered frames (no live camera access from thread).
    
    Args:
        detection_type: Type of detection
        frame_copy: Current frame to add to recording
        camera_id: ID of the camera that captured the detection
    """
    global is_recording
    
    # Check if already recording
    with recording_lock:
        if is_recording:
            return
        is_recording = True
    
    def record_task():
        global is_recording
        try:
            ensure_video_directory()
            
            # Generate filename with timestamp
            timestamp = datetime.now()
            date_folder = timestamp.strftime("%Y-%m-%d")
            
            # Create date subfolder
            date_path = os.path.join(VIDEO_DIR, date_folder)
            if not os.path.exists(date_path):
                os.makedirs(date_path)
            
            # Create filename with camera ID
            time_str = timestamp.strftime("%H%M%S")
            safe_detection = detection_type.replace(" ", "_").replace(",", "")
            filename = f"clip_{time_str}_{camera_id}_{safe_detection}.mp4"
            filepath = os.path.join(date_path, filename)
            
            # Get frames from buffer
            frames = get_buffer_frames()
            
            if not frames:
                print("⚠ No buffered frames available")
                return
            
            # Get frame dimensions
            height, width = frames[0].shape[:2]
            
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(filepath, fourcc, FPS, (width, height))
            
            if not out.isOpened():
                print(" Failed to create video writer")
                return
            
            # Write all buffered frames
            for frame in frames:
                out.write(frame)
            
            # Add the detection frame if provided
            if frame_copy is not None:
                for _ in range(FPS):  # Add 1 second of the detection frame
                    out.write(frame_copy)
            
            out.release()
            print(f"Video clip saved: {filepath}")
            
        except Exception as e:
            print(f" Video recording error: {e}")
        
        finally:
            with recording_lock:
                global is_recording
                is_recording = False
    
    # Start recording in background thread
    thread = threading.Thread(target=record_task, daemon=True)
    thread.start()

def get_video_relative_path(filepath: str) -> str:
    """Convert absolute path to relative path for database storage"""
    if os.path.isabs(filepath):
        try:
            return os.path.relpath(filepath).replace("\\", "/")
        except ValueError:
            return filepath.replace("\\", "/")
    return filepath.replace("\\", "/")

def cleanup_old_videos(days: int = 7):
    """
    Delete video recordings older than specified days
    
    Args:
        days: Number of days to keep recordings
    """
    if days <= 0:
        return
    
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    if not os.path.exists(VIDEO_DIR):
        return
    
    for date_folder in os.listdir(VIDEO_DIR):
        folder_path = os.path.join(VIDEO_DIR, date_folder)
        
        if not os.path.isdir(folder_path):
            continue
        
        try:
            folder_date = datetime.strptime(date_folder, "%Y-%m-%d")
            if folder_date < cutoff_date:
                # Delete all files in folder
                for file in os.listdir(folder_path):
                    os.remove(os.path.join(folder_path, file))
                    deleted_count += 1
                os.rmdir(folder_path)
        except (ValueError, OSError):
            continue
    
    if deleted_count > 0:
        print(f" Cleaned up {deleted_count} old video recordings")
