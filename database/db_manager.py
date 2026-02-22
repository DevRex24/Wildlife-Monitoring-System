"""
SQLite Database Manager for Wildlife Monitoring System
Handles all database operations for alert logging and retrieval
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import config

def get_db_connection():
    """Create and return a database connection"""
    # Ensure database directory exists
    db_dir = os.path.dirname(config.DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            detection_type TEXT NOT NULL,
            confidence REAL NOT NULL,
            camera_id TEXT NOT NULL,
            image_path TEXT,
            email_sent BOOLEAN DEFAULT 0,
            notes TEXT
        )
    ''')
    
    # Create index on timestamp for faster queries
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp 
        ON alerts(timestamp DESC)
    ''')
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully")

def log_alert(detection_type: str, confidence: float, image_path: str, 
              email_sent: bool = False, notes: str = "") -> int:
    """
    Log a new alert to the database
    
    Args:
        detection_type: Type of detection (e.g., "person", "car")
        confidence: Confidence score (0.0 to 1.0)
        image_path: Path to saved snapshot image
        email_sent: Whether email was sent successfully
        notes: Additional notes
    
    Returns:
        Alert ID of the inserted record
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO alerts (detection_type, confidence, camera_id, image_path, email_sent, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (detection_type, confidence, config.CAMERA_ID, image_path, email_sent, notes))
    
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return alert_id

