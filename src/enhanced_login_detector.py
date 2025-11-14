"""
Enhanced login flow detector with smart authentication success detection.
Waits for successful login confirmation before saving credentials and provides real-time tracking.
"""

import re
import time
import threading
import json
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from pynput import keyboard, mouse
from pynput.keyboard import Key, Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener
import win32gui
import win32process
import psutil


class LoginSuccessDetector:
    """Detects successful login confirmations before saving credentials."""
    
    def __init__(self):
        # Success indicators in window titles
        self.success_indicators = [
            'dashboard', 'welcome', 'inbox', 'home', 'portal', 'main',
            'account', 'profile', 'settings', 'overview', 'workspace',
            'admin', 'console', 'panel', 'menu', 'feed', 'timeline',
            'logged in', 'signed in', 'authenticated', 'authorized'
        ]
        
        # Failure indicators
        self.failure_indicators = [
            'login failed', 'invalid', 'incorrect', 'error', 'denied',
            'unauthorized', 'forbidden', 'expired', 'locked', 'disabled',
            'suspended', 'blocked', 'wrong password', 'wrong username'
        ]
        
        # URL patterns that indicate successful login
        self.success_url_patterns = [
            'dashboard', 'home', 'portal', 'admin', 'user', 'account',
            'profile', 'settings', 'welcome', 'main', 'app', 'workspace'
        ]
        
    def check_login_success(self, window_title: str, previous_title: str = None) -> Tuple[bool, str]:
        """
        Check if login was successful based on window title changes.
        Returns (success, reason)
        """
        if not window_title:
            return False, "No window title"
            
        title_lower = window_title.lower()
        
        # Check for explicit failure indicators first
        for failure in self.failure_indicators:
            if failure in title_lower:
                return False, f"Login failed: {failure}"
        
        # Check for success indicators
        for success in self.success_indicators:
            if success in title_lower:
                # Additional validation: ensure it's different from login page
                if previous_title:
                    prev_lower = previous_title.lower()
                    if success not in prev_lower:  # Title changed to include success indicator
                        return True, f"Success indicator: {success}"
                else:
                    return True, f"Success indicator: {success}"
        
        # Check for URL pattern changes (for browsers)
        for pattern in self.success_url_patterns:
            if pattern in title_lower and 'login' not in title_lower and 'signin' not in title_lower:
                return True, f"Success URL pattern: {pattern}"
        
        return False, "No clear success indication"
    
    def is_likely_success_page(self, window_title: str) -> bool:
        """Quick check if window title indicates a post-login page."""
        title_lower = window_title.lower()
        return any(indicator in title_lower for indicator in self.success_indicators)


