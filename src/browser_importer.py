"""
Browser Password Importer for SilentLock
Imports saved passwords from major browsers with user consent.
"""

import os
import json
import sqlite3
import base64
import shutil
import tempfile
from typing import List, Dict, Optional
import win32crypt
from cryptography.fernet import Fernet
from pathlib import Path


class BrowserPasswordImporter:
    """Imports saved passwords from major browsers."""
    
    def __init__(self):
        self.supported_browsers = {
            'chrome': {
                'name': 'Google Chrome',
                'profile_path': os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data',
                'db_name': 'Login Data',
                'key_path': 'Local State'
            },
            'edge': {
                'name': 'Microsoft Edge',
                'profile_path': os.path.expanduser('~') + r'\AppData\Local\Microsoft\Edge\User Data',
                'db_name': 'Login Data',
                'key_path': 'Local State'
            },
            'firefox': {
                'name': 'Mozilla Firefox',
                'profile_path': os.path.expanduser('~') + r'\AppData\Roaming\Mozilla\Firefox\Profiles',
                'db_name': 'logins.json',
                'key_path': 'key4.db'
            },
            'opera': {
                'name': 'Opera',
                'profile_path': os.path.expanduser('~') + r'\AppData\Roaming\Opera Software\Opera Stable',
                'db_name': 'Login Data',
                'key_path': 'Local State'
            },
            'brave': {
                'name': 'Brave Browser',
                'profile_path': os.path.expanduser('~') + r'\AppData\Local\BraveSoftware\Brave-Browser\User Data',
                'db_name': 'Login Data',
                'key_path': 'Local State'
            }
        }
    
    def get_available_browsers(self) -> List[Dict]:
        """Get list of browsers with saved passwords."""
        available = []
        
        for browser_id, config in self.supported_browsers.items():
            if os.path.exists(config['profile_path']):
                try:
                    password_count = self._count_passwords(browser_id)
                    if password_count > 0:
                        available.append({
                            'id': browser_id,
                            'name': config['name'],
                            'password_count': password_count
                        })
                except Exception as e:
                    print(f"Error checking {config['name']}: {e}")
        
        return available
    
    def _count_passwords(self, browser_id: str) -> int:
        """Count saved passwords in browser."""
        config = self.supported_browsers[browser_id]
        
        if browser_id == 'firefox':
            return self._count_firefox_passwords(config)
        else:
            return self._count_chromium_passwords(config)
    
    def _count_chromium_passwords(self, config: Dict) -> int:
        """Count passwords in Chromium-based browsers."""
        try:
            # Check Default profile first
            default_db = os.path.join(config['profile_path'], 'Default', config['db_name'])
            if not os.path.exists(default_db):
                return 0
            
            # Copy database to temp location (Chrome locks the file)
            temp_db = tempfile.mktemp(suffix='.db')
            shutil.copy2(default_db, temp_db)
            
            try:
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM logins WHERE password_value != ''")
                count = cursor.fetchone()[0]
                conn.close()
                return count
            finally:
                if os.path.exists(temp_db):
                    os.unlink(temp_db)
                    
        except Exception as e:
            print(f"Error counting Chromium passwords: {e}")
            return 0
    
    def _count_firefox_passwords(self, config: Dict) -> int:
        """Count passwords in Firefox."""
        try:
            profile_dir = self._get_firefox_profile_dir(config['profile_path'])
            if not profile_dir:
                return 0
            
            logins_file = os.path.join(profile_dir, config['db_name'])
            if not os.path.exists(logins_file):
                return 0
            
            with open(logins_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return len(data.get('logins', []))
                
        except Exception as e:
            print(f"Error counting Firefox passwords: {e}")
            return 0
    
    def import_browser_passwords(self, browser_id: str) -> List[Dict]:
        """Import passwords from specified browser."""
        config = self.supported_browsers.get(browser_id)
        if not config:
            raise ValueError(f"Unsupported browser: {browser_id}")
        
        print(f"Importing passwords from {config['name']}...")
        
        if browser_id == 'firefox':
            return self._import_firefox_passwords(config)
        else:
            return self._import_chromium_passwords(config)
    
    def _import_chromium_passwords(self, config: Dict) -> List[Dict]:
        """Import passwords from Chromium-based browsers."""
        passwords = []
        
        try:
            # Get encryption key
            key = self._get_chromium_key(config)
            if not key:
                print("Could not retrieve browser encryption key")
                return []
            
            # Get database path
            db_path = os.path.join(config['profile_path'], 'Default', config['db_name'])
            if not os.path.exists(db_path):
                return []
            
            # Copy database to temp location
            temp_db = tempfile.mktemp(suffix='.db')
            shutil.copy2(db_path, temp_db)
            
            try:
                conn = sqlite3.connect(temp_db)
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT origin_url, username_value, password_value
                    FROM logins
                    WHERE password_value != ''
                """)
                
                for row in cursor.fetchall():
                    url, username, encrypted_password = row
                    
                    try:
                        # Decrypt password
                        password = self._decrypt_chromium_password(encrypted_password, key)
                        
                        if password and username and url:  # Only add if all fields are present
                            passwords.append({
                                'url': url,
                                'username': username,
                                'password': password,
                                'site_name': self._extract_domain_from_url(url)
                            })
                    except Exception:
                        # Skip failed passwords silently
                        continue
                
                conn.close()
                
            finally:
                if os.path.exists(temp_db):
                    os.unlink(temp_db)
                    
        except Exception as e:
            print(f"Error importing Chromium passwords: {e}")
        
        return passwords
    
    def _get_chromium_key(self, config: Dict) -> Optional[bytes]:
        """Get Chromium browser encryption key."""
        try:
            local_state_path = os.path.join(config['profile_path'], config['key_path'])
            if not os.path.exists(local_state_path):
                return None
            
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
            
            encrypted_key = local_state['os_crypt']['encrypted_key']
            encrypted_key = base64.b64decode(encrypted_key)
            
            # Remove DPAPI prefix
            encrypted_key = encrypted_key[5:]
            
            # Decrypt with DPAPI
            key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
            return key
            
        except Exception as e:
            print(f"Error getting Chromium key: {e}")
            return None
    
    def _decrypt_chromium_password(self, encrypted_password: bytes, key: bytes) -> Optional[str]:
        """Decrypt Chromium password."""
        try:
            if encrypted_password[:3] == b'v10':
                # AES encryption (newer Chrome/Edge versions)
                nonce = encrypted_password[3:15]
                ciphertext = encrypted_password[15:]
                
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(nonce, ciphertext, None)
                return decrypted.decode('utf-8')
                
            elif encrypted_password[:3] == b'v11':
                # AES encryption (latest versions)
                nonce = encrypted_password[3:15]
                ciphertext = encrypted_password[15:]
                
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                aesgcm = AESGCM(key)
                decrypted = aesgcm.decrypt(nonce, ciphertext, None)
                return decrypted.decode('utf-8')
                
            else:
                # DPAPI encryption (older Chrome versions)
                try:
                    decrypted_data = win32crypt.CryptUnprotectData(encrypted_password, None, None, None, 0)
                    return decrypted_data[1].decode('utf-8')
                except Exception as e:
                    print(f"DPAPI decryption failed: {e}")
                    return None
                
        except Exception as e:
            # Don't print individual errors, return None for failed decryption
            return None
    
    def _import_firefox_passwords(self, config: Dict) -> List[Dict]:
        """Import passwords from Firefox."""
        passwords = []
        
        try:
            profile_dir = self._get_firefox_profile_dir(config['profile_path'])
            if not profile_dir:
                return []
            
            logins_file = os.path.join(profile_dir, config['db_name'])
            if not os.path.exists(logins_file):
                return []
            
            with open(logins_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for login in data.get('logins', []):
                try:
                    url = login.get('hostname', '')
                    username = login.get('encryptedUsername', '')
                    password = login.get('encryptedPassword', '')
                    
                    # Firefox passwords are encrypted with master password
                    # For now, we'll skip decryption and ask user to export manually
                    # This is more secure and ethical
                    
                    if url and username:
                        passwords.append({
                            'url': url,
                            'username': '<encrypted>',  # Placeholder
                            'password': '<encrypted>',  # Placeholder
                            'site_name': self._extract_domain_from_url(url),
                            'requires_manual_export': True
                        })
                        
                except Exception as e:
                    print(f"Error processing Firefox login: {e}")
            
        except Exception as e:
            print(f"Error importing Firefox passwords: {e}")
        
        return passwords
    
    def _get_firefox_profile_dir(self, profiles_path: str) -> Optional[str]:
        """Get Firefox default profile directory."""
        try:
            if not os.path.exists(profiles_path):
                return None
            
            # Look for profiles.ini
            profiles_ini = os.path.join(os.path.dirname(profiles_path), 'profiles.ini')
            if os.path.exists(profiles_ini):
                # Parse profiles.ini to find default profile
                with open(profiles_ini, 'r') as f:
                    content = f.read()
                    for line in content.split('\n'):
                        if line.startswith('Path='):
                            profile_name = line.split('=', 1)[1].strip()
                            return os.path.join(profiles_path, profile_name)
            
            # Fallback: use first .default profile found
            for item in os.listdir(profiles_path):
                if item.endswith('.default') or item.endswith('.default-release'):
                    return os.path.join(profiles_path, item)
            
            return None
            
        except Exception as e:
            print(f"Error finding Firefox profile: {e}")
            return None
    
    def _extract_domain_from_url(self, url: str) -> str:
        """Extract domain from URL."""
        if not url:
            return "Unknown"
        
        try:
            # Remove protocol
            if '://' in url:
                url = url.split('://', 1)[1]
            
            # Remove path
            if '/' in url:
                url = url.split('/', 1)[0]
            
            # Remove port
            if ':' in url:
                url = url.split(':', 1)[0]
            
            # Remove www prefix
            if url.startswith('www.'):
                url = url[4:]
            
            return url.lower()
            
        except Exception:
            return "Unknown"
    
    def export_to_silentlock_format(self, passwords: List[Dict]) -> List[Dict]:
        """Convert browser passwords to SilentLock format."""
        converted = []
        
        for pwd in passwords:
            if pwd.get('requires_manual_export'):
                continue  # Skip encrypted Firefox passwords
            
            converted.append({
                'site_name': pwd['site_name'],
                'site_url': pwd['url'],
                'username': pwd['username'],
                'password': pwd['password'],
                'notes': f"Imported from browser on {self._get_current_date()}",
                'created_date': self._get_current_date(),
                'last_used': None
            })
        
        return converted
    
    def _get_current_date(self) -> str:
        """Get current date string."""
        from datetime import datetime
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')