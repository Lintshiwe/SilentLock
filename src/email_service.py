"""
Email service for SilentLock 2FA OTP codes.
Handles secure email delivery for authentication.
"""

import smtplib
import ssl
import secrets
import time
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import threading


class EmailOTPService:
    """Email-based OTP service for 2FA authentication."""
    
    def __init__(self):
        self.active_codes = {}  # Store active OTP codes
        self.code_expiry = 300  # 5 minutes
        self.smtp_config = self._load_smtp_config()
        self.cleanup_thread = None
        self._start_cleanup_thread()
    
    def _load_smtp_config(self) -> Dict:
        """Load SMTP configuration from config file or use defaults."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'email_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        
        # Default configuration for common email providers
        return {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "from_email": "",  # To be configured by user
            "from_password": "",  # To be configured by user (app password)
            "from_name": "SilentLock Security"
        }
    
    def configure_email_settings(self, smtp_server: str, smtp_port: int, 
                                email: str, password: str, use_tls: bool = True,
                                from_name: str = "SilentLock Security") -> Dict:
        """Configure email settings for OTP delivery."""
        try:
            # Test the configuration
            test_result = self._test_smtp_connection(smtp_server, smtp_port, email, password, use_tls)
            if not test_result['success']:
                return test_result
            
            # Save configuration
            self.smtp_config.update({
                "smtp_server": smtp_server,
                "smtp_port": smtp_port,
                "use_tls": use_tls,
                "from_email": email,
                "from_password": password,
                "from_name": from_name
            })
            
            # Save to file
            self._save_smtp_config()
            
            return {'success': True, 'message': 'Email configuration saved successfully'}
            
        except Exception as e:
            return {'success': False, 'error': f'Configuration failed: {str(e)}'}
    
    def _test_smtp_connection(self, smtp_server: str, smtp_port: int, 
                            email: str, password: str, use_tls: bool) -> Dict:
        """Test SMTP connection with provided credentials."""
        try:
            if use_tls:
                context = ssl.create_default_context()
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls(context=context)
            else:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            
            server.login(email, password)
            server.quit()
            
            return {'success': True, 'message': 'SMTP connection successful'}
            
        except smtplib.SMTPAuthenticationError:
            return {'success': False, 'error': 'Invalid email credentials'}
        except smtplib.SMTPConnectError:
            return {'success': False, 'error': 'Cannot connect to SMTP server'}
        except Exception as e:
            return {'success': False, 'error': f'Connection test failed: {str(e)}'}
    
    def _save_smtp_config(self):
        """Save SMTP configuration to file."""
        try:
            config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, 'email_config.json')
            
            # Don't save password in plain text - this is a basic implementation
            # In production, use proper encryption for stored credentials
            with open(config_path, 'w') as f:
                json.dump(self.smtp_config, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not save email config: {e}")
    
    def generate_otp_code(self, email: str, purpose: str = "login") -> Dict:
        """Generate and store a new OTP code for email delivery."""
        try:
            # Generate 6-digit OTP code
            otp_code = str(secrets.randbelow(900000) + 100000)
            
            # Create code entry
            code_id = f"{email}:{purpose}:{int(time.time())}"
            expiry_time = datetime.now() + timedelta(seconds=self.code_expiry)
            
            code_data = {
                'code': otp_code,
                'email': email,
                'purpose': purpose,
                'created_at': datetime.now(),
                'expires_at': expiry_time,
                'attempts': 0,
                'max_attempts': 3
            }
            
            # Store code (remove any existing codes for same email/purpose)
            self._cleanup_codes_for_email(email, purpose)
            self.active_codes[code_id] = code_data
            
            return {
                'success': True,
                'code_id': code_id,
                'otp_code': otp_code,
                'expires_at': expiry_time.isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': f'OTP generation failed: {str(e)}'}
    
    def send_otp_email(self, email: str, otp_code: str, purpose: str = "login") -> Dict:
        """Send OTP code via email."""
        try:
            if not self.smtp_config.get('from_email'):
                return {'success': False, 'error': 'Email service not configured'}
            
            # Create email message
            message = MIMEMultipart("alternative")
            message["Subject"] = f"SilentLock Security Code - {purpose.title()}"
            message["From"] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
            message["To"] = email
            
            # Create HTML and text versions
            text_body = self._create_text_email(otp_code, purpose)
            html_body = self._create_html_email(otp_code, purpose)
            
            text_part = MIMEText(text_body, "plain")
            html_part = MIMEText(html_body, "html")
            
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            if self.smtp_config['use_tls']:
                context = ssl.create_default_context()
                server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
                server.starttls(context=context)
            else:
                server = smtplib.SMTP_SSL(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
            
            server.login(self.smtp_config['from_email'], self.smtp_config['from_password'])
            server.send_message(message)
            server.quit()
            
            return {'success': True, 'message': f'OTP code sent to {email}'}
            
        except Exception as e:
            return {'success': False, 'error': f'Email delivery failed: {str(e)}'}
    
    def _create_text_email(self, otp_code: str, purpose: str) -> str:
        """Create plain text email content."""
        return f"""
