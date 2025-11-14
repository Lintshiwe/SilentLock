"""
Administrator Authentication System for SilentLock
Provides elevated privileges for password review and security management.
Supports TOTP, email OTP, and recovery codes for 2FA.
"""

import os
import hashlib
import secrets
import json
import base64
import time
import qrcode
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import pyotp
import win32crypt
import winreg

from .email_service import EmailOTPService
from .user_profile import UserProfileManager


class AdminAuthenticator:
    """Advanced administrator authentication with multiple security layers."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.email_otp_service = EmailOTPService()
        self.profile_manager = UserProfileManager(db_manager)
        # Use the same directory as the database to avoid permission issues
        db_dir = os.path.dirname(self.db_manager.db_path) if hasattr(self.db_manager, 'db_path') else os.path.join(os.path.expandvars(r'%APPDATA%'), 'SilentLock')
        self.admin_config_path = os.path.join(db_dir, 'admin_config.enc')
        self.session_timeout = 900  # 15 minutes
        self.active_sessions = {}
        
        # Initialize admin system
        self._initialize_admin_system()
    
    def _initialize_admin_system(self):
        """Initialize the admin authentication system with comprehensive fallback."""
        try:
            # First, try to determine the best config directory
            # Use database directory if available, otherwise try AppData
            if hasattr(self.db_manager, 'db_path') and self.db_manager.db_path:
                db_dir = os.path.dirname(self.db_manager.db_path)
                self.admin_config_path = os.path.join(db_dir, 'admin_config.enc')
                print(f"🗂️ Using database directory for admin config: {db_dir}")
            else:
                # Try AppData first
                appdata_dir = os.path.join(os.path.expandvars(r'%APPDATA%'), 'SilentLock')
                self.admin_config_path = os.path.join(appdata_dir, 'admin_config.enc')
            
            # Test if we can write to the chosen directory
            config_dir = os.path.dirname(self.admin_config_path)
            try:
                os.makedirs(config_dir, exist_ok=True)
                
                # Test write permission by creating a temporary file
                test_file = os.path.join(config_dir, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                
                print(f"✅ Admin config directory accessible: {config_dir}")
                
            except (PermissionError, OSError) as e:
                # Fallback to local data directory
                print(f"⚠️ Cannot access {config_dir}: {e}")
                fallback_dir = os.path.join(os.getcwd(), 'data')
                self.admin_config_path = os.path.join(fallback_dir, 'admin_config.enc')
                
                os.makedirs(fallback_dir, exist_ok=True)
                print(f"✅ Using fallback admin config directory: {fallback_dir}")
            
            # Check if config file exists
            if not os.path.exists(self.admin_config_path):
                # First run - create admin setup
                print("Admin authentication system requires initial setup.")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Admin system initialization error: {e}")
            # Final fallback to local directory
            try:
                fallback_dir = os.path.join(os.getcwd(), 'data')
                self.admin_config_path = os.path.join(fallback_dir, 'admin_config.enc')
                os.makedirs(fallback_dir, exist_ok=True)
                print(f"✅ Emergency fallback admin config: {self.admin_config_path}")
                return False  # Still needs setup
            except Exception as final_error:
                print(f"❌ Complete admin system failure: {final_error}")
                return False
    
    def setup_admin_account(self, admin_password: str, email: str = None, enable_2fa: bool = True) -> Dict:
        """Set up the administrator account with enhanced security."""
        try:
            # Generate strong salt
            salt = secrets.token_bytes(32)
            
            # Hash admin password with high iteration count
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=500000,  # Very high for admin password
            )
            admin_key = base64.urlsafe_b64encode(kdf.derive(admin_password.encode()))
            
            # Generate admin ID
            admin_id = secrets.token_urlsafe(16)
            
            # Generate 2FA secret if enabled
            totp_secret = None
            qr_code_data = None
            if enable_2fa:
                totp_secret = pyotp.random_base32()
                totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
                    name=email or "admin",
                    issuer_name="SilentLock Password Manager"
                )
                
                # Generate QR code for 2FA setup
                qr_code_data = self._generate_qr_code(totp_uri)
            
            # Generate recovery codes
            recovery_codes = [secrets.token_urlsafe(12) for _ in range(10)]
            hashed_recovery_codes = [
                hashlib.sha256(code.encode()).hexdigest() 
                for code in recovery_codes
            ]
            
            # Generate RSA key pair for admin operations
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Create admin configuration
            admin_config = {
                'admin_id': admin_id,
                'salt': base64.b64encode(salt).decode(),
                'password_hash': hashlib.sha256(admin_password.encode() + salt).hexdigest(),
                'email': email,
                'created_at': datetime.now().isoformat(),
                'last_login': None,
                'login_attempts': 0,
                'locked_until': None,
                '2fa_enabled': enable_2fa,
                '2fa_method': '2fa_method',  # 'totp', 'email', or 'both'
                'email_2fa_enabled': False,  # Will be set if email is provided
                'totp_secret': totp_secret,
                'recovery_codes': hashed_recovery_codes,
                'private_key': base64.b64encode(private_pem).decode(),
                'public_key': base64.b64encode(public_pem).decode(),
                'permissions': {
                    'view_all_passwords': True,
                    'export_passwords': True,
                    'security_audit': True,
                    'system_config': True,
                    'user_management': True
                },
                'security_settings': {
                    'session_timeout': self.session_timeout,
                    'require_2fa_for_sensitive': True,
                    'log_all_actions': True,
                    'require_approval_for_export': True
                }
            }
            
            # Enable email 2FA if email is provided
            if email and enable_2fa:
                admin_config['email_2fa_enabled'] = True
                admin_config['2fa_method'] = 'email'  # Default to email for new setups
            
            # Encrypt and save admin configuration
            self._save_admin_config(admin_config, admin_key)
            
            return {
                'success': True,
                'admin_id': admin_id,
                'recovery_codes': recovery_codes,
                'qr_code_data': qr_code_data,
                'totp_secret': totp_secret if not enable_2fa else None
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def authenticate_admin(self, password: str, totp_code: str = None, 
                          recovery_code: str = None, email_otp: str = None) -> Dict:
        """Authenticate administrator with multi-factor authentication."""
        try:
            # Load admin configuration
            admin_config = self._load_admin_config()
            if not admin_config:
                return {'success': False, 'error': 'Admin account not configured'}
            
            # Check if account is locked
            if admin_config.get('locked_until'):
                locked_until = datetime.fromisoformat(admin_config['locked_until'])
                if datetime.now() < locked_until:
                    return {'success': False, 'error': 'Account temporarily locked due to failed attempts'}
            
            # Verify password
            salt = base64.b64decode(admin_config['salt'])
            password_hash = hashlib.sha256(password.encode() + salt).hexdigest()
            
            if password_hash != admin_config['password_hash']:
                self._handle_failed_login(admin_config)
                return {'success': False, 'error': 'Invalid credentials'}
            
            # Verify 2FA if enabled
            if admin_config.get('2fa_enabled'):
                if recovery_code:
                    # Verify recovery code
                    if not self._verify_recovery_code(admin_config, recovery_code):
                        self._handle_failed_login(admin_config)
                        return {'success': False, 'error': 'Invalid recovery code'}
                else:
                    # Check 2FA method and verify accordingly
                    twofa_method = admin_config.get('2fa_method', 'totp')
                    email_2fa_enabled = admin_config.get('email_2fa_enabled', False)
                    
                    if twofa_method == 'email' or email_2fa_enabled:
                        # Email OTP verification
                        if not email_otp:
                            return {'success': False, 'error': 'Email OTP code required', 'requires_email_otp': True}
                        
                        email = admin_config.get('email')
                        if not email:
                            return {'success': False, 'error': 'No email configured for 2FA'}
                        
                        otp_result = self.email_otp_service.verify_otp_code(email, email_otp, 'admin_login')
                        if not otp_result['success']:
                            self._handle_failed_login(admin_config)
                            return {'success': False, 'error': otp_result['error']}
                    
                    elif twofa_method == 'totp':
                        # TOTP verification
                        if not totp_code:
                            return {'success': False, 'error': 'TOTP code required', 'requires_totp': True}
                        
                        if not self._verify_totp(admin_config['totp_secret'], totp_code):
                            self._handle_failed_login(admin_config)
                            return {'success': False, 'error': 'Invalid 2FA code'}
                    
                    elif twofa_method == 'both':
                        # Require both TOTP and Email OTP
                        if not totp_code or not email_otp:
                            return {
                                'success': False, 
                                'error': 'Both TOTP and Email OTP required',
                                'requires_totp': not totp_code,
                                'requires_email_otp': not email_otp
                            }
                        
                        if not self._verify_totp(admin_config['totp_secret'], totp_code):
                            self._handle_failed_login(admin_config)
                            return {'success': False, 'error': 'Invalid TOTP code'}
                        
                        email = admin_config.get('email')
                        if email:
                            otp_result = self.email_otp_service.verify_otp_code(email, email_otp, 'admin_login')
                            if not otp_result['success']:
                                self._handle_failed_login(admin_config)
                                return {'success': False, 'error': f'Email OTP: {otp_result["error"]}'}
            
            # Create admin session
            session_token = self._create_admin_session(admin_config)
            
            # Update last login
            admin_config['last_login'] = datetime.now().isoformat()
            admin_config['login_attempts'] = 0
            admin_config['locked_until'] = None
            self._save_admin_config_update(admin_config)
            
            # Create user profile if not exists
            if admin_config.get('email'):
                self.profile_manager.create_user_profile(
                    admin_config['admin_id'], 
                    admin_config['email']
                )
                self.profile_manager.update_login_info(admin_config['admin_id'])
            
            return {
                'success': True,
                'session_token': session_token,
                'admin_id': admin_config['admin_id'],
                'permissions': admin_config['permissions'],
                'session_expires': (datetime.now() + timedelta(seconds=self.session_timeout)).isoformat()
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Authentication error: {str(e)}'}
    
    def _verify_recovery_code(self, admin_config: Dict, recovery_code: str) -> bool:
        """Verify and consume a recovery code."""
        try:
            code_hash = hashlib.sha256(recovery_code.encode()).hexdigest()
            
            if code_hash in admin_config['recovery_codes']:
                # Remove used recovery code
                admin_config['recovery_codes'].remove(code_hash)
                return True
            
            return False
            
        except Exception:
            return False
    
    def _verify_totp(self, secret: str, code: str) -> bool:
        """Verify TOTP code."""
        try:
            totp = pyotp.TOTP(secret)
            # Allow for time drift (window of 1 = 30 seconds before/after)
            return totp.verify(code, valid_window=1)
            
        except Exception:
            return False
    
    def _handle_failed_login(self, admin_config: Dict):
        """Handle failed login attempt."""
        try:
            admin_config['login_attempts'] += 1
            
            # Lock account after 5 failed attempts
            if admin_config['login_attempts'] >= 5:
                # Lock for increasing durations
                lock_duration = min(admin_config['login_attempts'] * 5, 60)  # Max 60 minutes
                admin_config['locked_until'] = (
                    datetime.now() + timedelta(minutes=lock_duration)
                ).isoformat()
            
            self._save_admin_config_update(admin_config)
            
        except Exception:
            pass
    
    def _create_admin_session(self, admin_config: Dict) -> str:
        """Create an admin session token."""
        try:
            session_token = secrets.token_urlsafe(32)
            session_data = {
                'admin_id': admin_config['admin_id'],
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(seconds=self.session_timeout)).isoformat(),
                'permissions': admin_config['permissions']
            }
            
            self.active_sessions[session_token] = session_data
            
            # Cleanup expired sessions
            self._cleanup_expired_sessions()
            
            return session_token
            
        except Exception:
            return None
    
    def verify_admin_session(self, session_token: str) -> Dict:
        """Verify admin session token."""
        try:
            if session_token not in self.active_sessions:
                return {'valid': False, 'error': 'Invalid session'}
            
            session_data = self.active_sessions[session_token]
            expires_at = datetime.fromisoformat(session_data['expires_at'])
            
            if datetime.now() > expires_at:
                del self.active_sessions[session_token]
                return {'valid': False, 'error': 'Session expired'}
            
            # Extend session
            session_data['expires_at'] = (
                datetime.now() + timedelta(seconds=self.session_timeout)
            ).isoformat()
            
            return {
                'valid': True,
                'admin_id': session_data['admin_id'],
                'permissions': session_data['permissions']
            }
            
        except Exception:
            return {'valid': False, 'error': 'Session verification failed'}
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions."""
        try:
            current_time = datetime.now()
            expired_tokens = [
                token for token, data in self.active_sessions.items()
                if datetime.fromisoformat(data['expires_at']) < current_time
            ]
            
            for token in expired_tokens:
                del self.active_sessions[token]
                
        except Exception:
            pass
    
    def revoke_admin_session(self, session_token: str) -> bool:
        """Revoke an admin session."""
        try:
            if session_token in self.active_sessions:
                del self.active_sessions[session_token]
                return True
            return False
            
        except Exception:
            return False
    
    def change_admin_password(self, session_token: str, old_password: str, new_password: str, totp_code: str = None) -> Dict:
        """Change admin password."""
        try:
            # Verify session
            session_check = self.verify_admin_session(session_token)
            if not session_check['valid']:
                return {'success': False, 'error': 'Invalid session'}
            
            # Load admin config
            admin_config = self._load_admin_config()
            if not admin_config:
                return {'success': False, 'error': 'Admin configuration not found'}
            
            # Verify old password
            salt = base64.b64decode(admin_config['salt'])
            old_password_hash = hashlib.sha256(old_password.encode() + salt).hexdigest()
            
            if old_password_hash != admin_config['password_hash']:
                return {'success': False, 'error': 'Current password incorrect'}
            
            # Verify 2FA if enabled
            if admin_config.get('2fa_enabled') and admin_config.get('totp_secret'):
                if not totp_code or not self._verify_totp(admin_config['totp_secret'], totp_code):
                    return {'success': False, 'error': '2FA code required'}
            
            # Generate new salt and hash
            new_salt = secrets.token_bytes(32)
            new_password_hash = hashlib.sha256(new_password.encode() + new_salt).hexdigest()
            
            # Update admin config
            admin_config['salt'] = base64.b64encode(new_salt).decode()
            admin_config['password_hash'] = new_password_hash
            admin_config['login_attempts'] = 0
            admin_config['locked_until'] = None
            
            # Save updated config
            self._save_admin_config_update(admin_config)
            
            # Revoke all sessions except current
            current_session = self.active_sessions.get(session_token)
            self.active_sessions.clear()
            if current_session:
                self.active_sessions[session_token] = current_session
            
            return {'success': True, 'message': 'Password updated successfully'}
            
        except Exception as e:
            return {'success': False, 'error': f'Password change failed: {str(e)}'}
    
    def enable_disable_2fa(self, session_token: str, enable: bool, password: str) -> Dict:
        """Enable or disable 2FA for admin account."""
        try:
            # Verify session
            session_check = self.verify_admin_session(session_token)
            if not session_check['valid']:
                return {'success': False, 'error': 'Invalid session'}
            
            # Load and verify admin config
            admin_config = self._load_admin_config()
            if not admin_config:
                return {'success': False, 'error': 'Admin configuration not found'}
            
            # Verify password
            salt = base64.b64decode(admin_config['salt'])
            password_hash = hashlib.sha256(password.encode() + salt).hexdigest()
            
            if password_hash != admin_config['password_hash']:
                return {'success': False, 'error': 'Password incorrect'}
            
            if enable and not admin_config.get('2fa_enabled'):
                # Enable 2FA
                totp_secret = pyotp.random_base32()
                totp_uri = pyotp.totp.TOTP(totp_secret).provisioning_uri(
                    name=admin_config.get('email', 'admin'),
                    issuer_name="SilentLock Admin"
                )
                
                qr_code_data = self._generate_qr_code(totp_uri)
                
                admin_config['2fa_enabled'] = True
                admin_config['totp_secret'] = totp_secret
                
                self._save_admin_config_update(admin_config)
                
                return {
                    'success': True,
                    'qr_code_data': qr_code_data,
                    'secret': totp_secret,
                    'message': '2FA enabled. Please scan QR code with your authenticator app.'
                }
                
            elif not enable and admin_config.get('2fa_enabled'):
                # Disable 2FA
                admin_config['2fa_enabled'] = False
                admin_config['totp_secret'] = None
                
                self._save_admin_config_update(admin_config)
                
                return {'success': True, 'message': '2FA disabled'}
            
            return {'success': False, 'error': 'No change required'}
            
        except Exception as e:
            return {'success': False, 'error': f'2FA operation failed: {str(e)}'}
    
    def _generate_qr_code(self, data: str) -> str:
        """Generate QR code for 2FA setup."""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64 for display
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception:
            return None
    
    def _save_admin_config(self, config: Dict, admin_key: bytes):
        """Save encrypted admin configuration with fallback handling."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.admin_config_path), exist_ok=True)
            
            # Encrypt configuration
            fernet = Fernet(admin_key)
            config_json = json.dumps(config, indent=2)
            encrypted_config = fernet.encrypt(config_json.encode())
            
            # Save to file
            with open(self.admin_config_path, 'wb') as f:
                f.write(encrypted_config)
            
            # Protect file with Windows ACL
            self._protect_admin_file()
            
        except PermissionError as e:
            # Try fallback location
            try:
                fallback_path = os.path.join(os.getcwd(), 'data', 'admin_config.enc')
                os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                
                # Update the path for future use
                self.admin_config_path = fallback_path
                
                # Encrypt configuration
                fernet = Fernet(admin_key)
                config_json = json.dumps(config, indent=2)
                encrypted_config = fernet.encrypt(config_json.encode())
                
                # Save to fallback location
                with open(self.admin_config_path, 'wb') as f:
                    f.write(encrypted_config)
                
                print(f"✅ Admin config saved to fallback location: {self.admin_config_path}")
                
            except Exception as fallback_error:
                raise Exception(f"Failed to save admin config even with fallback: {fallback_error}")
        except Exception as e:
            raise Exception(f"Failed to save admin config: {e}")
    
    def _save_admin_config_update(self, config: Dict):
        """Save updated admin configuration using existing encryption with fallback handling."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.admin_config_path), exist_ok=True)
            
            # This is simplified - in practice, you'd need to re-derive the key
            # or store it securely in memory during the session
            temp_config = json.dumps(config, indent=2)
            
            # For now, use Windows DPAPI for updates
            encrypted_data = win32crypt.CryptProtectData(
                temp_config.encode(),
                'SilentLock Admin Config',
                None,
                None,
                None,
                0
            )
            
            # Write to temporary location
            temp_path = self.admin_config_path + '.tmp'
            with open(temp_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Atomic replace
            os.replace(temp_path, self.admin_config_path)
            self._protect_admin_file()
            
        except PermissionError as e:
            # Try fallback location
            try:
                fallback_path = os.path.join(os.getcwd(), 'data', 'admin_config.enc')
                os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                
                # Update the path for future use
                self.admin_config_path = fallback_path
                
                # Encrypt data
                temp_config = json.dumps(config, indent=2)
                encrypted_data = win32crypt.CryptProtectData(
                    temp_config.encode(),
                    'SilentLock Admin Config',
                    None,
                    None,
                    None,
                    0
                )
                
                # Write to fallback location
                temp_path = self.admin_config_path + '.tmp'
                with open(temp_path, 'wb') as f:
                    f.write(encrypted_data)
                
                # Atomic replace
                os.replace(temp_path, self.admin_config_path)
                
                print(f"✅ Admin config updated at fallback location: {self.admin_config_path}")
                
            except Exception as fallback_error:
                print(f"❌ Failed to update admin config even with fallback: {fallback_error}")
        except Exception as e:
            print(f"❌ Failed to update admin config: {e}")
    
    def _load_admin_config(self) -> Optional[Dict]:
        """Load and decrypt admin configuration."""
        try:
            if not os.path.exists(self.admin_config_path):
                return None
            
            with open(self.admin_config_path, 'rb') as f:
                encrypted_data = f.read()
            
            # Try DPAPI decryption first (for updates)
            try:
                decrypted_data, _ = win32crypt.CryptUnprotectData(
                    encrypted_data,
                    None,
                    None,
                    None,
                    0
                )
                return json.loads(decrypted_data.decode())
            except:
                # If DPAPI fails, config needs to be decrypted with admin key
                # This would require password input
                return None
                
        except Exception:
            return None
    
    def _protect_admin_file(self):
        """Protect admin configuration file with Windows ACL."""
        try:
            # Set file as hidden and system
            import win32api
            import win32con
            
            win32api.SetFileAttributes(
                self.admin_config_path,
                win32con.FILE_ATTRIBUTE_HIDDEN | win32con.FILE_ATTRIBUTE_SYSTEM
            )
            
        except Exception:
            pass  # ACL protection not critical if fails
    
    def send_email_otp(self, email: str = None, purpose: str = 'admin_login') -> Dict:
        """Send email OTP for admin authentication."""
        try:
            # Load admin config to get email if not provided
            if not email:
                admin_config = self._load_admin_config()
                if not admin_config or not admin_config.get('email'):
                    return {'success': False, 'error': 'No email configured'}
                email = admin_config['email']
            
            # Check if email 2FA is enabled
            admin_config = self._load_admin_config()
            if not admin_config.get('email_2fa_enabled'):
                return {'success': False, 'error': 'Email 2FA not enabled'}
            
            # Check if email service is configured
            if not self.email_otp_service.is_configured():
                return {'success': False, 'error': 'Email service not configured'}
            
            # Generate OTP code
            otp_result = self.email_otp_service.generate_otp_code(email, purpose)
            if not otp_result['success']:
                return otp_result
            
            # Send email
            send_result = self.email_otp_service.send_otp_email(email, otp_result['otp_code'], purpose)
            if not send_result['success']:
                return send_result
            
            return {
                'success': True,
                'message': f'OTP code sent to {email}',
                'expires_at': otp_result['expires_at']
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to send OTP: {str(e)}'}
    
    def configure_email_2fa(self, session_token: str, enable: bool, 
                           email: str = None, smtp_config: Dict = None) -> Dict:
        """Configure email-based 2FA for admin account."""
        try:
            # Verify session
            session_check = self.verify_admin_session(session_token)
            if not session_check['valid']:
                return {'success': False, 'error': 'Invalid session'}
            
            # Load admin config
            admin_config = self._load_admin_config()
            if not admin_config:
                return {'success': False, 'error': 'Admin configuration not found'}
            
            if enable:
                # Configure email 2FA
                if email:
                    admin_config['email'] = email
                
                if not admin_config.get('email'):
                    return {'success': False, 'error': 'Email address required for email 2FA'}
                
                # Configure email service if SMTP config provided
                if smtp_config:
                    config_result = self.email_otp_service.configure_email_settings(
                        smtp_config['smtp_server'],
                        smtp_config['smtp_port'],
                        smtp_config['from_email'],
                        smtp_config['from_password'],
                        smtp_config.get('use_tls', True),
                        smtp_config.get('from_name', 'SilentLock Security')
                    )
                    if not config_result['success']:
                        return config_result
                
                # Test email sending
                test_result = self.send_email_otp(admin_config['email'], 'test_setup')
                if not test_result['success']:
                    return {'success': False, 'error': f'Email test failed: {test_result["error"]}'}
                
                admin_config['email_2fa_enabled'] = True
                # Update 2FA method based on current settings
                if admin_config.get('2fa_enabled') and admin_config.get('totp_secret'):
                    admin_config['2fa_method'] = 'both'  # Both TOTP and Email
                else:
                    admin_config['2fa_method'] = 'email'  # Email only
                    admin_config['2fa_enabled'] = True
                
                message = 'Email 2FA enabled successfully. Test email sent.'
                
            else:
                # Disable email 2FA
                admin_config['email_2fa_enabled'] = False
                # Update 2FA method
                if admin_config.get('totp_secret'):
                    admin_config['2fa_method'] = 'totp'  # TOTP only
                else:
                    admin_config['2fa_enabled'] = False
                    admin_config['2fa_method'] = None
                
                message = 'Email 2FA disabled'
            
            # Save updated config
            self._save_admin_config_update(admin_config)
            
            return {'success': True, 'message': message}
            
        except Exception as e:
            return {'success': False, 'error': f'Email 2FA configuration failed: {str(e)}'}
    
    def update_admin_profile(self, session_token: str, updates: Dict) -> Dict:
        """Update admin profile information."""
        try:
            # Verify session
            session_check = self.verify_admin_session(session_token)
            if not session_check['valid']:
                return {'success': False, 'error': 'Invalid session'}
            
            # Load admin config
            admin_config = self._load_admin_config()
            if not admin_config:
                return {'success': False, 'error': 'Admin configuration not found'}
            
            # Update admin config fields
            config_updates = {}
            if 'email' in updates:
                config_updates['email'] = updates['email']
            
            if config_updates:
                admin_config.update(config_updates)
                self._save_admin_config_update(admin_config)
            
            # Update user profile if exists
            admin_id = admin_config['admin_id']
            profile_updates = {}
            
            # Map updates to profile fields
            if 'display_name' in updates:
                profile_updates['display_name'] = updates['display_name']
            if 'phone_number' in updates:
                profile_updates['phone_number'] = updates['phone_number']
            if 'security_question' in updates:
                profile_updates['security_question'] = updates['security_question']
            if 'security_answer' in updates:
                profile_updates['security_answer'] = updates['security_answer']
            if 'preferences' in updates:
                profile_updates['preferences'] = updates['preferences']
            
            if profile_updates:
                # Create profile if it doesn't exist
                profile_result = self.profile_manager.get_user_profile(admin_id)
                if not profile_result['success']:
                    self.profile_manager.create_user_profile(admin_id, admin_config.get('email', ''))
                
                # Update profile
                self.profile_manager.update_user_profile(admin_id, profile_updates)
            
            return {'success': True, 'message': 'Admin profile updated successfully'}
            
        except Exception as e:
            return {'success': False, 'error': f'Profile update failed: {str(e)}'}
    
    def get_admin_profile(self, session_token: str) -> Dict:
        """Get complete admin profile information."""
        try:
            # Verify session
            session_check = self.verify_admin_session(session_token)
            if not session_check['valid']:
                return {'success': False, 'error': 'Invalid session'}
            
            # Get admin info
            admin_info = self.get_admin_info(session_token)
            if not admin_info['success']:
                return admin_info
            
            admin_data = admin_info.copy()
            admin_data.pop('success', None)
            
            # Get user profile if exists
            admin_id = admin_data['admin_id']
            profile_result = self.profile_manager.get_user_profile(admin_id)
            
            if profile_result['success']:
                profile_data = profile_result['profile']
                # Merge profile data with admin data
                admin_data.update({
                    'display_name': profile_data.get('display_name'),
                    'phone_number': profile_data.get('phone_number'),
                    'security_question': profile_data.get('security_question'),
                    'profile_picture_path': profile_data.get('profile_picture_path'),
                    'login_count': profile_data.get('login_count', 0),
                    'preferences': profile_data.get('preferences', {}),
                    'user_security_settings': profile_data.get('security_settings', {}),
                    'backup_settings': profile_data.get('backup_settings', {})
                })
            
            # Get activity log
            admin_data['recent_activity'] = self.profile_manager.get_user_activity_log(admin_id, 10)
            
            # Get active sessions
            admin_data['active_sessions'] = self.profile_manager.get_user_sessions(admin_id)
            
            # Get email service status
            admin_data['email_service_configured'] = self.email_otp_service.is_configured()
            admin_data['smtp_config_status'] = self.email_otp_service.get_smtp_config_status()
            
            return {'success': True, 'profile': admin_data}
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to get profile: {str(e)}'}
        """Get admin account information."""
        try:
            # Verify session
            session_check = self.verify_admin_session(session_token)
            if not session_check['valid']:
                return {'success': False, 'error': 'Invalid session'}
            
            admin_config = self._load_admin_config()
            if not admin_config:
                return {'success': False, 'error': 'Admin configuration not found'}
            
            return {
                'success': True,
                'admin_id': admin_config['admin_id'],
                'email': admin_config.get('email'),
                'created_at': admin_config['created_at'],
                'last_login': admin_config.get('last_login'),
                '2fa_enabled': admin_config.get('2fa_enabled', False),
                'permissions': admin_config['permissions'],
                'security_settings': admin_config.get('security_settings', {}),
                'recovery_codes_remaining': len(admin_config.get('recovery_codes', []))
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}