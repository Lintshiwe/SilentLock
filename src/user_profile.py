"""
User profile management for SilentLock.
Handles user information, preferences, and security settings.
"""

import json
import os
import sqlite3
import hashlib
import secrets
import base64
from datetime import datetime
from typing import Dict, Optional, List
from .security import SecurityManager


class UserProfileManager:
    """Manages user profiles and preferences."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.security = SecurityManager()
        self._init_profile_tables()
    
    def _init_profile_tables(self):
        """Initialize user profile tables."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # User profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    email TEXT,
                    display_name TEXT,
                    profile_picture_path TEXT,
                    phone_number TEXT,
                    security_question TEXT,
                    security_answer_hash TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_count INTEGER DEFAULT 0,
                    preferences TEXT,
                    security_settings TEXT,
                    backup_settings TEXT
                )
            ''')
            
            # User sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    device_info TEXT,
                    ip_address TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')
            
            # Password history table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')
            
            # User activity log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    activity_description TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT,
                    device_info TEXT,
                    FOREIGN KEY (user_id) REFERENCES user_profiles (user_id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error initializing profile tables: {e}")
    
    def create_user_profile(self, user_id: str, email: str, display_name: str = None, 
                          phone_number: str = None) -> Dict:
        """Create a new user profile."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Check if profile already exists
            cursor.execute('SELECT user_id FROM user_profiles WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                conn.close()
                return {'success': False, 'error': 'User profile already exists'}
            
            # Default preferences
            default_preferences = {
                'theme': 'light',
                'auto_lock_timeout': 900,  # 15 minutes
                'enable_notifications': True,
                'auto_backup': True,
                'backup_frequency': 'weekly',
                'password_generator_length': 16,
                'password_generator_symbols': True,
                'password_generator_numbers': True,
                'password_generator_uppercase': True,
                'password_generator_lowercase': True,
                'auto_fill_enabled': True,
                'clipboard_clear_timeout': 30,
                'show_password_strength': True,
                'require_2fa_for_sensitive': False
            }
            
            # Default security settings
            default_security_settings = {
                'require_master_password_change': False,
                'master_password_expiry_days': 0,  # 0 = never expires
                'enable_biometric_auth': False,
                'enable_email_2fa': False,
                'email_2fa_for_login': False,
                'email_2fa_for_sensitive_actions': True,
                'failed_login_lockout_attempts': 5,
                'failed_login_lockout_duration': 300,  # 5 minutes
                'session_timeout': 3600,  # 1 hour
                'enable_activity_logging': True,
                'password_history_count': 5
            }
            
            # Default backup settings
            default_backup_settings = {
                'auto_backup_enabled': True,
                'backup_frequency': 'weekly',
                'backup_retention_days': 90,
                'backup_encryption': True,
                'include_activity_logs': False,
                'backup_location': 'local'
            }
            
            # Insert profile
            cursor.execute('''
                INSERT INTO user_profiles 
                (user_id, email, display_name, phone_number, preferences, 
                 security_settings, backup_settings, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                email,
                display_name or email.split('@')[0],
                phone_number,
                json.dumps(default_preferences),
                json.dumps(default_security_settings),
                json.dumps(default_backup_settings),
                datetime.now(),
                datetime.now()
            ))
            
            conn.commit()
            conn.close()
            
            # Log activity
            self.log_user_activity(user_id, 'profile_created', 'User profile created')
            
            return {
                'success': True,
                'message': 'User profile created successfully',
                'user_id': user_id
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Profile creation failed: {str(e)}'}
    
    def get_user_profile(self, user_id: str) -> Dict:
        """Get user profile information."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, email, display_name, profile_picture_path, phone_number,
                       security_question, created_at, updated_at, last_login, login_count,
                       preferences, security_settings, backup_settings
                FROM user_profiles WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return {'success': False, 'error': 'User profile not found'}
            
            # Parse JSON fields
            try:
                preferences = json.loads(result[10]) if result[10] else {}
                security_settings = json.loads(result[11]) if result[11] else {}
                backup_settings = json.loads(result[12]) if result[12] else {}
            except json.JSONDecodeError:
                preferences = {}
                security_settings = {}
                backup_settings = {}
            
            return {
                'success': True,
                'profile': {
                    'user_id': result[0],
                    'email': result[1],
                    'display_name': result[2],
                    'profile_picture_path': result[3],
                    'phone_number': result[4],
                    'security_question': result[5],
                    'created_at': result[6],
                    'updated_at': result[7],
                    'last_login': result[8],
                    'login_count': result[9],
                    'preferences': preferences,
                    'security_settings': security_settings,
                    'backup_settings': backup_settings
                }
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Failed to get profile: {str(e)}'}
    
    def update_user_profile(self, user_id: str, updates: Dict) -> Dict:
        """Update user profile information."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            # Get current profile
            profile_result = self.get_user_profile(user_id)
            if not profile_result['success']:
                conn.close()
                return profile_result
            
            current_profile = profile_result['profile']
            
            # Build update query dynamically
            update_fields = []
            update_values = []
            
            # Simple fields
            simple_fields = ['email', 'display_name', 'phone_number', 'profile_picture_path']
            for field in simple_fields:
                if field in updates:
                    update_fields.append(f"{field} = ?")
                    update_values.append(updates[field])
            
            # JSON fields
            if 'preferences' in updates:
                current_prefs = current_profile['preferences']
                current_prefs.update(updates['preferences'])
                update_fields.append("preferences = ?")
                update_values.append(json.dumps(current_prefs))
            
            if 'security_settings' in updates:
                current_security = current_profile['security_settings']
                current_security.update(updates['security_settings'])
                update_fields.append("security_settings = ?")
                update_values.append(json.dumps(current_security))
            
            if 'backup_settings' in updates:
                current_backup = current_profile['backup_settings']
                current_backup.update(updates['backup_settings'])
                update_fields.append("backup_settings = ?")
                update_values.append(json.dumps(current_backup))
            
            # Security question and answer
            if 'security_question' in updates:
                update_fields.append("security_question = ?")
                update_values.append(updates['security_question'])
            
            if 'security_answer' in updates:
                # Hash the security answer
                answer_hash = hashlib.sha256(updates['security_answer'].lower().encode()).hexdigest()
                update_fields.append("security_answer_hash = ?")
                update_values.append(answer_hash)
            
            if not update_fields:
                conn.close()
                return {'success': False, 'error': 'No valid updates provided'}
            
            # Add updated_at timestamp
            update_fields.append("updated_at = ?")
            update_values.append(datetime.now())
            update_values.append(user_id)
            
            # Execute update
            query = f"UPDATE user_profiles SET {', '.join(update_fields)} WHERE user_id = ?"
            cursor.execute(query, update_values)
            
            conn.commit()
            conn.close()
            
            # Log activity
            self.log_user_activity(user_id, 'profile_updated', f"Profile updated: {', '.join(updates.keys())}")
            
            return {'success': True, 'message': 'Profile updated successfully'}
            
        except Exception as e:
            return {'success': False, 'error': f'Profile update failed: {str(e)}'}
    
    def verify_security_answer(self, user_id: str, security_answer: str) -> Dict:
        """Verify user's security answer."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT security_answer_hash FROM user_profiles WHERE user_id = ?',
                (user_id,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if not result or not result[0]:
                return {'success': False, 'error': 'No security question set'}
            
            # Hash provided answer and compare
            answer_hash = hashlib.sha256(security_answer.lower().encode()).hexdigest()
            
            if answer_hash == result[0]:
                self.log_user_activity(user_id, 'security_answer_verified', 'Security answer verified')
                return {'success': True, 'message': 'Security answer verified'}
            else:
                self.log_user_activity(user_id, 'security_answer_failed', 'Security answer verification failed')
                return {'success': False, 'error': 'Invalid security answer'}
                
        except Exception as e:
            return {'success': False, 'error': f'Verification failed: {str(e)}'}
    
    def update_login_info(self, user_id: str, device_info: str = None, ip_address: str = None):
        """Update user's last login information."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE user_profiles 
                SET last_login = ?, login_count = login_count + 1 
                WHERE user_id = ?
            ''', (datetime.now(), user_id))
            
            conn.commit()
            conn.close()
            
            # Log activity
            self.log_user_activity(user_id, 'login', 'User login', ip_address, device_info)
            
        except Exception as e:
            print(f"Error updating login info: {e}")
    
    def log_user_activity(self, user_id: str, activity_type: str, description: str, 
                         ip_address: str = None, device_info: str = None):
        """Log user activity."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_activity_log 
                (user_id, activity_type, activity_description, ip_address, device_info)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, activity_type, description, ip_address, device_info))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error logging user activity: {e}")
    
    def get_user_activity_log(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get user activity log."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT activity_type, activity_description, timestamp, ip_address, device_info
                FROM user_activity_log 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            activities = []
            for result in results:
                activities.append({
                    'activity_type': result[0],
                    'description': result[1],
                    'timestamp': result[2],
                    'ip_address': result[3],
                    'device_info': result[4]
                })
            
            return activities
            
        except Exception as e:
            print(f"Error getting activity log: {e}")
            return []
    
    def create_user_session(self, user_id: str, device_info: str = None, 
                           ip_address: str = None, expires_in_hours: int = 24) -> Dict:
        """Create a new user session."""
        try:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now().timestamp() + (expires_in_hours * 3600)
            
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_sessions 
                (user_id, session_token, expires_at, device_info, ip_address)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, session_token, expires_at, device_info, ip_address))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'session_token': session_token,
                'expires_at': expires_at
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Session creation failed: {str(e)}'}
    
    def validate_user_session(self, session_token: str) -> Dict:
        """Validate a user session."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT user_id, expires_at, is_active 
                FROM user_sessions 
                WHERE session_token = ?
            ''', (session_token,))
            
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {'valid': False, 'error': 'Session not found'}
            
            user_id, expires_at, is_active = result
            
            if not is_active:
                conn.close()
                return {'valid': False, 'error': 'Session deactivated'}
            
            if datetime.now().timestamp() > expires_at:
                # Deactivate expired session
                cursor.execute(
                    'UPDATE user_sessions SET is_active = 0 WHERE session_token = ?',
                    (session_token,)
                )
                conn.commit()
                conn.close()
                return {'valid': False, 'error': 'Session expired'}
            
            # Update last activity
            cursor.execute(
                'UPDATE user_sessions SET last_activity = ? WHERE session_token = ?',
                (datetime.now(), session_token)
            )
            conn.commit()
            conn.close()
            
            return {'valid': True, 'user_id': user_id}
            
        except Exception as e:
            return {'valid': False, 'error': f'Session validation failed: {str(e)}'}
    
    def revoke_user_session(self, session_token: str) -> bool:
        """Revoke a user session."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'UPDATE user_sessions SET is_active = 0 WHERE session_token = ?',
                (session_token,)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error revoking session: {e}")
            return False
    
    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Get active sessions for user."""
        try:
            conn = sqlite3.connect(self.db_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_token, created_at, last_activity, expires_at, device_info, ip_address
                FROM user_sessions 
                WHERE user_id = ? AND is_active = 1 AND expires_at > ?
                ORDER BY last_activity DESC
            ''', (user_id, datetime.now().timestamp()))
            
            results = cursor.fetchall()
            conn.close()
            
            sessions = []
            for result in results:
                sessions.append({
                    'session_token': result[0],
                    'created_at': result[1],
                    'last_activity': result[2],
                    'expires_at': result[3],
                    'device_info': result[4],
                    'ip_address': result[5]
                })
            
            return sessions
            
        except Exception as e:
            print(f"Error getting user sessions: {e}")
            return []