class RealTimeCredentialTracker:
    """Tracks real-time credential usage and displays live updates."""
    
    def __init__(self):
        self.usage_log = []
        self.last_activity = {}
        self.callbacks = []  # UI update callbacks
        
    def add_usage(self, credential_id: int, action: str, details: str = None):
        """Record credential usage with timestamp."""
        usage_entry = {
            'credential_id': credential_id,
            'action': action,  # 'saved', 'used', 'accessed', 'auto-filled'
            'timestamp': datetime.now(),
            'details': details or ''
        }
        
        self.usage_log.append(usage_entry)
        self.last_activity[credential_id] = usage_entry
        
        # Trigger UI updates
        self._notify_callbacks(usage_entry)
        
        # Keep only recent entries (last 1000)
        if len(self.usage_log) > 1000:
            self.usage_log = self.usage_log[-1000:]
    
    def get_last_activity(self, credential_id: int) -> Optional[Dict]:
        """Get last activity for a credential."""
        return self.last_activity.get(credential_id)
    
    def get_recent_activity(self, hours: int = 24) -> List[Dict]:
        """Get activity from last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [entry for entry in self.usage_log if entry['timestamp'] > cutoff]
    
    def format_last_used(self, credential_id: int) -> str:
        """Format last used time for display."""
        activity = self.get_last_activity(credential_id)
        if not activity:
            return "Never used"
        
        timestamp = activity['timestamp']
        now = datetime.now()
        diff = now - timestamp
        
        if diff.total_seconds() < 60:
            return "Just now"
        elif diff.total_seconds() < 3600:
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
    
    def add_callback(self, callback: Callable):
        """Add callback for UI updates."""
        self.callbacks.append(callback)
    
    def _notify_callbacks(self, usage_entry: Dict):
        """Notify all registered callbacks."""
        for callback in self.callbacks:
            try:
                callback(usage_entry)
            except Exception as e:
                print(f"Error in callback: {e}")


class EnhancedLoginFormDetector:
    """Enhanced form detector with success verification and multi-step login support."""
    
    def __init__(self, on_login_detected: Callable = None, credential_db=None, master_password=None):
        self.on_login_detected = on_login_detected
        self.credential_db = credential_db
        self.master_password = master_password
        
        # Login flow tracking
        self.login_sessions = {}  # Track ongoing login attempts
        self.active_verifications = set()  # Track active verification sessions
        self.success_detector = LoginSuccessDetector()
        self.realtime_tracker = RealTimeCredentialTracker()
        
        # Enhanced state tracking
        self.current_session = None
        self.monitoring_active = False
        self.pending_credentials = []
        
        # Multi-step login support
        self.multi_step_timeout = 30  # seconds to wait for additional steps
        self.login_verification_delay = 3  # seconds to wait for success confirmation
        
        # Thread safety
        self.verification_lock = threading.RLock()
        
        # Self-exclusion patterns - Enhanced to ignore SilentLock completely
        self.silentlock_exclusions = {
            'window_titles': [
                'SilentLock Password Manager',
                'SilentLock - Authentication', 
                'Administrator Account Created',
                'SilentLock Auto-Fill',
                'Select Credential',
                'SilentLock',
                'Profile Management',
                'Admin Dashboard'
            ],
            'process_indicators': [
                'main.py',
                'SilentLock',
                'silentlock'
            ]
        }
        
        # Base form detector for compatibility
        import form_detector
        self.base_detector = form_detector.LoginFormDetector(
            on_login_detected=self._handle_base_detection,
            credential_db=credential_db,
            master_password=master_password
        )
        
        # Override base detector methods for enhanced functionality
        self._enhance_base_detector()
    
    def _enhance_base_detector(self):
        """Enhance the base detector with our improved logic."""
        original_analyze = self.base_detector._analyze_window
        original_trigger = self.base_detector._trigger_save_prompt
        
        def enhanced_analyze(hwnd, is_background=False):
            """Enhanced window analysis with self-exclusion and success detection."""
            try:
                window_title = win32gui.GetWindowText(hwnd)
                if not window_title:
                    return
                
                # CRITICAL: Complete SilentLock exclusion
                if self._is_silentlock_window(window_title, hwnd):
                    return  # Silently ignore our own windows
                
                # Call original analysis
                original_analyze(hwnd, is_background)
                
                # Add success detection logic
                self._monitor_login_success(hwnd, window_title)
                
            except Exception as e:
                if not is_background:
                    print(f"Error in enhanced analysis: {e}")
        
        def enhanced_trigger():
            """Enhanced trigger that waits for login success before saving."""
            try:
                # Don't save immediately - wait for success confirmation
                self._queue_for_success_verification()
            except Exception as e:
                print(f"Error in enhanced trigger: {e}")
        
        # Replace methods
        self.base_detector._analyze_window = enhanced_analyze
        self.base_detector._trigger_save_prompt = enhanced_trigger
    
    def _is_silentlock_window(self, window_title: str, hwnd: int) -> bool:
        """Comprehensive check if this is a SilentLock window/process."""
        try:
            # Check window title
            if any(title.lower() in window_title.lower() for title in self.silentlock_exclusions['window_titles']):
                return True
            
            # Check process information
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name().lower()
            
            # Check if it's Python running SilentLock
            if 'python' in process_name:
                try:
                    cmdline = process.cmdline()
                    cmdline_str = ' '.join(cmdline).lower()
                    if any(indicator.lower() in cmdline_str for indicator in self.silentlock_exclusions['process_indicators']):
                        return True
                except:
                    pass
            
            return False
            
        except Exception:
            return False
    
    def _handle_base_detection(self, *args, **kwargs):
        """Handle detection from base detector."""
        # Base detector found potential credentials - queue for verification
        self._queue_for_success_verification()
    
    def _queue_for_success_verification(self):
        """Queue current credentials for success verification with deduplication."""
        if not hasattr(self.base_detector, 'form_data') or not self.base_detector.form_data:
            return
        
        with self.verification_lock:
            current_time = time.time()
            session_id = f"{current_time}_{id(self.base_detector.form_data)}"
            
            # Check if we already have a verification for this site/user
            username = getattr(self.base_detector, 'potential_username', '')
            site_name = self.base_detector.form_data.get('site_name', '')
            
            # Create deduplication key
            dedup_key = f"{site_name}:{username}"
            
            # Check for recent similar verifications
            for existing_cred in self.pending_credentials:
                existing_key = f"{existing_cred.get('site_name', '')}:{existing_cred.get('username', '')}"
                if existing_key == dedup_key and (current_time - existing_cred['timestamp']) < 10:
                    print(f"🚫 Verification already queued for {site_name} - {username}")
                    return
            
            pending_cred = {
                'session_id': session_id,
                'timestamp': current_time,
                'username': username,
                'password': getattr(self.base_detector, 'potential_password', ''),
                'site_name': site_name,
                'window_title': self.base_detector.form_data.get('window_title', ''),
                'window_handle': self.base_detector.form_data.get('window_handle'),
                'verified': False,
                'verification_attempts': 0,
                '_being_verified': False
            }
            
            # Only queue if we have meaningful credentials and not already processing
            if (pending_cred['username'] or pending_cred['password']) and session_id not in self.active_verifications:
                self.pending_credentials.append(pending_cred)
                self.active_verifications.add(session_id)
                print(f"📋 Queued credentials for verification: {pending_cred['site_name']} - {pending_cred['username']}")
                
                # Start verification process
                self._start_verification_process(session_id)
    
    def _start_verification_process(self, session_id: str):
        """Start the login success verification process with thread-safe retry prevention."""
        def verify_login():
            try:
                # Find the pending credential
                pending_cred = None
                for cred in self.pending_credentials:
                    if cred['session_id'] == session_id:
                        pending_cred = cred
                        break
                
                if not pending_cred:
                    # Clean up active verification tracking
                    with self.verification_lock:
                        self.active_verifications.discard(session_id)
                    return
                
                # Check if we're already processing this credential
                if hasattr(pending_cred, '_being_verified') and pending_cred.get('_being_verified', False):
                    print(f"🚫 Verification already in progress for {pending_cred['site_name']}")
                    return
                
                # Mark as being verified to prevent duplicates
                pending_cred['_being_verified'] = True
                
                max_attempts = 3
                retry_delay = 2
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        print(f"🔍 Verification attempt {attempt}/{max_attempts} for {pending_cred['site_name']}")
                        
                        # Wait before checking (first attempt waits longer)
                        wait_time = self.login_verification_delay if attempt == 1 else retry_delay
                        time.sleep(wait_time)
                        
                        # Check for login success
                        success = self._verify_login_success(pending_cred)
                        
                        if success:
                            print(f"✅ Login success verified for {pending_cred['site_name']} on attempt {attempt}")
                            pending_cred['verified'] = True
                            credential_id = self._save_verified_credentials(pending_cred)
                            
                            # Record real-time usage with proper credential ID
                            if credential_id and credential_id > 0:
                                self.realtime_tracker.add_usage(credential_id, 'saved', 
                                    f"New credential for {pending_cred['site_name']}")
                                print(f"📊 Real-time activity logged: saved credential {credential_id}")
                            
                            # Mark as no longer being verified and break
                            pending_cred['_being_verified'] = False
                            
                            # Clean up active verification tracking
                            with self.verification_lock:
                                self.active_verifications.discard(session_id)
                            return
                        
                        # Update attempt counter
                        pending_cred['verification_attempts'] = attempt
                        
                        if attempt < max_attempts:
                            print(f"⏳ Retrying verification for {pending_cred['site_name']} in {retry_delay}s (attempt {attempt}/{max_attempts})")
                        
                    except Exception as e:
                        print(f"Error in verification attempt {attempt}: {e}")
                        if attempt >= max_attempts:
                            break
                
                # All attempts failed
                print(f"❌ Login verification failed for {pending_cred['site_name']} after {max_attempts} attempts - credentials not saved")
                if pending_cred in self.pending_credentials:
                    self.pending_credentials.remove(pending_cred)
                pending_cred['_being_verified'] = False
                
                # Clean up active verification tracking
                with self.verification_lock:
                    self.active_verifications.discard(session_id)
                
            except Exception as e:
                print(f"Error in verification process: {e}")
                # Make sure to clean up the verification flag and tracking
                if 'pending_cred' in locals() and pending_cred:
                    pending_cred['_being_verified'] = False
                with self.verification_lock:
                    self.active_verifications.discard(session_id)
        
        # Run verification in background with unique thread name
        thread_name = f"verification-{session_id[-8:]}"
        verification_thread = threading.Thread(target=verify_login, daemon=True, name=thread_name)
        verification_thread.start()
    
    def _verify_login_success(self, pending_cred: Dict) -> bool:
        """Verify if login was successful by checking window state."""
        try:
            hwnd = pending_cred.get('window_handle')
            if not hwnd:
                return False
            
            # Get current window title
            try:
                current_title = win32gui.GetWindowText(hwnd)
            except:
                return False  # Window may have closed
            
            previous_title = pending_cred.get('window_title', '')
            
            # Use success detector
            success, reason = self.success_detector.check_login_success(current_title, previous_title)
            
            if success:
                print(f"Login success detected: {reason}")
                return True
            
            # Additional heuristics
            if current_title != previous_title:
                # Title changed - could indicate page navigation
                if not any(fail in current_title.lower() for fail in ['error', 'invalid', 'failed']):
                    # No obvious failure, and title changed
                    print(f"Title changed from '{previous_title}' to '{current_title}' - likely success")
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error verifying login success: {e}")
            return False
    
    def _monitor_login_success(self, hwnd: int, window_title: str):
        """Monitor for login success indicators in real-time."""
        # This runs continuously to detect success patterns
        pass
    
    def _save_verified_credentials(self, pending_cred: Dict) -> int:
        """Save credentials that have been verified as successful and return credential ID."""
        try:
            if self.on_login_detected:
                # Prepare credential data in expected format
                cred_data = {
                    'site_name': pending_cred['site_name'],
                    'username': pending_cred['username'],
                    'password': pending_cred['password'],
                    'url': pending_cred.get('url', ''),
                    'notes': f"Auto-captured and verified on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
                
                # Call the original save handler
                save_success = self.on_login_detected(cred_data)
                
                if save_success:
                    # Get the credential ID by searching for the just-saved credential
                    if hasattr(self, 'credential_db') and self.credential_db:
                        try:
                            credentials = self.credential_db.search_credentials(
                                f"{pending_cred['site_name']} {pending_cred['username']}", 
                                self.master_password
                            )
                            if credentials and len(credentials) > 0:
                                credential_id = credentials[0]['id']
                                
                                # Remove from pending
                                if pending_cred in self.pending_credentials:
                                    self.pending_credentials.remove(pending_cred)
                                
                                print(f"✅ Successfully saved verified credentials for {pending_cred['site_name']} (ID: {credential_id})")
                                return credential_id
                        except Exception as e:
                            print(f"Error getting credential ID: {e}")
                
                # Remove from pending even if we couldn't get the ID
                if pending_cred in self.pending_credentials:
                    self.pending_credentials.remove(pending_cred)
                
                print(f"✅ Successfully saved verified credentials for {pending_cred['site_name']}")
                return 0  # Return 0 if we can't get the ID
            
        except Exception as e:
            print(f"Error saving verified credentials: {e}")
            return 0
    
    def start_monitoring(self):
        """Start enhanced monitoring with success verification."""
        self.monitoring_active = True
        self.base_detector.start_monitoring()
        print("🔍 Enhanced monitoring started with login success verification")
    
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring_active = False
        self.base_detector.stop_monitoring()
        print("⏹️ Enhanced monitoring stopped")
    
    def get_realtime_tracker(self) -> RealTimeCredentialTracker:
        """Get the real-time activity tracker."""
        return self.realtime_tracker
    
    def get_pending_verifications(self) -> List[Dict]:
        """Get list of credentials pending verification."""
        return self.pending_credentials.copy()
    
    def force_verify_credential(self, session_id: str) -> bool:
        """Force verification of a specific credential."""
        for cred in self.pending_credentials:
            if cred['session_id'] == session_id:
                self._save_verified_credentials(cred)
                return True
        return False