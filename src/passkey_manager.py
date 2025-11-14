"""
Passkey/FIDO2 Authentication Support for SilentLock
Implements WebAuthn standard for enhanced security beyond traditional passwords.
"""

import os
import json
import base64
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sqlite3

try:
    from fido2.server import Fido2Server
    from fido2.webauthn import PublicKeyCredentialRpEntity, PublicKeyCredentialUserEntity
    from fido2.client import Fido2Client
    from fido2 import cbor
    from fido2.ctap2 import Ctap2
    from fido2.hid import CtapHidDevice
    FIDO2_AVAILABLE = True
except ImportError:
    FIDO2_AVAILABLE = False
    print("FIDO2 libraries not available. Passkey support disabled.")


class PasskeyManager:
    """Manages FIDO2/WebAuthn passkey authentication for SilentLock."""
    
    def __init__(self, db_manager, app_domain: str = "localhost"):
        self.db_manager = db_manager
        self.app_domain = app_domain
        self.rp_id = app_domain
        self.rp_name = "SilentLock Password Manager"
        
        if not FIDO2_AVAILABLE:
            self.server = None
            return
        
        # Initialize FIDO2 server
        self.rp = PublicKeyCredentialRpEntity(
            id=self.rp_id,
            name=self.rp_name
        )
        
        self.server = Fido2Server(self.rp)
        
        # Initialize passkey database
        self._init_passkey_db()
        
        # Active challenges
        self.active_challenges = {}
    
    def _init_passkey_db(self):
        """Initialize passkey storage database."""
        if not FIDO2_AVAILABLE:
            return
            
        try:
            cursor = self.db_manager.get_cursor()
            
            # Registered passkeys table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS passkeys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    credential_id BLOB NOT NULL,
                    public_key BLOB NOT NULL,
                    sign_count INTEGER DEFAULT 0,
                    device_name TEXT,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    is_backup_eligible BOOLEAN DEFAULT FALSE,
                    is_backup_device BOOLEAN DEFAULT FALSE,
                    transports TEXT,
                    UNIQUE(credential_id)
                )
            ''')
            
            # Authentication challenges table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    challenge TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    challenge_type TEXT NOT NULL,
                    used BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # Passkey authentication logs
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS passkey_auth_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    credential_id BLOB,
                    auth_type TEXT,
                    success BOOLEAN,
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT
                )
            ''')
            
            cursor.connection.commit()
            
        except Exception as e:
            print(f"Error initializing passkey database: {e}")
    
    def is_available(self) -> bool:
        """Check if FIDO2/passkey support is available."""
        return FIDO2_AVAILABLE and self.server is not None
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available FIDO2 devices."""
        if not FIDO2_AVAILABLE:
            return []
        
        try:
            devices = list(CtapHidDevice.list_devices())
            device_info = []
            
            for device in devices:
                try:
                    client = Fido2Client(device, self.rp_id)
                    info = client.ctap2.get_info()
                    
                    device_info.append({
                        'device_path': str(device.path),
                        'manufacturer': getattr(device, 'product_name', 'Unknown'),
                        'product': getattr(device, 'manufacturer_string', 'Unknown'),
                        'versions': info.versions,
                        'extensions': info.extensions,
                        'transports': info.transports if hasattr(info, 'transports') else []
                    })
                except Exception as e:
                    print(f"Error reading device info: {e}")
            
            return device_info
            
        except Exception as e:
            print(f"Error listing FIDO2 devices: {e}")
            return []
    
    def begin_registration(self, user_id: str, username: str, display_name: str = None) -> Optional[Dict[str, Any]]:
        """Begin passkey registration process."""
        if not FIDO2_AVAILABLE:
            return None
        
        try:
            # Create user entity
            user = PublicKeyCredentialUserEntity(
                id=user_id.encode(),
                name=username,
                display_name=display_name or username
            )
            
            # Get existing credentials for this user
            existing_creds = self._get_user_credentials(user_id)
            exclude_creds = [cred['credential_id'] for cred in existing_creds]
            
            # Generate registration options
            registration_data, state = self.server.register_begin(
                user=user,
                exclude_list=exclude_creds,
                user_verification="preferred",
                authenticator_attachment="cross-platform"  # Support both platform and roaming authenticators
            )
            
            # Store challenge
            challenge_id = self._store_challenge(
                challenge=state['challenge'],
                user_id=user_id,
                challenge_type="registration"
            )
            
            # Convert to JSON-serializable format
            options = {
                'challenge_id': challenge_id,
                'publicKey': {
                    'challenge': base64.urlsafe_b64encode(registration_data.challenge).decode(),
                    'rp': {
                        'id': registration_data.rp.id,
                        'name': registration_data.rp.name
                    },
                    'user': {
                        'id': base64.urlsafe_b64encode(registration_data.user.id).decode(),
                        'name': registration_data.user.name,
                        'displayName': registration_data.user.display_name
                    },
                    'pubKeyCredParams': [
                        {'type': param.type, 'alg': param.alg} 
                        for param in registration_data.pub_key_cred_params
                    ],
                    'excludeCredentials': [
                        {
                            'type': 'public-key',
                            'id': base64.urlsafe_b64encode(cred.id).decode(),
                            'transports': cred.transports
                        }
                        for cred in registration_data.exclude_list
                    ] if registration_data.exclude_list else [],
                    'authenticatorSelection': {
                        'userVerification': registration_data.user_verification,
                        'authenticatorAttachment': registration_data.authenticator_selection.authenticator_attachment if registration_data.authenticator_selection else None
                    },
                    'timeout': 60000,
                    'attestation': 'none'
                }
            }
            
            # Store state for completion
            self.active_challenges[challenge_id] = state
            
            return options
            
        except Exception as e:
            print(f"Error beginning passkey registration: {e}")
            return None
    
    def complete_registration(self, challenge_id: str, credential_data: Dict, device_name: str = None) -> Dict[str, Any]:
        """Complete passkey registration process."""
        if not FIDO2_AVAILABLE:
            return {'success': False, 'error': 'FIDO2 not available'}
        
        try:
            # Retrieve stored challenge state
            if challenge_id not in self.active_challenges:
                return {'success': False, 'error': 'Invalid or expired challenge'}
            
            state = self.active_challenges[challenge_id]
            
            # Validate challenge from database
            challenge_info = self._get_challenge(challenge_id)
            if not challenge_info or challenge_info['used']:
                return {'success': False, 'error': 'Challenge already used or invalid'}
            
            if datetime.now() > challenge_info['expires_at']:
                return {'success': False, 'error': 'Challenge expired'}
            
            # Parse credential data
            try:
                client_data = base64.urlsafe_b64decode(credential_data['response']['clientDataJSON'])
                attestation_object = base64.urlsafe_b64decode(credential_data['response']['attestationObject'])
                credential_id = base64.urlsafe_b64decode(credential_data['id'])
            except Exception as e:
                return {'success': False, 'error': f'Invalid credential data: {e}'}
            
            # Complete registration
            auth_data = self.server.register_complete(
                state=state,
                client_data=client_data,
                attestation_object=attestation_object
            )
            
            # Store the credential
            credential_stored = self._store_credential(
                user_id=challenge_info['user_id'],
                credential_id=credential_id,
                public_key=auth_data.credential_data.public_key,
                sign_count=auth_data.sign_count,
                device_name=device_name,
                transports=credential_data.get('response', {}).get('transports', [])
            )
            
            if credential_stored:
                # Mark challenge as used
                self._mark_challenge_used(challenge_id)
                
                # Clean up active challenge
                del self.active_challenges[challenge_id]
                
                # Log successful registration
                self._log_passkey_auth(
                    user_id=challenge_info['user_id'],
                    credential_id=credential_id,
                    auth_type='registration',
                    success=True
                )
                
                return {'success': True, 'credential_id': base64.urlsafe_b64encode(credential_id).decode()}
            else:
                return {'success': False, 'error': 'Failed to store credential'}
                
        except Exception as e:
            print(f"Error completing passkey registration: {e}")
            return {'success': False, 'error': str(e)}
    
    def begin_authentication(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Begin passkey authentication process."""
        if not FIDO2_AVAILABLE:
            return None
        
        try:
            # Get user credentials
            if user_id:
                credentials = self._get_user_credentials(user_id)
                allow_creds = [cred['credential_id'] for cred in credentials]
            else:
                # Discoverable credential authentication
                allow_creds = []
            
            # Generate authentication options
            auth_data, state = self.server.authenticate_begin(
                credentials=allow_creds,
                user_verification="preferred"
            )
            
            # Store challenge
            challenge_id = self._store_challenge(
                challenge=state['challenge'],
                user_id=user_id or '',
                challenge_type="authentication"
            )
            
            # Convert to JSON-serializable format
            options = {
                'challenge_id': challenge_id,
                'publicKey': {
                    'challenge': base64.urlsafe_b64encode(auth_data.challenge).decode(),
                    'timeout': 60000,
                    'rpId': self.rp_id,
                    'allowCredentials': [
                        {
                            'type': 'public-key',
                            'id': base64.urlsafe_b64encode(cred.id).decode(),
                            'transports': cred.transports
                        }
                        for cred in auth_data.allow_list
                    ] if auth_data.allow_list else [],
                    'userVerification': auth_data.user_verification
                }
            }
            
            # Store state for completion
            self.active_challenges[challenge_id] = state
            
            return options
            
        except Exception as e:
            print(f"Error beginning passkey authentication: {e}")
            return None
    
    def complete_authentication(self, challenge_id: str, credential_data: Dict) -> Dict[str, Any]:
        """Complete passkey authentication process."""
        if not FIDO2_AVAILABLE:
            return {'success': False, 'error': 'FIDO2 not available'}
        
        try:
            # Retrieve stored challenge state
            if challenge_id not in self.active_challenges:
                return {'success': False, 'error': 'Invalid or expired challenge'}
            
            state = self.active_challenges[challenge_id]
            
            # Validate challenge from database
            challenge_info = self._get_challenge(challenge_id)
            if not challenge_info or challenge_info['used']:
                return {'success': False, 'error': 'Challenge already used or invalid'}
            
            if datetime.now() > challenge_info['expires_at']:
                return {'success': False, 'error': 'Challenge expired'}
            
            # Parse credential data
            try:
                credential_id = base64.urlsafe_b64decode(credential_data['id'])
                client_data = base64.urlsafe_b64decode(credential_data['response']['clientDataJSON'])
                auth_data = base64.urlsafe_b64decode(credential_data['response']['authenticatorData'])
                signature = base64.urlsafe_b64decode(credential_data['response']['signature'])
            except Exception as e:
                return {'success': False, 'error': f'Invalid credential data: {e}'}
            
            # Get stored credential
            stored_cred = self._get_credential(credential_id)
            if not stored_cred:
                return {'success': False, 'error': 'Credential not found'}
            
            # Complete authentication
            try:
                auth_result = self.server.authenticate_complete(
                    state=state,
                    credentials=[stored_cred['public_key']],
                    credential_id=credential_id,
                    client_data=client_data,
                    auth_data=auth_data,
                    signature=signature
                )
                
                # Update sign count
                self._update_credential_usage(credential_id, auth_result.sign_count)
                
                # Mark challenge as used
                self._mark_challenge_used(challenge_id)
                
                # Clean up active challenge
                del self.active_challenges[challenge_id]
                
                # Log successful authentication
                self._log_passkey_auth(
                    user_id=stored_cred['user_id'],
                    credential_id=credential_id,
                    auth_type='authentication',
                    success=True
                )
                
                return {
                    'success': True,
                    'user_id': stored_cred['user_id'],
                    'credential_id': base64.urlsafe_b64encode(credential_id).decode(),
                    'device_name': stored_cred['device_name']
                }
                
            except Exception as auth_error:
                # Log failed authentication
                self._log_passkey_auth(
                    user_id=stored_cred['user_id'],
                    credential_id=credential_id,
                    auth_type='authentication',
                    success=False,
                    error_message=str(auth_error)
                )
                
                return {'success': False, 'error': f'Authentication failed: {auth_error}'}
                
        except Exception as e:
            print(f"Error completing passkey authentication: {e}")
            return {'success': False, 'error': str(e)}
    
    def _store_challenge(self, challenge: bytes, user_id: str, challenge_type: str) -> str:
        """Store authentication challenge."""
        try:
            cursor = self.db_manager.get_cursor()
            
            challenge_id = secrets.token_urlsafe(32)
            challenge_b64 = base64.urlsafe_b64encode(challenge).decode()
            expires_at = datetime.now() + timedelta(minutes=5)
            
            cursor.execute('''
                INSERT INTO auth_challenges 
                (id, challenge, user_id, expires_at, challenge_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (challenge_id, challenge_b64, user_id, expires_at, challenge_type))
            
            cursor.connection.commit()
            return challenge_id
            
        except Exception as e:
            print(f"Error storing challenge: {e}")
            return None
    
    def _get_challenge(self, challenge_id: str) -> Optional[Dict]:
        """Retrieve stored challenge."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                SELECT challenge, user_id, expires_at, challenge_type, used
                FROM auth_challenges WHERE id = ?
            ''', (challenge_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'challenge': result[0],
                    'user_id': result[1],
                    'expires_at': datetime.fromisoformat(result[2]),
                    'challenge_type': result[3],
                    'used': bool(result[4])
                }
            return None
            
        except Exception as e:
            print(f"Error retrieving challenge: {e}")
            return None
    
    def _mark_challenge_used(self, challenge_id: str):
        """Mark challenge as used."""
        try:
            cursor = self.db_manager.get_cursor()
            cursor.execute('UPDATE auth_challenges SET used = 1 WHERE id = ?', (challenge_id,))
            cursor.connection.commit()
        except Exception as e:
            print(f"Error marking challenge as used: {e}")
    
    def _store_credential(self, user_id: str, credential_id: bytes, public_key: bytes, 
                         sign_count: int, device_name: str = None, transports: List = None) -> bool:
        """Store registered passkey credential."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                INSERT INTO passkeys 
                (user_id, credential_id, public_key, sign_count, device_name, transports)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id, 
                credential_id, 
                public_key, 
                sign_count, 
                device_name or 'Unknown Device',
                json.dumps(transports) if transports else None
            ))
            
            cursor.connection.commit()
            return True
            
        except Exception as e:
            print(f"Error storing credential: {e}")
            return False
    
    def _get_user_credentials(self, user_id: str) -> List[Dict]:
        """Get all credentials for a user."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                SELECT credential_id, public_key, sign_count, device_name, 
                       registered_at, last_used, transports
                FROM passkeys WHERE user_id = ?
            ''', (user_id,))
            
            results = cursor.fetchall()
            credentials = []
            
            for result in results:
                credentials.append({
                    'credential_id': result[0],
                    'public_key': result[1],
                    'sign_count': result[2],
                    'device_name': result[3],
                    'registered_at': result[4],
                    'last_used': result[5],
                    'transports': json.loads(result[6]) if result[6] else []
                })
            
            return credentials
            
        except Exception as e:
            print(f"Error getting user credentials: {e}")
            return []
    
    def _get_credential(self, credential_id: bytes) -> Optional[Dict]:
        """Get specific credential by ID."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                SELECT user_id, public_key, sign_count, device_name
                FROM passkeys WHERE credential_id = ?
            ''', (credential_id,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'user_id': result[0],
                    'public_key': result[1],
                    'sign_count': result[2],
                    'device_name': result[3]
                }
            return None
            
        except Exception as e:
            print(f"Error getting credential: {e}")
            return None
    
    def _update_credential_usage(self, credential_id: bytes, sign_count: int):
        """Update credential usage information."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                UPDATE passkeys 
                SET sign_count = ?, last_used = CURRENT_TIMESTAMP
                WHERE credential_id = ?
            ''', (sign_count, credential_id))
            
            cursor.connection.commit()
            
        except Exception as e:
            print(f"Error updating credential usage: {e}")
    
    def _log_passkey_auth(self, user_id: str, credential_id: bytes, auth_type: str, 
                         success: bool, ip_address: str = None, user_agent: str = None,
                         error_message: str = None):
        """Log passkey authentication attempt."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                INSERT INTO passkey_auth_log 
                (user_id, credential_id, auth_type, success, ip_address, user_agent, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, credential_id, auth_type, success, ip_address, user_agent, error_message))
            
            cursor.connection.commit()
            
        except Exception as e:
            print(f"Error logging passkey authentication: {e}")
    
    def get_user_passkeys(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all registered passkeys for a user."""
        try:
            credentials = self._get_user_credentials(user_id)
            
            # Convert to user-friendly format
            passkeys = []
            for cred in credentials:
                passkeys.append({
                    'id': base64.urlsafe_b64encode(cred['credential_id']).decode(),
                    'device_name': cred['device_name'],
                    'registered_at': cred['registered_at'],
                    'last_used': cred['last_used'],
                    'transports': cred['transports'],
                    'sign_count': cred['sign_count']
                })
            
            return passkeys
            
        except Exception as e:
            print(f"Error getting user passkeys: {e}")
            return []
    
    def delete_passkey(self, user_id: str, credential_id: str) -> bool:
        """Delete a registered passkey."""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Decode credential ID
            cred_id_bytes = base64.urlsafe_b64decode(credential_id)
            
            # Delete the passkey
            cursor.execute('''
                DELETE FROM passkeys 
                WHERE user_id = ? AND credential_id = ?
            ''', (user_id, cred_id_bytes))
            
            deleted = cursor.rowcount > 0
            cursor.connection.commit()
            
            return deleted
            
        except Exception as e:
            print(f"Error deleting passkey: {e}")
            return False
    
    def get_auth_logs(self, user_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get passkey authentication logs."""
        try:
            cursor = self.db_manager.get_cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT user_id, auth_type, success, ip_address, user_agent, 
                           timestamp, error_message
                    FROM passkey_auth_log 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC LIMIT ?
                ''', (user_id, limit))
            else:
                cursor.execute('''
                    SELECT user_id, auth_type, success, ip_address, user_agent, 
                           timestamp, error_message
                    FROM passkey_auth_log 
                    ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
            
            results = cursor.fetchall()
            logs = []
            
            for result in results:
                logs.append({
                    'user_id': result[0],
                    'auth_type': result[1],
                    'success': bool(result[2]),
                    'ip_address': result[3],
                    'user_agent': result[4],
                    'timestamp': result[5],
                    'error_message': result[6]
                })
            
            return logs
            
        except Exception as e:
            print(f"Error getting auth logs: {e}")
            return []
    
    def cleanup_expired_challenges(self):
        """Clean up expired challenges."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                DELETE FROM auth_challenges 
                WHERE expires_at < datetime('now')
            ''')
            
            cursor.connection.commit()
            
            # Also clean up active challenges
            expired_challenges = []
            for challenge_id, state in self.active_challenges.items():
                challenge_info = self._get_challenge(challenge_id)
                if not challenge_info or datetime.now() > challenge_info['expires_at']:
                    expired_challenges.append(challenge_id)
            
            for challenge_id in expired_challenges:
                del self.active_challenges[challenge_id]
                
        except Exception as e:
            print(f"Error cleaning up expired challenges: {e}")