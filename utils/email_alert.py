"""
Email Alert System for Wildlife Monitoring System
Sends email notifications with detection snapshots to officers
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
import os
import config

def send_alert_email(detection_type: str, confidence: float, image_path: str, 
                     camera_id: str = None) -> bool:
    """
    Send email alert with detection snapshot
    
    Args:
        detection_type: Type of detection (e.g., "person", "car")
        confidence: Confidence score (0.0 to 1.0)
        image_path: Path to snapshot image
        camera_id: Camera identifier (uses config if not provided)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not config.ENABLE_EMAIL:
        print("⚠ Email alerts disabled in config")
        return False
    
    # Validate email configuration
    if config.SENDER_EMAIL == "your-email@gmail.com" or config.SENDER_PASSWORD == "your-app-password":
        print("⚠ Email not configured. Please update config.py with your Gmail credentials")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = config.OFFICER_EMAIL
        msg['Subject'] = f"⚠ WILDLIFE ALERT: {detection_type.upper()} DETECTED"
        
        # Email body
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        camera = camera_id or config.CAMERA_ID
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .alert-box {{ 
                    background-color: #ff4444; 
                    color: white; 
                    padding: 20px; 
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .info-table {{ 
                    border-collapse: collapse; 
                    width: 100%; 
                    margin: 20px 0;
                }}
                .info-table td {{ 
                    padding: 10px; 
                    border: 1px solid #ddd; 
                }}
                .info-table td:first-child {{ 
                    font-weight: bold; 
                    background-color: #f0f0f0; 
                    width: 150px;
                }}
            </style>
        </head>
        <body>
            <div class="alert-box">
                <h2>⚠ THREAT DETECTED IN WILDLIFE ZONE</h2>
            </div>
            
            <p>An automated alert has been triggered by the Wildlife Monitoring System.</p>
            
            <table class="info-table">
                <tr>
                    <td>Detection Type</td>
                    <td><strong>{detection_type.upper()}</strong></td>
                </tr>
                <tr>
                    <td>Confidence</td>
                    <td>{confidence * 100:.1f}%</td>
                </tr>
                <tr>
                    <td>Camera ID</td>
                    <td>{camera}</td>
                </tr>
                <tr>
                    <td>Timestamp</td>
                    <td>{timestamp}</td>
                </tr>
            </table>
            
            <p><strong>Action Required:</strong> Please review the attached snapshot and take appropriate action.</p>
            
            <p style="color: #666; font-size: 12px;">
                This is an automated message from the Wildlife Monitoring System. 
                Do not reply to this email.
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Attach image if exists
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                img_data = f.read()
                image = MIMEImage(img_data, name=os.path.basename(image_path))
                msg.attach(image)
        else:
            print(f"⚠ Warning: Image not found at {image_path}")
        
        # Send email
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ Email alert sent to {config.OFFICER_EMAIL}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("✗ Email authentication failed. Please check your Gmail App Password")
        return False
    except Exception as e:
        print(f"✗ Failed to send email: {str(e)}")
        return False

def test_email_configuration() -> bool:
    """
    Test email configuration by sending a test email
    
    Returns:
        True if test email sent successfully, False otherwise
    """
    print("Testing email configuration...")
    
    # Check if configured
    if config.SENDER_EMAIL == "your-email@gmail.com":
        print("✗ Email not configured. Please update config.py")
        return False
    
    try:
        # Create test message
        msg = MIMEMultipart()
        msg['From'] = config.SENDER_EMAIL
        msg['To'] = config.OFFICER_EMAIL
        msg['Subject'] = "Wildlife Monitoring System - Test Email"
        
        body = """
        <html>
        <body>
            <h2>✓ Email Configuration Test</h2>
            <p>This is a test email from the Wildlife Monitoring System.</p>
            <p>If you received this email, your email configuration is working correctly!</p>
            <p style="color: #666; font-size: 12px;">
                Sent at: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send test email
        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.SENDER_EMAIL, config.SENDER_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ Test email sent successfully to {config.OFFICER_EMAIL}")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("✗ Authentication failed. Please check your Gmail App Password")
        print("   1. Go to https://myaccount.google.com/apppasswords")
        print("   2. Generate a new app password")
        print("   3. Update SENDER_PASSWORD in config.py")
        return False
    except Exception as e:
        print(f"✗ Email test failed: {str(e)}")
        return False

# Test function
if __name__ == "__main__":
    print("Email Alert System Test")
    print("=" * 50)
    test_email_configuration()