def get_recent_alerts(limit: int = 50) -> List[Dict]:
    """
    Retrieve recent alerts from the database
    
    Args:
        limit: Maximum number of alerts to retrieve
    
    Returns:
        List of alert dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, timestamp, detection_type, confidence, camera_id, 
               image_path, email_sent, notes
        FROM alerts
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    
    alerts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return alerts

def get_alert_stats() -> Dict:
    """
    Get alert statistics for the dashboard
    
    Returns:
        Dictionary with statistics
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Total alerts
    cursor.execute('SELECT COUNT(*) as total FROM alerts')
    total_alerts = cursor.fetchone()['total']
    
    # Today's alerts
    today = datetime.now().date()
    cursor.execute('''
        SELECT COUNT(*) as today_count 
        FROM alerts 
        WHERE DATE(timestamp) = ?
    ''', (today,))
    today_alerts = cursor.fetchone()['today_count']
    
    # This week's alerts
    week_ago = datetime.now() - timedelta(days=7)
    cursor.execute('''
        SELECT COUNT(*) as week_count 
        FROM alerts 
        WHERE timestamp >= ?
    ''', (week_ago,))
    week_alerts = cursor.fetchone()['week_count']
    
    # Most common detection type
    cursor.execute('''
        SELECT detection_type, COUNT(*) as count
        FROM alerts
        GROUP BY detection_type
        ORDER BY count DESC
        LIMIT 1
    ''')
    most_common_row = cursor.fetchone()
    most_common = most_common_row['detection_type'] if most_common_row else "None"
    
    # Email success rate
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN email_sent = 1 THEN 1 ELSE 0 END) as sent
        FROM alerts
    ''')
    email_stats = cursor.fetchone()
    email_rate = (email_stats['sent'] / email_stats['total'] * 100) if email_stats['total'] > 0 else 0
    
    conn.close()
    
    return {
        'total_alerts': total_alerts,
        'today_alerts': today_alerts,
        'week_alerts': week_alerts,
        'most_common_detection': most_common,
        'email_success_rate': round(email_rate, 1)
    }

def get_alert_by_id(alert_id: int) -> Optional[Dict]:
    """
    Get a specific alert by ID
    
    Args:
        alert_id: Alert ID to retrieve
    
    Returns:
        Alert dictionary or None if not found
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, timestamp, detection_type, confidence, camera_id, 
               image_path, email_sent, notes
        FROM alerts
        WHERE id = ?
    ''', (alert_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None

def update_email_status(alert_id: int, email_sent: bool):
    """
    Update email sent status for an alert
    
    Args:
        alert_id: Alert ID to update
        email_sent: New email sent status
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE alerts
        SET email_sent = ?
        WHERE id = ?
    ''', (email_sent, alert_id))
    
    conn.commit()
    conn.close()

def delete_old_alerts(days: int = 30):
    """
    Delete alerts older than specified days
    
    Args:
        days: Number of days to keep
    """
    if days <= 0:
        return  # Don't delete if retention is 0 (keep forever)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cutoff_date = datetime.now() - timedelta(days=days)
    cursor.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff_date,))
    
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted_count > 0:
        print(f"✓ Deleted {deleted_count} old alerts")

def get_chart_data(time_range: str = 'daily') -> Dict:
    """
    Get chart data for statistics dashboard
    
    Args:
        time_range: 'daily', 'weekly', or 'monthly'
    
    Returns:
        Dictionary with chart data
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now()
    
    # Trend data based on time range
    if time_range == 'daily':
        # Last 7 days
        labels = []
        values = []
        for i in range(6, -1, -1):
            date = (now - timedelta(days=i)).date()
            labels.append(date.strftime('%a'))
            cursor.execute('''
                SELECT COUNT(*) as count FROM alerts 
                WHERE DATE(timestamp) = ?
            ''', (date,))
            values.append(cursor.fetchone()['count'])
    
    elif time_range == 'weekly':
        # Last 4 weeks
        labels = []
        values = []
        for i in range(3, -1, -1):
            week_start = now - timedelta(weeks=i, days=now.weekday())
            week_end = week_start + timedelta(days=6)
            labels.append(f"Week {4-i}")
            cursor.execute('''
                SELECT COUNT(*) as count FROM alerts 
                WHERE DATE(timestamp) >= ? AND DATE(timestamp) <= ?
            ''', (week_start.date(), week_end.date()))
            values.append(cursor.fetchone()['count'])
    
    else:  # monthly
        # Last 6 months
        labels = []
        values = []
        for i in range(5, -1, -1):
            month_date = now - timedelta(days=i*30)
            month_name = month_date.strftime('%b')
            labels.append(month_name)
            cursor.execute('''
                SELECT COUNT(*) as count FROM alerts 
                WHERE strftime('%Y-%m', timestamp) = ?
            ''', (month_date.strftime('%Y-%m'),))
            values.append(cursor.fetchone()['count'])
    
    # Detection types distribution
    cursor.execute('''
        SELECT detection_type, COUNT(*) as count
        FROM alerts
        GROUP BY detection_type
    ''')
    type_data = cursor.fetchall()
    type_labels = [row['detection_type'] for row in type_data]
    type_values = [row['count'] for row in type_data]
    
    # Hourly distribution
    hourly_values = [0] * 24
    cursor.execute('''
        SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
        FROM alerts
        GROUP BY hour
    ''')
    for row in cursor.fetchall():
        hour_idx = int(row['hour'])
        hourly_values[hour_idx] = row['count']
    
    # Weekly comparison (this week vs last week by day)
    this_week = []
    last_week = []
    day_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    for i in range(7):
        # This week
        this_week_date = (now - timedelta(days=now.weekday()) + timedelta(days=i)).date()
        cursor.execute('''
            SELECT COUNT(*) as count FROM alerts 
            WHERE DATE(timestamp) = ?
        ''', (this_week_date,))
        this_week.append(cursor.fetchone()['count'])
        
        # Last week
        last_week_date = this_week_date - timedelta(weeks=1)
        cursor.execute('''
            SELECT COUNT(*) as count FROM alerts 
            WHERE DATE(timestamp) = ?
        ''', (last_week_date,))
        last_week.append(cursor.fetchone()['count'])
    
    conn.close()
    
    return {
        'trend': {
            'labels': labels,
            'values': values
        },
        'types': {
            'labels': type_labels if type_labels else ['No Data'],
            'values': type_values if type_values else [0]
        },
        'hourly': {
            'labels': [f'{i:02d}:00' for i in range(24)],
            'values': hourly_values
        },
        'weekly': {
            'labels': day_labels,
            'thisWeek': this_week,
            'lastWeek': last_week
        }
    }

# Initialize database on module import
if __name__ == "__main__":
    init_database()
    print("Database setup complete!")
