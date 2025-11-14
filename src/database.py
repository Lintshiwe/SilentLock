"""
Database manager for SilentLock password manager.
Handles secure storage and retrieval of credentials.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from .security import SecurityManager


class DatabaseManager:
    """Manages the local SQLite database for credential storage."""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Store in user's AppData directory
            app_data = os.path.expandvars(r'%APPDATA%\SilentLock')
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, 'credentials.db')
        
        self.db_path = db_path
        self.security = SecurityManager()
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create credentials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_name TEXT NOT NULL,
                site_url TEXT NOT NULL,
                username TEXT NOT NULL,
                encrypted_password TEXT NOT NULL,
                encryption_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP,
                notes TEXT,
                UNIQUE(site_url, username)
            )
        ''')
        
        # Create master password table (stores hash for verification)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_password (
                id INTEGER PRIMARY KEY,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def set_master_password(self, password: str) -> bool:
        """Set the master password for the database."""
        try:
            # Generate salt and hash password
            salt = self.security.generate_salt()
            password_hash = self.security.derive_key(password, salt)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clear existing master password
            cursor.execute('DELETE FROM master_password')
            
            # Insert new master password
            cursor.execute(
                'INSERT INTO master_password (password_hash, salt) VALUES (?, ?)',
                (password_hash.hex(), salt.hex())
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error setting master password: {e}")
            return False
    
    def verify_master_password(self, password: str) -> bool:
        """Verify the master password."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT password_hash, salt FROM master_password LIMIT 1')
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                return False
            
            stored_hash, salt_hex = result
            salt = bytes.fromhex(salt_hex)
            
            # Derive key from provided password
            derived_key = self.security.derive_key(password, salt)
            
            return derived_key.hex() == stored_hash
            
        except Exception as e:
            print(f"Error verifying master password: {e}")
            return False
    
    def has_master_password(self) -> bool:
        """Check if master password is set."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM master_password')
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def store_credential(self, site_name: str, site_url: str, username: str, 
                        password: str, master_password: str, notes: str = "", 
                        force_update: bool = False) -> int:
        """Store a credential securely and return the credential ID."""
        try:
            # Encrypt the password
            encrypted_data = self.security.encrypt_data(password, master_password)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or update credential
            cursor.execute('''
                INSERT OR REPLACE INTO credentials 
                (site_name, site_url, username, encrypted_password, encryption_data, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                site_name, 
                site_url, 
                username, 
                encrypted_data['ciphertext'],
                json.dumps(encrypted_data),
                notes,
                datetime.now()
            ))
            
            credential_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return credential_id if credential_id else 0
            
        except Exception as e:
            print(f"Error storing credential: {e}")
            return 0

    def check_duplicate_credentials(self, site_name: str, site_url: str, username: str, 
                                  master_password: str) -> Dict[str, any]:
        """Check for duplicate credentials and return detailed information."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            duplicates = {
                'exact_match': None,
                'same_site_different_user': [],
                'same_user_different_site': [],
                'similar_domains': [],
                'has_duplicates': False
            }
            
            # 1. Check for exact match (same URL + username)
            cursor.execute('''
                SELECT site_name, site_url, username, encryption_data, notes, created_at, last_used
                FROM credentials WHERE site_url = ? AND username = ?
            ''', (site_url, username))
            
            exact_result = cursor.fetchone()
            if exact_result:
                encryption_data = json.loads(exact_result[3])
                try:
                    decrypted_password = self.security.decrypt_data(encryption_data, master_password)
                    duplicates['exact_match'] = {
                        'site_name': exact_result[0],
                        'site_url': exact_result[1],
                        'username': exact_result[2],
                        'password': decrypted_password,
                        'notes': exact_result[4],
                        'created_at': exact_result[5],
                        'last_used': exact_result[6]
                    }
                    duplicates['has_duplicates'] = True
                except Exception:
                    pass  # Skip if can't decrypt
            
            # 2. Check for same site, different username
            cursor.execute('''
                SELECT site_name, site_url, username, encryption_data, notes
                FROM credentials WHERE site_url = ? AND username != ?
                ORDER BY username
            ''', (site_url, username))
            
            same_site_results = cursor.fetchall()
            for result in same_site_results:
                encryption_data = json.loads(result[3])
                try:
                    decrypted_password = self.security.decrypt_data(encryption_data, master_password)
                    duplicates['same_site_different_user'].append({
                        'site_name': result[0],
                        'site_url': result[1],
                        'username': result[2],
                        'password': decrypted_password,
                        'notes': result[4]
                    })
                except Exception:
                    continue
            
            if duplicates['same_site_different_user']:
                duplicates['has_duplicates'] = True
            
            # 3. Check for same username, different site
            cursor.execute('''
                SELECT site_name, site_url, username, encryption_data, notes
                FROM credentials WHERE username = ? AND site_url != ?
                ORDER BY site_name
            ''', (username, site_url))
            
            same_user_results = cursor.fetchall()
            for result in same_user_results:
                encryption_data = json.loads(result[3])
                try:
                    decrypted_password = self.security.decrypt_data(encryption_data, master_password)
                    duplicates['same_user_different_site'].append({
                        'site_name': result[0],
                        'site_url': result[1],
                        'username': result[2],
                        'password': decrypted_password,
                        'notes': result[4]
                    })
                except Exception:
                    continue
            
            if duplicates['same_user_different_site']:
                duplicates['has_duplicates'] = True
            
            # 4. Check for similar domains (basic domain matching)
            if site_url:
                # Extract domain from URL
                import re
                domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/]+)', site_url)
                if domain_match:
                    domain = domain_match.group(1).lower()
                    # Remove common subdomains and get base domain
                    domain_parts = domain.split('.')
                    if len(domain_parts) > 2:
                        base_domain = '.'.join(domain_parts[-2:])  # Get last two parts
                    else:
                        base_domain = domain
                    
                    cursor.execute('''
                        SELECT site_name, site_url, username, encryption_data, notes
                        FROM credentials WHERE site_url LIKE ? AND site_url != ? AND username = ?
                        ORDER BY site_name
                    ''', (f'%{base_domain}%', site_url, username))
                    
                    similar_results = cursor.fetchall()
                    for result in similar_results:
                        encryption_data = json.loads(result[3])
                        try:
                            decrypted_password = self.security.decrypt_data(encryption_data, master_password)
                            duplicates['similar_domains'].append({
                                'site_name': result[0],
                                'site_url': result[1],
                                'username': result[2],
                                'password': decrypted_password,
                                'notes': result[4]
                            })
                        except Exception:
                            continue
                    
                    if duplicates['similar_domains']:
                        duplicates['has_duplicates'] = True
            
            conn.close()
            return duplicates
            
        except Exception as e:
            print(f"Error checking duplicates: {e}")
            return {'has_duplicates': False, 'exact_match': None, 'same_site_different_user': [], 
                   'same_user_different_site': [], 'similar_domains': []}
    
    def get_credential(self, site_url: str, username: str, master_password: str) -> Optional[Dict]:
        """Retrieve and decrypt a credential."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT site_name, site_url, username, encryption_data, notes, created_at, last_used
                FROM credentials WHERE site_url = ? AND username = ?
            ''', (site_url, username))
            
            result = cursor.fetchone()
            
            if result:
                # Update last_used timestamp
                cursor.execute(
                    'UPDATE credentials SET last_used = ? WHERE site_url = ? AND username = ?',
                    (datetime.now(), site_url, username)
                )
                conn.commit()
            
            conn.close()
            
            if not result:
                return None
            
            site_name, site_url, username, encryption_data_str, notes, created_at, last_used = result
            encryption_data = json.loads(encryption_data_str)
            
            # Decrypt password
            decrypted_password = self.security.decrypt_data(encryption_data, master_password)
            
            return {
                'site_name': site_name,
                'site_url': site_url,
                'username': username,
                'password': decrypted_password,
                'notes': notes,
                'created_at': created_at,
                'last_used': last_used
            }
            
        except Exception as e:
            print(f"Error retrieving credential: {e}")
            return None
    
    def get_all_credentials(self, master_password: str) -> List[Dict]:
        """Retrieve all stored credentials."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, site_name, site_url, username, encryption_data, notes, created_at, last_used
                FROM credentials ORDER BY site_name, username
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            credentials = []
            for result in results:
                credential_id, site_name, site_url, username, encryption_data_str, notes, created_at, last_used = result
                
                try:
                    encryption_data = json.loads(encryption_data_str)
                    decrypted_password = self.security.decrypt_data(encryption_data, master_password)
                    
                    credentials.append({
                        'id': credential_id,  # Include the ID
                        'site_name': site_name,
                        'site_url': site_url,
                        'username': username,
                        'password': decrypted_password,
                        'notes': notes,
                        'created_at': created_at,
                        'last_used': last_used
                    })
                except Exception:
                    # Skip credentials that can't be decrypted (wrong master password)
                    continue
            
            return credentials
            
        except Exception as e:
            print(f"Error retrieving credentials: {e}")
            return []
    
    def delete_credential(self, site_url: str, username: str) -> bool:
        """Delete a credential."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM credentials WHERE site_url = ? AND username = ?',
                (site_url, username)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Error deleting credential: {e}")
            return False
    
    def search_credentials(self, query: str, master_password: str) -> List[Dict]:
        """Search credentials by site name or URL."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, site_name, site_url, username, encryption_data, notes, created_at, last_used
                FROM credentials 
                WHERE site_name LIKE ? OR site_url LIKE ?
                ORDER BY site_name, username
            ''', (f'%{query}%', f'%{query}%'))
            
            results = cursor.fetchall()
            conn.close()
            
            credentials = []
            for result in results:
                credential_id, site_name, site_url, username, encryption_data_str, notes, created_at, last_used = result
                
                try:
                    encryption_data = json.loads(encryption_data_str)
                    decrypted_password = self.security.decrypt_data(encryption_data, master_password)
                    
                    credentials.append({
                        'id': credential_id,  # Include the ID
                        'site_name': site_name,
                        'site_url': site_url,
                        'username': username,
                        'password': decrypted_password,
                        'notes': notes,
                        'created_at': created_at,
                        'last_used': last_used
                    })
                except Exception:
                    continue
            
            return credentials
            
        except Exception as e:
            print(f"Error searching credentials: {e}")
            return []
    
    def get_cursor(self):
        """Get database cursor for direct SQL operations."""
        try:
            # Return a connection that can be used directly
            return sqlite3.connect(self.db_path)
        except Exception as e:
            print(f"Error getting database connection: {e}")
            return None
    
    def close_connection(self):
        """Close database connection."""
        # Since we're using connection-per-operation pattern,
        # this is mainly for cleanup and consistency
        pass