SilentLock Password Manager - Security Code

Your verification code for {purpose}: {otp_code}

This code will expire in {self.code_expiry // 60} minutes.

If you did not request this code, please ignore this email.

For security reasons, do not share this code with anyone.

---
SilentLock Password Manager
Secure, Professional Password Management
        """.strip()
    
    def _create_html_email(self, otp_code: str, purpose: str) -> str:
        """Create HTML email content."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
                .content {{ background: #f8f9fa; padding: 30px; border-radius: 0 0 8px 8px; }}
                .otp-code {{ 
                    font-size: 32px; 
                    font-weight: bold; 
                    letter-spacing: 8px; 
                    text-align: center; 
                    background: #e74c3c; 
                    color: white; 
                    padding: 15px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                }}
                .warning {{ 
                    background: #fff3cd; 
                    border: 1px solid #ffeaa7; 
                    padding: 15px; 
                    border-radius: 5px; 
                    margin-top: 20px; 
                }}
                .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 SilentLock Security</h1>
                    <p>Password Manager Verification</p>
                </div>
                <div class="content">
                    <h2>Verification Code for {purpose.title()}</h2>
                    <p>Your verification code is:</p>
                    <div class="otp-code">{otp_code}</div>
                    <p><strong>This code will expire in {self.code_expiry // 60} minutes.</strong></p>
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong><br>
                        • If you did not request this code, please ignore this email<br>
                        • Do not share this code with anyone<br>
                        • SilentLock will never ask for your code via phone or email
                    </div>
                </div>
                <div class="footer">
                    SilentLock Password Manager<br>
                    Secure, Professional Password Management
                </div>
            </div>
        </body>
        </html>
        """
    
    def verify_otp_code(self, email: str, provided_code: str, purpose: str = "login") -> Dict:
        """Verify an OTP code for given email and purpose."""
        try:
            # Find active code for this email/purpose
            code_entry = None
            code_id = None
            
            for cid, data in self.active_codes.items():
                if (data['email'] == email and 
                    data['purpose'] == purpose and 
                    datetime.now() < data['expires_at']):
                    code_entry = data
                    code_id = cid
                    break
            
            if not code_entry:
                return {'success': False, 'error': 'No valid code found or code expired'}
            
            # Check attempt limit
            if code_entry['attempts'] >= code_entry['max_attempts']:
                del self.active_codes[code_id]
                return {'success': False, 'error': 'Too many verification attempts'}
            
            # Verify code
            if provided_code.strip() == code_entry['code']:
                # Code is valid - remove it
                del self.active_codes[code_id]
                return {
                    'success': True,
                    'message': 'Code verified successfully',
                    'verified_at': datetime.now().isoformat()
                }
            else:
                # Increment attempts
                code_entry['attempts'] += 1
                return {
                    'success': False, 
                    'error': f'Invalid code. {code_entry["max_attempts"] - code_entry["attempts"]} attempts remaining'
                }
                
        except Exception as e:
            return {'success': False, 'error': f'Verification failed: {str(e)}'}
    
    def _cleanup_codes_for_email(self, email: str, purpose: str):
        """Remove existing codes for email/purpose combination."""
        to_remove = []
        for code_id, data in self.active_codes.items():
            if data['email'] == email and data['purpose'] == purpose:
                to_remove.append(code_id)
        
        for code_id in to_remove:
            del self.active_codes[code_id]
    
    def _cleanup_expired_codes(self):
        """Remove expired OTP codes."""
        now = datetime.now()
        expired_codes = []
        
        for code_id, data in self.active_codes.items():
            if now >= data['expires_at']:
                expired_codes.append(code_id)
        
        for code_id in expired_codes:
            del self.active_codes[code_id]
    
    def _start_cleanup_thread(self):
        """Start background thread for cleaning expired codes."""
        def cleanup_worker():
            while True:
                try:
                    self._cleanup_expired_codes()
                    time.sleep(60)  # Cleanup every minute
                except Exception:
                    pass
        
        if not self.cleanup_thread or not self.cleanup_thread.is_alive():
            self.cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
            self.cleanup_thread.start()
    
    def get_active_codes_count(self) -> int:
        """Get count of active OTP codes (for monitoring)."""
        return len(self.active_codes)
    
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_config.get('from_email') and self.smtp_config.get('from_password'))

    def get_smtp_config_status(self) -> Dict:
        """Get current SMTP configuration status (without sensitive data)."""
        return {
            'configured': self.is_configured(),
            'smtp_server': self.smtp_config.get('smtp_server', ''),
            'smtp_port': self.smtp_config.get('smtp_port', 0),
            'from_email': self.smtp_config.get('from_email', ''),
            'use_tls': self.smtp_config.get('use_tls', True),
            'from_name': self.smtp_config.get('from_name', ''),
            'has_password': bool(self.smtp_config.get('from_password'))
        }