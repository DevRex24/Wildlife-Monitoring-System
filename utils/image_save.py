"""
Image Saving Utility for Wildlife Monitoring System
Handles saving detection snapshots with organized file structure
"""

import cv2
import os
from datetime import datetime
import config

def ensure_snapshot_directory():
    """Create snapshot directory if it doesn't exist"""
    if not os.path.exists(config.SNAPSHOT_DIR):
        os.makedirs(config.SNAPSHOT_DIR)
        print(f"✓ Created snapshot directory: {config.SNAPSHOT_DIR}")

def save_snapshot(frame, detection_info: str = "") -> str:
    """
    Save a detection snapshot with timestamp
    
    Args:
        frame: Image frame to save (numpy array)
        detection_info: Optional detection information for filename
    
    Returns:
        Path to saved image file
    """
    ensure_snapshot_directory()
    
    # Generate filename with timestamp - use CURRENT time when clicking/saving
    timestamp = datetime.now()
    date_folder = timestamp.strftime("%Y-%m-%d")
    
    # Create date subfolder
    date_path = os.path.join(config.SNAPSHOT_DIR, date_folder)
    if not os.path.exists(date_path):
        os.makedirs(date_path)
    
    # Create filename with current timestamp
    time_str = timestamp.strftime("%H%M%S")
    filename = f"alert_{time_str}"
    
    if detection_info:
        # Sanitize detection info for filename
        safe_info = detection_info.replace(" ", "_").replace(",", "")
        filename += f"_{safe_info}"
    
    filename += ".jpg"
    
    # Full path
    filepath = os.path.join(date_path, filename)
    
    # Add timestamp overlay on the image
    frame_with_timestamp = frame.copy()
    timestamp_text = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    # Get frame dimensions
    height, width = frame_with_timestamp.shape[:2]
    
    # Add black background rectangle for better visibility
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2
    text_size = cv2.getTextSize(timestamp_text, font, font_scale, thickness)[0]
    
    # Position at bottom-left corner
    text_x = 10
    text_y = height - 15
    
    # Draw background rectangle
    cv2.rectangle(frame_with_timestamp, 
                  (text_x - 5, text_y - text_size[1] - 5),
                  (text_x + text_size[0] + 5, text_y + 5),
                  (0, 0, 0), -1)
    
    # Draw timestamp text
    cv2.putText(frame_with_timestamp, timestamp_text, (text_x, text_y),
                font, font_scale, (255, 255, 255), thickness)
    
    # Save image with timestamp overlay
    cv2.imwrite(filepath, frame_with_timestamp)
    
    return filepath

def get_relative_path(absolute_path: str) -> str:
    """
    Convert absolute path to relative path from project root
    
    Args:
        absolute_path: Absolute file path
    
    Returns:
        Relative path string
    """
    # Get relative path for database storage
    if os.path.isabs(absolute_path):
        try:
            return os.path.relpath(absolute_path)
        except ValueError:
            return absolute_path
    return absolute_path

def cleanup_old_snapshots(days: int = None):
    """
    Delete snapshots older than specified days
    
    Args:
        days: Number of days to keep (uses config if not specified)
    """
    if days is None:
        days = config.IMAGE_RETENTION_DAYS
    
    if days <= 0:
        return  # Keep forever
    
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    
    if not os.path.exists(config.SNAPSHOT_DIR):
        return
    
    # Iterate through date folders
    for date_folder in os.listdir(config.SNAPSHOT_DIR):
        folder_path = os.path.join(config.SNAPSHOT_DIR, date_folder)
        
        if not os.path.isdir(folder_path):
            continue
        
        try:
            # Parse folder date
            folder_date = datetime.strptime(date_folder, "%Y-%m-%d")
            
            # Delete if older than cutoff
            if folder_date < cutoff_date:
                import shutil
                shutil.rmtree(folder_path)
                deleted_count += 1
                print(f"✓ Deleted old snapshot folder: {date_folder}")
        except ValueError:
            # Skip folders that don't match date format
            continue
    
    if deleted_count > 0:
        print(f"✓ Cleaned up {deleted_count} old snapshot folders")

def get_snapshot_count() -> int:
    """
    Get total number of saved snapshots
    
    Returns:
        Total count of snapshot images
    """
    if not os.path.exists(config.SNAPSHOT_DIR):
        return 0
    
    count = 0
    for root, dirs, files in os.walk(config.SNAPSHOT_DIR):
        count += len([f for f in files if f.endswith(('.jpg', '.jpeg', '.png'))])
    
    return count

def get_latest_snapshot() -> str:
    """
    Get path to the most recent snapshot
    
    Returns:
        Path to latest snapshot or None if no snapshots exist
    """
    if not os.path.exists(config.SNAPSHOT_DIR):
        return None
    
    latest_file = None
    latest_time = None
    
    for root, dirs, files in os.walk(config.SNAPSHOT_DIR):
        for file in files:
            if file.endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(root, file)
                file_time = os.path.getmtime(filepath)
                
                if latest_time is None or file_time > latest_time:
                    latest_time = file_time
                    latest_file = filepath
    
    return latest_file

# Test function
if __name__ == "__main__":
    print("Testing image save utility...")
    ensure_snapshot_directory()
    
    # Create a test image
    import numpy as np
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(test_frame, "TEST SNAPSHOT", (200, 240), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Save test snapshot
    saved_path = save_snapshot(test_frame, "test_detection")
    print(f"✓ Test snapshot saved: {saved_path}")
    
    # Get stats
    count = get_snapshot_count()
    print(f"✓ Total snapshots: {count}")
    
    latest = get_latest_snapshot()
    print(f"✓ Latest snapshot: {latest}")
