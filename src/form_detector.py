"""
Form detection and monitoring for SilentLock password manager.
Detects login forms and prompts user to save credentials.
"""

import re
import time
import threading
import queue
from collections import deque
from typing import Dict, List, Optional, Callable
from pynput import keyboard, mouse
from pynput.keyboard import Key, Listener as KeyboardListener
from pynput.mouse import Listener as MouseListener
import win32gui
import win32process
import psutil


class ThreadSafeEventProcessor:
    """Thread-safe event processor to prevent loops and repetition."""
    
    def __init__(self, max_queue_size=100):
        self.event_queue = queue.Queue(maxsize=max_queue_size)
        self.processed_events = deque(maxlen=1000)  # Keep track of recent events
        self.processing_thread = None
        self.stop_event = threading.Event()
        self.lock = threading.RLock()
        
    def start_processing(self):
        """Start the event processing thread."""
        if self.processing_thread and self.processing_thread.is_alive():
            return
            
        self.stop_event.clear()
        self.processing_thread = threading.Thread(target=self._process_events)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        print("📡 Event processing thread started")
    
    def stop_processing(self):
        """Stop the event processing thread."""
        self.stop_event.set()
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        print("📡 Event processing thread stopped")
    
    def add_event(self, event_type, event_data, priority=1):
        """Add event to queue with deduplication."""
        try:
            # Create event fingerprint for deduplication
            event_fingerprint = f"{event_type}:{hash(str(event_data))}"
            current_time = time.time()
            
            # Check for recent duplicates (within last 5 seconds)
            with self.lock:
                for timestamp, fingerprint in reversed(list(self.processed_events)):
                    if current_time - timestamp > 5.0:
                        break
                    if fingerprint == event_fingerprint:
                        print(f"🚫 Duplicate event blocked: {event_type}")
                        return False
            
            # Add to queue if not full
            if not self.event_queue.full():
                self.event_queue.put((current_time, event_type, event_data, priority), block=False)
                print(f"📥 Event queued: {event_type}")
                return True
            else:
                print(f"⚠️ Event queue full, dropping: {event_type}")
                return False
                
        except queue.Full:
            print(f"⚠️ Event queue full, dropping: {event_type}")
            return False
    
    def _process_events(self):
        """Process events from queue."""
        while not self.stop_event.is_set():
            try:
                # Get event with timeout
                timestamp, event_type, event_data, priority = self.event_queue.get(timeout=1.0)
                
                # Mark as processed
                event_fingerprint = f"{event_type}:{hash(str(event_data))}"
                with self.lock:
                    self.processed_events.append((timestamp, event_fingerprint))
                
                # Process the event
                self._handle_event(event_type, event_data)
                
                # Mark task as done
                self.event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing event: {e}")
                
    def _handle_event(self, event_type, event_data):
        """Override this method to handle specific events."""
        print(f"📨 Processing event: {event_type}")


class LoginFormDetector:
    """Detects login forms and provides auto-fill capabilities with thread safety."""
    
    def __init__(self, on_login_detected: Callable = None, credential_db=None, master_password=None):
        self.on_login_detected = on_login_detected
        self.credential_db = credential_db
        self.master_password = master_password
        self.is_monitoring = False
        self.current_window = None
        self.typed_text = ""
        self.potential_username = ""
        self.potential_password = ""
        self.last_input_time = 0
        self.input_timeout = 30  # seconds
        
        # Thread-safe event processing
        self.event_processor = ThreadSafeEventProcessor()
        self.event_processor._handle_event = self._handle_queued_event
        
        # Auto-fill state
        self.autofill_enabled = True
        self.current_site_url = ""
        self.available_credentials = []
        self.fill_prompt_shown = False
        
        # Thread-safe window tracking
        self.window_lock = threading.RLock()
        self.last_analyzed_window = None
        self.last_window_title = ""
        self.window_analysis_cooldown = {}  # Track when windows were last analyzed
        
        # Dialog state management (thread-safe)
        self.dialog_lock = threading.RLock()
        self._selection_dialog_open = False
        self._autofill_dialog_open = False
        self._save_prompt_open = False
        
        # Enhanced login form indicators
        self.login_keywords = [
            'login', 'signin', 'sign-in', 'log in', 'password', 'username',
            'email', 'account', 'auth', 'authentication', 'credentials',
            'register', 'signup', 'sign up', 'create account', 'join',
            'member', 'user', 'pass', 'security', 'access', 'portal',
            'dashboard', 'profile', 'settings', 'microsoft', 'google',
            'facebook', 'twitter', 'linkedin', 'github', 'amazon',
            'apple', 'adobe', 'office', 'outlook', 'gmail', 'yahoo',
            'enterprise', 'sso', 'saml', 'oauth', 'openid', 'connect',
            'verification', 'confirm', 'validate', 'activate', 'unlock',
            'reset', 'recovery', 'forgot', 'session', 'secure'
        ]
        
        # URL patterns that indicate login pages
        self.login_url_patterns = [
            'login', 'signin', 'auth', 'account', 'sso', 'oauth',
            'portal', 'dashboard', 'admin', 'secure', 'my',
            'user', 'profile', 'settings', 'member'
        ]
        
        # Browser processes to monitor
        self.browser_processes = [
            'chrome.exe', 'firefox.exe', 'msedge.exe', 'iexplore.exe',
            'opera.exe', 'brave.exe', 'vivaldi.exe', 'safari.exe',
            'chromium.exe', 'waterfox.exe', 'seamonkey.exe'
        ]
        
        # Enhanced Edge detection patterns
        self.edge_processes = ['msedge.exe', 'microsoftedge.exe', 'edge.exe']
        
        # Monitor ALL applications - comprehensive list
        self.monitor_all_apps = True  # New flag to monitor everything
        
        # Known applications that commonly have login forms (for better detection)
        self.common_login_apps = [
            # Browsers
            'chrome.exe', 'firefox.exe', 'msedge.exe', 'iexplore.exe',
            'opera.exe', 'brave.exe', 'vivaldi.exe', 'safari.exe',
            
            # Communication
            'discord.exe', 'slack.exe', 'teams.exe', 'zoom.exe',
            'skype.exe', 'telegram.exe', 'whatsapp.exe', 'signal.exe',
            'messenger.exe', 'viber.exe', 'line.exe', 'wechat.exe',
            
            # Development
            'code.exe', 'devenv.exe', 'pycharm64.exe', 'idea64.exe',
            'notepad++.exe', 'sublime_text.exe', 'atom.exe', 'eclipse.exe',
            'androidstudio64.exe', 'rider64.exe', 'webstorm64.exe',
            
            # Gaming
            'steam.exe', 'epicgameslauncher.exe', 'origin.exe',
            'battlenet.exe', 'riotclientux.exe', 'gog.exe', 'uplay.exe',
            'xbox.exe', 'xboxgamingoverlay.exe', 'minecraft.exe',
            
            # Productivity
            'outlook.exe', 'thunderbird.exe', 'onenote.exe',
            'evernote.exe', 'notion.exe', 'obsidian.exe', 'todoist.exe',
            'trello.exe', 'asana.exe', 'monday.exe', 'slack.exe',
            
            # Media
            'spotify.exe', 'itunes.exe', 'vlc.exe', 'netflix.exe',
            'plex.exe', 'kodi.exe', 'musicbee.exe', 'foobar2000.exe',
            
            # Finance
            'quicken.exe', 'mint.exe', 'personalcapital.exe',
            'quickbooks.exe', 'wave.exe', 'xero.exe',
            
            # VPN/Security
            'nordvpn.exe', 'expressvpn.exe', 'protonvpn.exe',
            'surfshark.exe', 'cyberghost.exe', 'windscribe.exe',
            'bitdefender.exe', 'norton.exe', 'mcafee.exe',
            
            # Cloud Storage
            'onedrive.exe', 'dropbox.exe', 'googledrivesync.exe',
            'box.exe', 'sync.exe', 'megasync.exe', 'pcloud.exe',
            
            # Remote Access
            'teamviewer.exe', 'anydesk.exe', 'chrome_remote_desktop.exe',
            'remotepc.exe', 'logmein.exe', 'gotomeeting.exe',
            
            # Design/Creative
            'photoshop.exe', 'illustrator.exe', 'indesign.exe',
            'figma.exe', 'sketch.exe', 'canva.exe', 'blender.exe',
            
            # Business
            'zoom.exe', 'webex.exe', 'gotomeeting.exe', 'join.me.exe',
            'bluejeans.exe', 'meet.exe', 'hangouts.exe',
            
            # Password Managers
            '1password.exe', 'lastpass.exe', 'keepass.exe',
            
            # System utilities
            'powershell.exe', 'cmd.exe', 'terminal.exe', 'wt.exe'
        ]
        
        # Application processes that may have login forms
        self.app_processes = [
            'discord.exe', 'slack.exe', 'teams.exe', 'zoom.exe',
            'skype.exe', 'telegram.exe', 'whatsapp.exe', 'signal.exe',
            'steam.exe', 'epicgameslauncher.exe', 'origin.exe',
            'spotify.exe', 'outlook.exe', 'thunderbird.exe'
        ]
        
        # Keyboard and mouse listeners
        self.keyboard_listener = None
        self.mouse_listener = None
        
        # Enhanced monitoring state
        self.monitoring_errors = 0
        self.max_errors = 10
        self.error_cooldown = 5  # seconds
        
        # State tracking
        self.in_password_field = False
        self.username_captured = False
        self.password_captured = False
        self.form_data = {}
        
        # Separate password tracking (for security)
        self.actual_password = ""  # Store actual password temporarily for saving
    
    def start_monitoring(self):
        """Start monitoring for login forms with thread-safe event processing."""
        if self.is_monitoring:
            print("🚫 Monitoring already active")
            return
        
        self.is_monitoring = True
        self.monitoring_errors = 0
        
        try:
            # Start thread-safe event processor
            self.event_processor.start_processing()
            
            # Start keyboard listener with error handling
            self.keyboard_listener = KeyboardListener(
                on_press=self._on_key_press_safe,
                on_release=self._on_key_release_safe
            )
            self.keyboard_listener.start()
            
            # Start mouse listener with error handling
            self.mouse_listener = MouseListener(
                on_click=self._on_mouse_click_safe
            )
            self.mouse_listener.start()
            
            # Start window monitoring thread
            self.monitor_thread = threading.Thread(
                target=self._monitor_windows_safe, 
                name="WindowMonitor"
            )
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            print("🚀 SilentLock monitoring started with thread-safe processing")
            
        except Exception as e:
            print(f"Error starting monitoring: {e}")
            self.is_monitoring = False
            self.event_processor.stop_processing()
            raise
    
    def stop_monitoring(self):
        """Stop monitoring for login forms and clean up threads."""
        self.is_monitoring = False
        
        try:
            # Stop event processor first
            self.event_processor.stop_processing()
            
            if self.keyboard_listener:
                self.keyboard_listener.stop()
            
            if self.mouse_listener:
                self.mouse_listener.stop()
                
            # Reset dialog states safely
            with self.dialog_lock:
                self._selection_dialog_open = False
                self._autofill_dialog_open = False
                self._save_prompt_open = False
                
            print("🛑 SilentLock monitoring stopped and threads cleaned up")
            
        except Exception as e:
            print(f"Error stopping monitoring: {e}")

    def get_monitoring_status(self):
        """Get detailed monitoring status including current input monitoring."""
        try:
            status = {
                'is_monitoring': self.is_monitoring,
                'current_window': self.form_data.get('site_name', 'Unknown') if hasattr(self, 'form_data') and self.form_data else 'None',
                'is_login_context': self._is_login_page_context() if hasattr(self, 'form_data') and self.form_data else False,
                'username_status': 'CAPTURED' if self.username_captured else 'MONITORING',
                'password_status': 'CAPTURED' if self.password_captured else 'MONITORING',
                'current_field': 'PASSWORD' if self.in_password_field else 'USERNAME',
                'current_input_length': len(self.typed_text),
                'last_activity': f"{time.time() - self.last_input_time:.1f}s ago" if self.last_input_time > 0 else 'No activity',
                'ready_for_save': self.username_captured and self.password_captured
            }
            
            if self.username_captured:
                status['username_preview'] = f"{self.potential_username[:5]}..." if len(self.potential_username) > 5 else self.potential_username
                status['username_length'] = len(self.potential_username)
                
            if self.password_captured:
                status['password_preview'] = '*' * min(len(self.potential_password), 8)
                status['password_length'] = len(self.potential_password)
                
            return status
            
        except Exception as e:
            return {'error': f"Error getting status: {e}"}
    
    def print_current_monitoring_status(self):
        """Print current monitoring status for debugging."""
        status = self.get_monitoring_status()
        
        if 'error' in status:
            print(f"❌ {status['error']}")
            return
            
        print(f"\n📊 SILENTLOCK MONITORING STATUS")
        print("=" * 40)
        print(f"🔍 Active: {'YES' if status['is_monitoring'] else 'NO'}")
        print(f"🌍 Current Site: {status['current_window']}")
        print(f"🎯 Login Context: {'YES' if status['is_login_context'] else 'NO'}")
        print(f"👤 Username: {status['username_status']}")
        if status['username_status'] == 'CAPTURED':
            print(f"   └─ Preview: {status.get('username_preview', 'N/A')} ({status.get('username_length', 0)} chars)")
        print(f"🔐 Password: {status['password_status']}")
        if status['password_status'] == 'CAPTURED':
            print(f"   └─ Preview: {status.get('password_preview', 'N/A')} ({status.get('password_length', 0)} chars)")
        print(f"🔄 Current Field: {status['current_field']}")
        print(f"📝 Input Length: {status['current_input_length']}")
        print(f"⏰ Last Activity: {status['last_activity']}")
        print(f"💾 Ready to Save: {'YES' if status['ready_for_save'] else 'NO'}")
        print("=" * 40)

    def _is_silentlock_dialog_active(self):
        """Check if any SilentLock dialog is currently active to prevent self-monitoring."""
        with self.dialog_lock:
            return (self._selection_dialog_open or 
                    self._autofill_dialog_open or 
                    self._save_prompt_open)

    def _get_all_silentlock_windows(self):
        """Get all possible SilentLock window titles for exclusion."""
        return [
            'SilentLock Password Manager',
            'SilentLock - Authentication', 
            'SilentLock - Administrator Access',
            'SilentLock - Administrator Dashboard',
            'Administrator Account Created',
            'Setup Administrator Account',
            'SilentLock Auto-Fill',
            'Select Credential',
            'SilentLock',  # Catch-all for SilentLock notifications
            'Add Credential',
            'Edit Credential',
            'Generate New Passkey',
            'Admin Profile Management',
            'Activity Statistics',
            'SilentLock Eye Monitor',
            'Select Browser to Import From'
        ]

    def _handle_queued_event(self, event_type, event_data):
        """Handle events from the thread-safe queue with enhanced browser tab detection."""
        try:
            if event_type == "key_press":
                self._process_key_press(event_data)
            elif event_type == "key_release":
                self._process_key_release(event_data)
            elif event_type == "mouse_click":
                self._process_mouse_click(event_data)
            elif event_type == "window_change":
                self._process_window_change(event_data)
            elif event_type == "save_prompt":
                self._process_save_prompt(event_data)
            elif event_type == "autofill_check":
                self._process_autofill_check(event_data)
            elif event_type == "browser_tab_scan":
                self._process_comprehensive_browser_scan(event_data)
            elif event_type == "background_scan":
                self._process_comprehensive_app_scan(event_data)
            else:
                print(f"⚠️ Unknown event type: {event_type}")
                
        except Exception as e:
            print(f"Error handling queued event {event_type}: {e}")
    
    def _on_key_press_safe(self, key):
        """Safe wrapper for key press handling with event queuing."""
        try:
            # Queue the event instead of processing directly
            self.event_processor.add_event("key_press", {
                'key': key,
                'timestamp': time.time(),
                'window': self.current_window
            })
        except Exception as e:
            self._handle_monitoring_error(f"Key press queueing error: {e}")
    
    def _on_key_release_safe(self, key):
        """Safe wrapper for key release handling with event queuing."""
        try:
            self.event_processor.add_event("key_release", {
                'key': key,
                'timestamp': time.time()
            })
        except Exception as e:
            self._handle_monitoring_error(f"Key release queueing error: {e}")
    
    def _on_mouse_click_safe(self, x, y, button, pressed):
        """Safe wrapper for mouse click handling with event queuing."""
        try:
            self.event_processor.add_event("mouse_click", {
                'x': x, 'y': y, 'button': button, 'pressed': pressed,
                'timestamp': time.time(),
                'window': self.current_window
            })
        except Exception as e:
            self._handle_monitoring_error(f"Mouse click queueing error: {e}")
    
    def _monitor_windows_safe(self):
        """Safe wrapper for window monitoring with thread-safe processing."""
        while self.is_monitoring:
            try:
                self._monitor_windows()
            except Exception as e:
                self._handle_monitoring_error(f"Window monitoring error: {e}")
                time.sleep(self.error_cooldown)
    
    def _handle_monitoring_error(self, error_msg):
        """Handle monitoring errors gracefully with thread safety."""
        with self.dialog_lock:
            self.monitoring_errors += 1
            
        print(f"Monitoring error ({self.monitoring_errors}/{self.max_errors}): {error_msg}")
        
        if self.monitoring_errors >= self.max_errors:
            print("Too many monitoring errors, stopping monitoring")
            self.stop_monitoring()
    
    def _monitor_windows(self):
        """Monitor active windows for login-related content with thread-safe queuing."""
        while self.is_monitoring:
            try:
                current_window = win32gui.GetForegroundWindow()
                
                with self.window_lock:
                    if current_window != self.current_window:
                        self.current_window = current_window
                        
                        # Queue window change event instead of processing directly
                        self.event_processor.add_event("window_change", {
                            'window_handle': current_window,
                            'timestamp': time.time(),
                            'is_foreground': True
                        })
                
                # Also monitor background windows occasionally for comprehensive detection
                if self.monitor_all_apps:
                    self._queue_background_window_scan()
                
                time.sleep(0.5)  # Reduced frequency to be less intensive
                
            except Exception as e:
                print(f"Error monitoring windows: {e}")
                time.sleep(2)  # Shorter recovery time
    
    def _queue_background_window_scan(self):
        """Queue background window scanning with enhanced browser tab detection."""
        # Only scan background windows every 20 iterations to avoid performance issues
        if not hasattr(self, '_background_scan_counter'):
            self._background_scan_counter = 0
        
        self._background_scan_counter += 1
        if self._background_scan_counter < 20:  # Scan every 10 seconds (20 * 0.5s)
            return
        
        self._background_scan_counter = 0
        
        # Enhanced: Queue both background scan AND browser tab scan
        self.event_processor.add_event("background_scan", {
            'timestamp': time.time()
        }, priority=2)  # Lower priority
        
        # Add comprehensive browser tab scanning
        self.event_processor.add_event("browser_tab_scan", {
            'timestamp': time.time()
        }, priority=2)
    
    def _process_key_press(self, event_data):
        """Process key press events from queue with enhanced username/password monitoring."""
        key = event_data.get('key')
        if not key:
            return
            
        self.last_input_time = time.time()
        
        # Get current window information for context
        current_window = self.form_data.get('site_name', 'Unknown')
        is_login_page = self._is_login_page_context()
        
        if key == Key.tab:
            # Tab indicates field navigation - critical for browser forms
            print(f"🔄 TAB - Field transition detected on {current_window}")
            self._handle_field_transition()
            
        elif key == Key.enter:
            # Enter indicates form submission or field confirmation
            print(f"🔑 ENTER - Form submission detected on {current_window}")
            self._handle_form_submission()
            
        elif key == Key.backspace:
            if self.typed_text:
                self.typed_text = self.typed_text[:-1]
                # Also handle actual password backspace
                if self.in_password_field and self.actual_password:
                    self.actual_password = self.actual_password[:-1]
                    print(f"🔐 Password backspace - remaining length: {len(self.actual_password)}")
                else:
                    print(f"👤 Username backspace - remaining text: '{self.typed_text[-5:]}...'")
        
        elif key == Key.space:
            # Space handling for different field types
            if not self.in_password_field:
                self.typed_text += ' '
                print(f"👤 Username space added - current: '{self.typed_text[-10:]}...'")
            elif self.form_data.get('is_browser', False):
                if self.in_password_field:
                    self.actual_password += ' '
                    self.typed_text += '*'
                    print(f"🔐 Password space added - length: {len(self.actual_password)}")
        
        elif hasattr(key, 'char') and key.char:
            # Regular character input
            char = key.char
            
            # Enhanced monitoring output
            if is_login_page:
                print(f"� LOGIN INPUT on '{current_window}': char='{char}' field={'PASSWORD' if self.in_password_field else 'USERNAME'}")
            
            # Enhanced password field detection
            self._update_password_field_detection(char)
            
            # Store input appropriately with enhanced feedback
            if self.in_password_field:
                # For password fields, store actual character but display asterisk
                self.actual_password += char
                self.typed_text += '*'
                print(f"🔐 PASSWORD CHAR CAPTURED: '{char}' | Total length: {len(self.actual_password)} | Site: {current_window}")
                
                # Validate password strength in real-time
                self._analyze_password_strength()
                
            else:
                self.typed_text += char
                print(f"👤 USERNAME CHAR CAPTURED: '{char}' | Current: '{self.typed_text[-10:]}...' | Site: {current_window}")
                
                # Check for email pattern
                if '@' in self.typed_text:
                    print(f"📧 Email pattern detected in username: {self.typed_text}")
                
            # Auto-detect password field based on typing patterns
            self._smart_password_field_detection()
            
            # Enhanced browser credential detection
            if self.form_data.get('is_browser', False):
                self._enhanced_browser_credential_detection()
                
            # Real-time credential validation
            self._validate_current_input()
    
    def _process_key_release(self, event_data):
        """Process key release events from queue."""
        # Currently no specific processing needed
        pass
    
    def _process_mouse_click(self, event_data):
        """Process mouse click events from queue."""
        if not event_data.get('pressed'):
            return
            
        # Mouse click indicates field change or button press - critical for browser login forms
        current_text = self.typed_text.strip()
        
        if self.form_data.get('is_browser', False):
            print(f"🌐 Browser click detected - Text: '{current_text[:5] if current_text else 'None'}...' (Password field: {self.in_password_field})")
        
        if current_text:
            if self.in_password_field and not self.password_captured:
                self.potential_password = self.actual_password if self.actual_password else current_text.replace('*', '')
                self.password_captured = True
                print(f"🔑 Password captured on click (length: {len(self.potential_password)}) - Browser: {self.form_data.get('is_browser', False)}")
            elif not self.username_captured:
                self.potential_username = current_text
                self.username_captured = True
                print(f"👤 Username captured on click: {self.potential_username[:3]}... - Browser: {self.form_data.get('is_browser', False)}")
            
            # Reset field detection for new field
            self.in_password_field = False
            self.typed_text = ""
            self.actual_password = ""  # Reset actual password
            
            # Queue save prompt check instead of processing directly
            if self.username_captured and self.password_captured:
                print("💾 Both credentials captured on click - queueing save prompt")
                self.event_processor.add_event("save_prompt", {
                    'username': self.potential_username,
                    'password': self.potential_password,
                    'site_data': self.form_data.copy(),
                    'trigger': 'click'
                })
        else:
            # Handle clicks without text for browsers
            if self.form_data.get('is_browser', False) and (self.username_captured or self.password_captured):
                print("🌐 Browser click without current text - checking captured credentials")
                if self.username_captured and self.password_captured:
                    print("💾 Browser login button click detected - queueing save prompt")
                    self.event_processor.add_event("save_prompt", {
                        'username': self.potential_username,
                        'password': self.potential_password,
                        'site_data': self.form_data.copy(),
                        'trigger': 'browser_click'
                    })
    
    def _process_window_change(self, event_data):
        """Process window change events from queue."""
        window_handle = event_data.get('window_handle')
        if window_handle:
            self._analyze_window(window_handle)
    
    def _analyze_window(self, hwnd, is_background=False):
        """Enhanced window analysis for all browsers and applications."""
        try:
            # CRITICAL: First check if any SilentLock dialog is active
            if self._is_silentlock_dialog_active():
                if not is_background:
                    print("⚠️ SilentLock dialog active - skipping window analysis to prevent loops")
                return
                
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title:
                return
            
            # Skip system windows and common non-login windows
            skip_titles = ['Program Manager', 'Desktop', 'Taskbar', 'Start', 'Windows Security']
            if any(skip in window_title for skip in skip_titles):
                return
            
            # CRITICAL: Skip SilentLock's own windows to prevent auto-fill on itself
            silentlock_windows = self._get_all_silentlock_windows()
            
            # Additional check: any window containing "SilentLock" should be excluded
            if 'SilentLock' in window_title or any(sl_window in window_title for sl_window in silentlock_windows):
                if not is_background:  # Only print for foreground windows
                    print(f"⚠️ Skipping SilentLock's own window: {window_title}")
                return
            
            # Prevent auto-fill loops: don't re-analyze the same window too frequently
            current_time = time.time()
            window_key = f"{hwnd}_{window_title}"
            
            # Check if we recently analyzed this exact window
            if window_key in self.window_analysis_cooldown:
                last_analysis = self.window_analysis_cooldown[window_key]
                if current_time - last_analysis < 10:  # 10 second cooldown
                    return
            
            # Update analysis time
            self.window_analysis_cooldown[window_key] = current_time
            
            # Clean up old entries to prevent memory buildup
            if len(self.window_analysis_cooldown) > 50:
                cutoff_time = current_time - 60  # Remove entries older than 1 minute
                self.window_analysis_cooldown = {
                    k: v for k, v in self.window_analysis_cooldown.items() 
                    if v > cutoff_time
                }
            
            # Check if window title suggests a login page
            title_lower = window_title.lower()
            is_login_page = any(keyword in title_lower for keyword in self.login_keywords)
            
            # Get process information
            process_name = "Unknown"
            is_browser = False
            is_monitored_app = False
            
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process = psutil.Process(pid)
                process_name = process.name().lower()
                
                # CRITICAL: Skip if this is SilentLock's own Python process
                if 'python' in process_name or 'tk' in process_name:
                    # Additional check to see if this is SilentLock's Python instance
                    try:
                        cmdline = process.cmdline()
                        if any('main.py' in cmd for cmd in cmdline) or any('SilentLock' in cmd for cmd in cmdline):
                            if not is_background:
                                print(f"⚠️ Skipping SilentLock's own Python process: {process_name}")
                            return
                        
                        # Check if this is a tkinter process related to SilentLock
                        if any('tkinter' in str(cmd).lower() or 'SilentLock' in str(cmd) for cmd in cmdline):
                            if not is_background:
                                print(f"⚠️ Skipping SilentLock's tkinter process: {process_name}")
                            return
                            
                    except:
                        # If we can't check cmdline but it's a Python process and we have SilentLock in the window title,
                        # it's likely our own process
                        if 'SilentLock' in window_title:
                            if not is_background:
                                print(f"⚠️ Skipping suspected SilentLock Python process: {process_name}")
                            return
                
                # Check if it's a browser
                is_browser = any(browser.lower() in process_name for browser in self.browser_processes)
                
                # Enhanced Edge detection
                if not is_browser and any(edge in process_name for edge in self.edge_processes):
                    is_browser = True
                
                # Check if it's a monitored application
                is_monitored_app = any(app.lower() in process_name for app in self.app_processes)
                
            except Exception as e:
                if not is_background:  # Only print errors for foreground windows
                    print(f"Error getting process info: {e}")
            
            # Enhanced login detection logic for ALL applications
            should_monitor = False
            
            if self.monitor_all_apps:
                # Monitor ALL applications, but use smart detection
                if is_browser:
                    # For browsers, use comprehensive detection
                    should_monitor = (
                        is_login_page or
                        any(pattern in title_lower for pattern in ['account', 'signin', 'login', 'auth', 'portal', 'dashboard', 'profile', 'secure']) or
                        self._detect_login_url_pattern(title_lower) or
                        self._detect_common_login_sites(title_lower) or
                        # Enhanced browser monitoring - monitor MORE aggressively
                        any(keyword in title_lower for keyword in [
                            'sign', 'log', 'enter', 'access', 'connect', 'password',
                            'user', 'email', 'credential', 'verification', 'verify',
                            'session', 'welcome', 'home', 'my', 'settings'
                        ])
                    )
                    
                    # AGGRESSIVE: For major browsers, monitor almost everything except obvious non-login pages
                    if any(browser in process_name for browser in ['chrome.exe', 'firefox.exe', 'msedge.exe']):
                        exclude_patterns = [
                            'youtube', 'netflix', 'twitch', 'spotify', 'music',
                            'video', 'stream', 'watch', 'play', 'game',
                            'news', 'weather', 'map', 'search', 'google.com - search'
                        ]
                        if not any(exclude in title_lower for exclude in exclude_patterns):
                            should_monitor = True
                            if not is_background:
                                print(f"🌐 AGGRESSIVE: Monitoring browser window: {title_lower[:50]}...")
                    
                    # Enhanced Edge detection - monitor more aggressively
                    if any(edge in process_name for edge in self.edge_processes):
                        should_monitor = should_monitor or any(keyword in title_lower for keyword in [
                            'microsoft', 'office', 'outlook', 'live', 'hotmail', 'msn',
                            'azure', 'bing', 'xbox', 'skype', 'teams', 'onedrive',
                            # Add more common login patterns for Edge
                            'sign', 'log', 'enter', 'access', 'connect', 'secure',
                            'portal', 'dashboard', 'profile', 'settings', 'account'
                        ])
                        
                        # For Edge, also monitor based on URL patterns in title
                        edge_login_patterns = [
                            'login.', 'signin.', 'auth.', 'account.', 'sso.',
                            'portal.', 'my.', 'secure.', 'admin.', 'dashboard.'
                        ]
                        should_monitor = should_monitor or any(pattern in title_lower for pattern in edge_login_patterns)
                        
                elif process_name in self.common_login_apps:
                    # For known apps with login forms, monitor more broadly
                    should_monitor = (
                        is_login_page or
                        any(pattern in title_lower for pattern in ['setup', 'welcome', 'start', 'config', 'settings'])
                    )
                    
                else:
                    # For ALL other applications, use selective detection
                    should_monitor = (
                        is_login_page or
                        any(sensitive_word in title_lower for sensitive_word in [
                            'password', 'login', 'signin', 'auth', 'credential', 
                            'setup', 'configuration', 'connect', 'account'
                        ])
                    )
            
            else:
                # Original logic (if monitoring is not set to all apps)
                if is_browser:
                    should_monitor = (
                        is_login_page or
                        any(pattern in title_lower for pattern in ['account', 'signin', 'login', 'auth', 'portal', 'dashboard']) or
                        self._detect_login_url_pattern(title_lower)
                    )
                elif is_monitored_app:
                    should_monitor = True
                elif is_login_page:
                    should_monitor = True
            
            # Debug output for any detected application
            if should_monitor and process_name not in ['dwm.exe', 'explorer.exe', 'winlogon.exe']:
                if not is_background:  # Only print for foreground windows to avoid spam
                    print(f"Detected potential login: {process_name} - {window_title[:80]} - Monitoring: {should_monitor}")
            
            if should_monitor:
                # Only reset form state if this is a truly new window/form
                window_changed = (
                    self.last_analyzed_window != hwnd or 
                    self.last_window_title != window_title
                )
                
                if window_changed:
                    self._reset_form_state()
                    self.last_analyzed_window = hwnd
                    self.last_window_title = window_title
                
                self.form_data['window_title'] = window_title
                self.form_data['window_handle'] = hwnd
                self.form_data['process_name'] = process_name
                self.form_data['is_browser'] = is_browser
                self.form_data['is_monitored_app'] = is_monitored_app
                self.form_data['is_background'] = is_background
                
                if is_browser:
                    self._extract_url_from_title(window_title)
                else:
                    self.form_data['site_name'] = self._clean_app_title(window_title, process_name)
                
                if not is_background:  # Only print monitoring status for foreground
                    print(f"Monitoring login form: {process_name} - {window_title[:50]}...")
                
                # Only check for auto-fill if this is a new window/form
                if window_changed:
                    self._check_for_autofill_opportunity()
                
        except Exception as e:
            if not is_background:  # Only print errors for foreground windows
                print(f"Error analyzing window: {e}")
    
    def _detect_login_url_pattern(self, title_lower):
        """Detect login-related URL patterns in browser titles."""
        return any(pattern in title_lower for pattern in self.login_url_patterns)
    
    def _detect_common_login_sites(self, title_lower):
        """Detect common login sites and services."""
        common_sites = [
            'microsoft', 'google', 'facebook', 'twitter', 'linkedin',
            'github', 'amazon', 'apple', 'adobe', 'netflix', 'spotify',
            'dropbox', 'onedrive', 'gmail', 'outlook', 'yahoo',
            'instagram', 'snapchat', 'tiktok', 'reddit', 'discord',
            'slack', 'zoom', 'teams', 'office', 'wordpress'
        ]
        return any(site in title_lower for site in common_sites)
    
    def _clean_app_title(self, title, process_name):
        """Clean application title for better site name."""
        if not title:
            return process_name.replace('.exe', '').title()
        
        # Remove common application suffixes
        cleaned = title
        app_suffixes = [
            f' - {process_name.replace(".exe", "").title()}',
            ' - Discord',
            ' - Slack',
            ' - Microsoft Teams',
            ' - Zoom',
            ' - Skype'
        ]
        
        for suffix in app_suffixes:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()
        
        return cleaned if cleaned else process_name.replace('.exe', '').title()
    
    def _extract_url_from_title(self, title):
        """Enhanced URL extraction from browser window titles."""
        # Enhanced patterns for URLs in browser titles
        url_patterns = [
            r'https?://[^\s\-]+',  # Standard URLs
            r'www\.[^\s\-]+',      # www URLs
            r'[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?',  # Domain patterns
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, title)
            if match:
                url = match.group()
                self.form_data['url'] = url
                # Extract domain for site name
                domain = self._extract_domain_from_url(url)
                self.form_data['site_name'] = domain
                return
        
        # Enhanced title parsing for modern browsers
        # Chrome: "Page Title - Google Chrome"
        # Firefox: "Page Title - Mozilla Firefox"
        # Edge: "Page Title - Microsoft Edge"
        
        browser_suffixes = [
            ' - Google Chrome',
            ' - Mozilla Firefox',
            ' - Microsoft Edge',
            ' - Internet Explorer',
            ' - Opera',
            ' - Safari',
            ' - Brave',
            ' - Vivaldi'
        ]
        
        cleaned_title = title
        for suffix in browser_suffixes:
            if cleaned_title.endswith(suffix):
                cleaned_title = cleaned_title[:-len(suffix)].strip()
                break
        
        # Try to extract site name from cleaned title
        if ' - ' in cleaned_title:
            # Format: "Site Name - Page Title"
            parts = cleaned_title.split(' - ')
            self.form_data['site_name'] = parts[-1] if len(parts) > 1 else parts[0]
        elif ' | ' in cleaned_title:
            # Format: "Page Title | Site Name"
            parts = cleaned_title.split(' | ')
            self.form_data['site_name'] = parts[-1] if len(parts) > 1 else parts[0]
        else:
            # Use the whole cleaned title
            self.form_data['site_name'] = cleaned_title
        
        # If site name is too short or generic, use a fallback
        site_name = self.form_data.get('site_name', '')
        if len(site_name) < 3 or site_name.lower() in ['login', 'signin', 'sign in']:
            self.form_data['site_name'] = 'Browser Application'
            
    def _extract_domain_from_url(self, url):
        """Extract clean domain name from URL."""
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
            return url
    
    def _schedule_delayed_check(self, delay=2.0):
        """Schedule a delayed check for credentials that might come later with throttling."""
        # Throttle delayed checks to prevent flooding
        current_time = time.time()
        
        # Check if we recently scheduled a delayed check
        if hasattr(self, '_last_delayed_check_time'):
            if current_time - self._last_delayed_check_time < 5.0:  # Only allow one per 5 seconds
                print("🚫 Delayed check throttled - too recent")
                return
        
        self._last_delayed_check_time = current_time
        
        def delayed_check():
            try:
                time.sleep(delay)
                if self.is_monitoring and (self.username_captured or self.password_captured):
                    print("Delayed check: Triggering save prompt with available credentials")
                    
                    # Use event queue to prevent direct triggering
                    self.event_processor.add_event("save_prompt", {
                        'username': self.potential_username,
                        'password': self.actual_password,
                        'site_data': self.form_data,
                        'trigger': 'delayed'
                    })
            except Exception as e:
                print(f"Error in delayed check: {e}")
        
        # Run delayed check in background thread
        threading.Thread(target=delayed_check, daemon=True, name="delayed-check").start()
    
    def _reset_form_state(self):
        """Reset form detection state."""
        self.typed_text = ""
        self.potential_username = ""
        self.potential_password = ""
        self.actual_password = ""  # Reset actual password
        self.in_password_field = False
        self.username_captured = False
        self.password_captured = False
        self.form_data = {}
        self.fill_prompt_shown = False
        self.available_credentials = []
    
    def _on_key_press(self, key):
        """Enhanced key press handling for better password detection in ALL applications including browsers."""
        try:
            self.last_input_time = time.time()
            
            # Enhanced browser detection and monitoring
            if self.form_data.get('is_browser', False):
                print(f"🌐 Browser input detected: {self.form_data.get('process_name', 'Unknown')} - {key}")
            
            if key == Key.tab:
                # Tab indicates field navigation - critical for browser forms
                self._handle_field_transition()
                
            elif key == Key.enter:
                # Enter indicates form submission or field confirmation
                print("🔑 Enter key detected - checking for form submission")
                self._handle_form_submission()
                
            elif key == Key.backspace:
                if self.typed_text:
                    self.typed_text = self.typed_text[:-1]
                    # Also handle actual password backspace
                    if self.in_password_field and self.actual_password:
                        self.actual_password = self.actual_password[:-1]
            
            elif key == Key.space:
                # Space in password field is less common, might indicate username
                if not self.in_password_field:
                    self.typed_text += ' '
                # For browsers, space in password is still valid
                elif self.form_data.get('is_browser', False):
                    if self.in_password_field:
                        self.actual_password += ' '
                        self.typed_text += '*'
            
            elif hasattr(key, 'char') and key.char:
                # Regular character input
                char = key.char
                
                # Enhanced browser credential capture
                if self.form_data.get('is_browser', False):
                    print(f"🌐 Browser char input: '{char}' (password field: {self.in_password_field})")
                
                # Enhanced password field detection
                self._update_password_field_detection(char)
                
                # Store input appropriately
                if self.in_password_field:
                    # For password fields, store actual character but display asterisk
                    self.actual_password += char
                    self.typed_text += '*'
                    print(f"🔐 Password char captured (total length: {len(self.actual_password)})")
                else:
                    self.typed_text += char
                    print(f"👤 Username char captured: '{char}' (total: {len(self.typed_text)})")
                    
                # Auto-detect password field based on typing patterns
                self._smart_password_field_detection()
                
                # Enhanced browser credential detection
                if self.form_data.get('is_browser', False):
                    self._enhanced_browser_credential_detection()
                    
        except Exception as e:
            print(f"Error in key press handler: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_field_transition(self):
        """Handle transition between form fields (Tab key) - enhanced for browsers."""
        if self.typed_text:
            current_text = self.typed_text.strip()
            current_site = self.form_data.get('site_name', 'Unknown')
            
            if self.form_data.get('is_browser', False):
                print(f"🌐 BROWSER FIELD TRANSITION on '{current_site}' - Moving from {'PASSWORD' if self.in_password_field else 'USERNAME'} field")
            
            if current_text and not self.in_password_field:
                # Likely moving from username to password field
                self.potential_username = current_text
                self.username_captured = True
                
                print(f"✅ USERNAME CAPTURED on '{current_site}'")
                print(f"   └─ Username: {self.potential_username[:5]}... (Length: {len(self.potential_username)})")
                print(f"   └─ Context: {'Browser' if self.form_data.get('is_browser', False) else 'Application'}")
                
                # Next field is likely password
                self.in_password_field = True
                print("🔐 ➡️ SWITCHING TO PASSWORD FIELD MODE")
                print("   └─ Now monitoring password input...")
                
            elif current_text and self.in_password_field:
                # Moving from password field
                self.potential_password = self.actual_password if self.actual_password else current_text.replace('*', '')
                self.password_captured = True
                
                print(f"✅ PASSWORD CAPTURED on '{current_site}'")
                print(f"   └─ Password: {'*' * min(len(self.potential_password), 8)} (Length: {len(self.potential_password)})")
                print(f"   └─ Context: {'Browser' if self.form_data.get('is_browser', False) else 'Application'}")
                
                # Check if we can trigger save prompt
                if self.username_captured and self.password_captured:
                    print("🎯 COMPLETE CREDENTIALS CAPTURED!")
                    print(f"   └─ Site: {current_site}")
                    print(f"   └─ Username: {self.potential_username[:5]}...")
                    print(f"   └─ Password: {'*' * min(len(self.potential_password), 8)}")
                    print("💾 Triggering save prompt...")
                    self._enhanced_login_monitoring_summary()
                    self._trigger_save_prompt()
            
            self.typed_text = ""
            if self.in_password_field:
                self.actual_password = ""  # Reset actual password when moving fields
    
    def _handle_form_submission(self):
        """Handle form submission (Enter key) - enhanced for browser detection."""
        current_text = self.typed_text.strip()
        current_site = self.form_data.get('site_name', 'Unknown')
        
        print(f"\n🔑 FORM SUBMISSION DETECTED on '{current_site}'")
        print("=" * 50)
        
        if self.form_data.get('is_browser', False):
            print(f"🌐 Browser submission - Current field: {'PASSWORD' if self.in_password_field else 'USERNAME'}")
        
        if current_text:
            if self.in_password_field:
                self.potential_password = self.actual_password if self.actual_password else current_text.replace('*', '')
                self.password_captured = True
                
                print(f"✅ PASSWORD CAPTURED ON SUBMIT")
                print(f"   └─ Site: {current_site}")
                print(f"   └─ Password: {'*' * min(len(self.potential_password), 8)} (Length: {len(self.potential_password)})")
                print(f"   └─ Context: {'Browser' if self.form_data.get('is_browser', False) else 'Application'}")
                
            elif not self.username_captured:
                self.potential_username = current_text
                self.username_captured = True
                
                print(f"✅ USERNAME CAPTURED ON SUBMIT")
                print(f"   └─ Site: {current_site}")
                print(f"   └─ Username: {self.potential_username[:5]}... (Length: {len(self.potential_username)})")
                print(f"   └─ Context: {'Browser' if self.form_data.get('is_browser', False) else 'Application'}")
        
        # Check credential status and determine action
        if self.username_captured and self.password_captured:
            print("🎯 COMPLETE LOGIN CREDENTIALS READY!")
            print(f"   ✓ Username: {self.potential_username[:5]}...")
            print(f"   ✓ Password: {'*' * min(len(self.potential_password), 8)}")
            print(f"   ✓ Site: {current_site}")
            print("💾 Triggering save prompt...")
            self._enhanced_login_monitoring_summary()
            self._trigger_save_prompt()
            
        elif self.password_captured and not self.username_captured:
            # Password-only login (common in some apps and browser extensions)
            site_name = self.form_data.get('site_name', 'Unknown Site')
            self.potential_username = f"user@{site_name}"
            self.username_captured = True
            
            print(f"🔐 PASSWORD-ONLY LOGIN DETECTED")
            print(f"   └─ Site: {site_name}")
            print(f"   └─ Generated username: {self.potential_username}")
            print(f"   └─ Password: {'*' * min(len(self.potential_password), 8)}")
            print("💾 Triggering save prompt for password-only login...")
            self._enhanced_login_monitoring_summary()
            self._trigger_save_prompt()
            
        elif current_text and not self.username_captured:
            # Might be a single-step login, treat as username for now
            self.potential_username = current_text
            self.username_captured = True
            
            print(f"👤 SINGLE-STEP USERNAME SUBMISSION")
            print(f"   └─ Username: {self.potential_username[:5]}...")
            print(f"   └─ Scheduling delayed check for password...")
            # Schedule delayed check in case password comes later
            self._schedule_delayed_check()
            
        else:
            # For browsers, try to capture any available data
            if self.form_data.get('is_browser', False) and (self.typed_text or self.actual_password):
                print("🌐 PARTIAL BROWSER DATA - scheduling delayed check")
                self._schedule_delayed_check()
            else:
                print("⏳ INCOMPLETE DATA - scheduling delayed check")
                # Schedule delayed check for potential later credential capture
                self._schedule_delayed_check()
        
        print("=" * 50)
        self.typed_text = ""
        self.actual_password = ""  # Reset actual password
    
    def _update_password_field_detection(self, char):
        """Update password field detection based on character patterns."""
        # If typing special characters commonly used in passwords
        password_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        if char in password_chars:
            # More likely to be a password field
            if not self.in_password_field and self.username_captured:
                self.in_password_field = True
                print("Detected password field based on special characters")
    
    def _smart_password_field_detection(self):
        """Smart detection of password fields based on context."""
        if not self.in_password_field and self.username_captured:
            # If we have username and are typing, likely in password field
            text_length = len(self.typed_text)
            
            # Password field heuristics:
            # 1. Typing after username capture
            # 2. Certain length patterns
            # 3. Mixed character types
            if text_length > 3:  # Reasonable password length
                # Check for mixed character types (common in passwords)
                has_letters = any(c.isalpha() for c in self.typed_text.replace('*', ''))
                has_numbers = any(c.isdigit() for c in self.typed_text.replace('*', ''))
                
                if has_letters or has_numbers:
                    self.in_password_field = True
                    print("Smart detection: Likely password field")
    
    def _enhanced_browser_credential_detection(self):
        """Enhanced credential detection specifically for browsers."""
        try:
            if not self.form_data.get('is_browser', False):
                return
            
            # Enhanced browser-specific detection logic
            browser_name = self.form_data.get('process_name', '').lower()
            window_title = self.form_data.get('window_title', '').lower()
            
            # Check for common browser login patterns in URL/title
            login_indicators = [
                'login', 'signin', 'sign-in', 'log-in', 'authenticate', 'auth',
                'account', 'portal', 'dashboard', 'secure', 'password',
                'user', 'email', 'username', 'credentials'
            ]
            
            has_login_indicator = any(indicator in window_title for indicator in login_indicators)
            
            # Enhanced detection for popular browsers
            if 'chrome' in browser_name or 'edge' in browser_name or 'firefox' in browser_name:
                # More aggressive detection for major browsers
                if has_login_indicator or len(self.typed_text) > 2:
                    print(f"🌐 Enhanced {browser_name} detection - Login context detected")
                    
                    # Auto-detect password fields more aggressively in browsers
                    if not self.in_password_field and self.username_captured and len(self.typed_text) > 4:
                        self.in_password_field = True
                        print("🔐 Auto-switching to password field mode in browser")
                    
                    # For browsers, trigger save prompt even with minimal data
                    if self.username_captured and len(self.actual_password) >= 6:
                        print("🌐 Browser credentials appear complete - preparing save prompt")
                        
        except Exception as e:
            print(f"Error in enhanced browser detection: {e}")
    
    def _on_key_release(self, key):
        """Handle key release events."""
        pass
    
    def _on_mouse_click(self, x, y, button, pressed):
        """Enhanced mouse click handling for form field detection and browser login buttons."""
        if pressed:
            # Mouse click indicates field change or button press - critical for browser login forms
            current_text = self.typed_text.strip()
            
            if self.form_data.get('is_browser', False):
                print(f"🌐 Browser click detected - Text: '{current_text[:5] if current_text else 'None'}...' (Password field: {self.in_password_field})")
            
            if current_text:
                if self.in_password_field and not self.password_captured:
                    self.potential_password = self.actual_password if self.actual_password else current_text.replace('*', '')
                    self.password_captured = True
                    print(f"🔑 Password captured on click (length: {len(self.potential_password)}) - Browser: {self.form_data.get('is_browser', False)}")
                elif not self.username_captured:
                    self.potential_username = current_text
                    self.username_captured = True
                    print(f"👤 Username captured on click: {self.potential_username[:3]}... - Browser: {self.form_data.get('is_browser', False)}")
                
                # Reset field detection for new field
                self.in_password_field = False
                self.typed_text = ""
                self.actual_password = ""  # Reset actual password
                
                # If this might be a login button click with both credentials
                if self.username_captured and self.password_captured:
                    print("💾 Both credentials captured on click - triggering save prompt")
                    self._trigger_save_prompt()
                    
                # For browsers, also check for single-field scenarios
                elif self.form_data.get('is_browser', False):
                    if self.password_captured and not self.username_captured:
                        # Browser password-only login
                        site_name = self.form_data.get('site_name', 'Unknown Site')
                        self.potential_username = f"user@{site_name}"
                        print(f"🌐 Browser password-only click for {site_name} - triggering save prompt")
                        self._trigger_save_prompt()
                    elif self.username_captured and not self.password_captured and len(self.potential_username) > 3:
                        # Schedule delayed check for password in browser
                        print("🌐 Browser username captured, waiting for password...")
                        self._schedule_delayed_check()
                        
            else:
                # Click without typed text - might be navigating to new field or clicking login button
                # For browsers, check if we have any captured credentials
                if self.form_data.get('is_browser', False) and (self.username_captured or self.password_captured):
                    print("🌐 Browser click without current text - checking captured credentials")
                    if self.username_captured and self.password_captured:
                        print("💾 Browser login button click detected - triggering save prompt")
                        self._trigger_save_prompt()
                    else:
                        # Schedule delayed check to see if more credentials come
                        self._schedule_delayed_check()
                
                # Reset password field detection
                self.in_password_field = False
                self.actual_password = ""
    
    def _detect_password_field(self):
        """Heuristic to detect if current field is a password field."""
        # This is a simplified detection - in practice, you might use
        # more sophisticated methods like window accessibility APIs
        
        # If we recently typed and now tabbed, and have username, assume password field
        if self.username_captured and not self.password_captured:
            self.in_password_field = True
        else:
            self.in_password_field = False
    
    def _process_save_prompt(self, event_data):
        """Process save prompt events from queue with thread-safe dialog management."""
        try:
            # Check dialog state safely
            with self.dialog_lock:
                if self._save_prompt_open:
                    print("🚫 Save prompt already open - skipping queued prompt")
                    return
                self._save_prompt_open = True
            
            # Prepare credential data
            credential_data = {
                'username': event_data.get('username'),
                'password': event_data.get('password'),
                'site_name': event_data.get('site_data', {}).get('site_name', 'Unknown Site'),
                'site_url': event_data.get('site_data', {}).get('url', ''),
                'window_title': event_data.get('site_data', {}).get('window_title', ''),
                'process_name': event_data.get('site_data', {}).get('process_name', ''),
                'timestamp': time.time(),
                'trigger': event_data.get('trigger', 'unknown')
            }
            
            # FINAL VALIDATION: Double-check credential data before showing save prompt
            username = credential_data['username']
            site_name = credential_data['site_name']
            
            # Skip if any SilentLock-related data
            if (username and ('silentlock' in username.lower() or 'fix this' in username.lower() or 
                            'why username' in username.lower() or '\x16' in username)):
                print(f"🚫 Final validation failed - SilentLock-related username: '{username}' - not saving")
                with self.dialog_lock:
                    self._save_prompt_open = False
                return
                
            if site_name and ('Microsoft​ Edge' in site_name or 'SilentLock' in site_name):
                print(f"🚫 Final validation failed - invalid site name: '{site_name}' - not saving")
                with self.dialog_lock:
                    self._save_prompt_open = False
                return
            
            print(f"💾 Processing save prompt: {credential_data['username']}@{credential_data['site_name']}")
            
            # Call the callback function if available
            if self.on_login_detected:
                self.on_login_detected(credential_data)
            
            # Reset state after triggering
            self._reset_form_state()
            
            # Reset dialog flag
            with self.dialog_lock:
                self._save_prompt_open = False
                
        except Exception as e:
            print(f"Error processing save prompt: {e}")
            with self.dialog_lock:
                self._save_prompt_open = False
    
    def _process_autofill_check(self, event_data):
        """Process autofill check events from queue."""
        try:
            if not self.credential_db or not self.master_password:
                return
            
            site_url = event_data.get('site_url', '')
            site_name = event_data.get('site_name', '')
            
            if not site_url and not site_name:
                return
            
            # Search for credentials
            credentials = None
            if site_url:
                credentials = self.credential_db.search_credentials(site_url, self.master_password)
                if not credentials and site_name:
                    credentials = self.credential_db.search_credentials(site_name, self.master_password)
            else:
                credentials = self.credential_db.search_credentials(site_name, self.master_password)
            
            if credentials:
                self.available_credentials = credentials
                self.current_site_url = site_url or site_name
                self._show_autofill_prompt_safe(credentials)
                
        except Exception as e:
            print(f"Error in autofill check: {e}")
    
    def _trigger_save_prompt(self):
        """Trigger the save credentials prompt using thread-safe queue."""
        try:
            if not (self.potential_username and self.potential_password):
                print("🚫 Missing username or password - cannot save")
                return
            
            # CRITICAL: Clean and validate credential data to prevent corruption
            clean_username = str(self.potential_username).strip()
            clean_password = str(self.potential_password).strip()
            
            # Validate username - should not be window title or corrupted data
            if len(clean_username) < 2:
                print(f"🚫 Username too short: '{clean_username}' - not saving")
                return
                
            # Check for corrupted username (contains window title patterns)
            username_corruption_patterns = [
                'display', 'real time', 'updates', 'microsoft edge', 'chrome', 'firefox',
                'browser', 'tab', 'window', '- personal', 'console', 'management',
                'silentlock', 'password manager', 'credential', 'dialog', 'select',
                'authentication', 'auto-fill', 'why username', 'fix this', 'loop',
                'when were they used', 'or saved', 'real tme', 'aws management',
                'and display', 'tme updates'
            ]
            username_lower = clean_username.lower()
            if any(pattern in username_lower for pattern in username_corruption_patterns):
                print(f"🚫 Corrupted username detected: '{clean_username}' - not saving")
                return
                
            # Check for special characters that indicate corruption (like \x16)
            if any(ord(char) < 32 or ord(char) > 126 for char in clean_username if char not in '\t\n\r'):
                print(f"🚫 Username contains invalid characters: '{repr(clean_username)}' - not saving")
                return
            
            # Validate password
            if len(clean_password) < 1:
                print(f"🚫 Password too short - not saving")
                return
                
            # Check for corrupted password (similar patterns as username)
            password_lower = clean_password.lower()
            if any(pattern in password_lower for pattern in username_corruption_patterns):
                print(f"🚫 Corrupted password detected: '{clean_password[:20]}...' - not saving")
                return
                
            # Check for special characters in password that indicate corruption
            if any(ord(char) < 32 or ord(char) > 126 for char in clean_password if char not in '\t\n\r'):
                print(f"🚫 Password contains invalid characters: '{repr(clean_password[:20])}...' - not saving")
                return
            
            # Get clean site information
            site_name = self.form_data.get('site_name', 'Unknown Site')
            site_url = self.form_data.get('url', self.form_data.get('window_title', 'Unknown'))
            
            # Clean site name from browser-specific suffixes
            browser_suffixes = [' - Google Chrome', ' - Mozilla Firefox', ' - Microsoft Edge', ' - Personal', ' - Chrome']
            for suffix in browser_suffixes:
                if site_name.endswith(suffix):
                    site_name = site_name[:-len(suffix)].strip()
                    
            # Validate site name - prevent saving browser names as sites
            invalid_site_names = [
                'Microsoft Edge', 'Google Chrome', 'Mozilla Firefox', 'Safari', 
                'Internet Explorer', 'Opera', 'Brave', 'SilentLock',
                'Unknown Site', 'Program Manager', 'Desktop', 'Taskbar'
            ]
            if site_name in invalid_site_names or site_name.startswith('Microsoft​'):
                print(f"🚫 Invalid site name detected: '{site_name}' - not saving")
                return
            
            print(f"💾 QUEUEING CLEAN CREDENTIAL: User='{clean_username}', Site='{site_name}', URL='{site_url[:50]}...'")
            
            # Queue save prompt instead of processing directly
            self.event_processor.add_event("save_prompt", {
                'username': clean_username,
                'password': clean_password,
                'site_data': {
                    'site_name': site_name,
                    'url': site_url,
                    'window_title': self.form_data.get('window_title', ''),
                    'process_name': self.form_data.get('process_name', ''),
                    'is_browser': self.form_data.get('is_browser', False)
                },
                'trigger': 'manual'
            })
            
        except Exception as e:
            print(f"Error queueing save prompt: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_autofill_prompt_safe(self, credentials):
        """Thread-safe autofill prompt handling."""
        try:
            with self.dialog_lock:
                if self._autofill_dialog_open or self.fill_prompt_shown:
                    print("🚫 Autofill dialog already open or shown")
                    return
                self._autofill_dialog_open = True
                self.fill_prompt_shown = True
            
            # Show autofill prompt (existing logic)
            self._show_autofill_prompt(credentials)
            
        except Exception as e:
            print(f"Error in safe autofill prompt: {e}")
        finally:
            with self.dialog_lock:
                self._autofill_dialog_open = False
    
    def _check_for_autofill_opportunity(self):
        """Check if we have stored credentials using thread-safe queue."""
        if not self.credential_db or not self.master_password:
            return
        
        site_url = self.form_data.get('url', self.form_data.get('site_name', ''))
        site_name = self.form_data.get('site_name', '')
        
        if site_url or site_name:
            # Queue autofill check instead of processing directly
            self.event_processor.add_event("autofill_check", {
                'site_url': site_url,
                'site_name': site_name,
                'timestamp': time.time()
            })
            
        try:
            if not site_url and not site_name:
                return
            
            # Search for credentials by URL or site name
            if site_url:
                # Try exact URL match first
                credentials = self.credential_db.search_credentials(site_url, self.master_password)
                if not credentials and site_name:
                    # Try site name if URL search fails
                    credentials = self.credential_db.search_credentials(site_name, self.master_password)
            else:
                # Search by site name
                credentials = self.credential_db.search_credentials(site_name, self.master_password)
            
            if credentials:
                self.available_credentials = credentials
                self.current_site_url = site_url or site_name
                self._show_autofill_prompt(credentials)
                
        except Exception as e:
            print(f"Error checking for autofill: {e}")
    
    def _show_autofill_prompt(self, credentials):
        """Show user prompt for auto-filling credentials with loop prevention."""
        if self.fill_prompt_shown or not credentials:
            return
        
        # CRITICAL: Prevent infinite dialog loops
        if hasattr(self, '_autofill_dialog_open') and self._autofill_dialog_open:
            print("🚫 Autofill dialog already open - preventing loop")
            return
            
        self.fill_prompt_shown = True
        self._autofill_dialog_open = True
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Create temporary window for prompt
            root = tk.Tk()
            root.withdraw()
            
            if len(credentials) == 1:
                cred = credentials[0]
                site_name = cred.get('site_name', 'Unknown Site')
                username = cred.get('username', 'Unknown User')
                
                message = f"Auto-fill login for {username}@{site_name}?"
                result = messagebox.askyesno("SilentLock Auto-Fill", message)
                
                if result:
                    self._perform_autofill(cred)
                
                # Reset flags after user responds
                self.fill_prompt_shown = False
                self._autofill_dialog_open = False
                
                # Use a timer to prevent immediate re-prompting
                threading.Timer(5.0, self._reset_autofill_flag).start()
                
            else:
                # Multiple credentials - show selection
                self.fill_prompt_shown = False  # Reset this so selection dialog can show
                self._autofill_dialog_open = False
                self._show_credential_selection(credentials)
                
            root.destroy()
            
        except Exception as e:
            print(f"Error showing autofill prompt: {e}")
            # Reset flags on error
            self.fill_prompt_shown = False
            self._autofill_dialog_open = False
    
    def _reset_autofill_flag(self):
        """Reset the auto-fill prompt flag after a delay."""
        self.fill_prompt_shown = False
    
    def _show_credential_selection(self, credentials):
        """Show enhanced selection dialog for multiple credentials with accurate display and prevent loops."""
        try:
            # CRITICAL: Prevent dialog loops by checking if a selection dialog is already open
            if hasattr(self, '_selection_dialog_open') and self._selection_dialog_open:
                print("🚫 Credential selection dialog already open - preventing loop")
                return
                
            self._selection_dialog_open = True
            
            import tkinter as tk
            from tkinter import ttk
            
            selection_window = tk.Toplevel()
            selection_window.title("Select Credential")
            selection_window.geometry("700x450")  # Even larger window for better display
            selection_window.transient()
            selection_window.grab_set()
            selection_window.resizable(True, True)
            
            # Ensure dialog closes properly to prevent loops
            def on_close():
                self._selection_dialog_open = False
                selection_window.destroy()
            
            selection_window.protocol("WM_DELETE_WINDOW", on_close)
            
            # Center the window
            selection_window.update_idletasks()
            x = (selection_window.winfo_screenwidth() // 2) - (700 // 2)
            y = (selection_window.winfo_screenheight() // 2) - (450 // 2)
            selection_window.geometry(f"+{x}+{y}")
            
            # Debug: Print credential data to identify the issue
            print("🔍 DEBUG: Credential data being displayed:")
            for i, cred in enumerate(credentials):
                print(f"  Credential {i+1}: {cred}")
            
            # Header
            header_frame = tk.Frame(selection_window)
            header_frame.pack(fill='x', padx=20, pady=10)
            
            tk.Label(header_frame, text="Multiple credentials found. Select one:", 
                    font=('Arial', 12, 'bold')).pack()
            
            # Enhanced Treeview for better credential display
            tree_frame = tk.Frame(selection_window)
            tree_frame.pack(fill='both', expand=True, padx=20, pady=10)
            
            # Create Treeview with columns
            columns = ('Site', 'Username', 'URL')
            tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=10)
            
            # Configure columns
            tree.heading('#0', text='#', anchor='w')
            tree.heading('Site', text='Site Name', anchor='w')
            tree.heading('Username', text='Username', anchor='w')
            tree.heading('URL', text='URL', anchor='w')
            
            # Configure column widths for better display
            tree.column('#0', width=50, minwidth=50)
            tree.column('Site', width=180, minwidth=120)
            tree.column('Username', width=200, minwidth=150)
            tree.column('URL', width=250, minwidth=180)
            
            # Add scrollbars
            v_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
            h_scrollbar = ttk.Scrollbar(tree_frame, orient='horizontal', command=tree.xview)
            tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # Populate treeview with CORRECTED credential information
            for i, cred in enumerate(credentials, 1):
                # FIX: Get the correct field names from the credential dictionary
                # Try multiple possible field name variations
                site_name = (cred.get('site_name') or cred.get('site') or 
                           cred.get('domain') or cred.get('service') or 'Unknown Site')
                
                username = (cred.get('username') or cred.get('user') or 
                          cred.get('email') or cred.get('login') or 'No Username')
                
                site_url = (cred.get('site_url') or cred.get('url') or 
                          cred.get('website') or cred.get('domain') or 'No URL')
                
                # Clean up and validate the display values
                if not isinstance(site_name, str):
                    site_name = str(site_name) if site_name else 'Unknown Site'
                if not isinstance(username, str):
                    username = str(username) if username else 'No Username' 
                if not isinstance(site_url, str):
                    site_url = str(site_url) if site_url else 'No URL'
                
                # Intelligent truncation with full data preservation
                display_site = site_name[:25] + "..." if len(site_name) > 25 else site_name
                display_username = username[:35] + "..." if len(username) > 35 else username
                display_url = site_url[:40] + "..." if len(site_url) > 40 else site_url
                
                print(f"🔍 Credential {i}: Site='{display_site}', User='{display_username}', URL='{display_url}'")
                
                tree.insert('', 'end', text=str(i), 
                           values=(display_site, display_username, display_url))
            
            # Pack treeview and scrollbars
            tree.pack(side='left', fill='both', expand=True)
            v_scrollbar.pack(side='right', fill='y')
            h_scrollbar.pack(side='bottom', fill='x')
            
            # Selection info frame
            info_frame = tk.Frame(selection_window)
            info_frame.pack(fill='x', padx=20, pady=5)
            
            info_label = tk.Label(info_frame, text="Select a credential and click Auto-Fill, or double-click to auto-fill immediately.", 
                                 font=('Arial', 9), fg='gray')
            info_label.pack()
            
            # Buttons
            button_frame = tk.Frame(selection_window)
            button_frame.pack(pady=15)
            
            def on_select():
                try:
                    selection = tree.selection()
                    if selection:
                        # Get the index from the tree item
                        item = tree.item(selection[0])
                        item_index = int(item['text']) - 1  # Convert back to 0-based index
                        
                        if 0 <= item_index < len(credentials):
                            selected_cred = credentials[item_index]
                            print(f"🔐 Auto-filling credential: {selected_cred.get('username', 'Unknown')}@{selected_cred.get('site_name', 'Unknown')}")
                            self._perform_autofill(selected_cred)
                    self._selection_dialog_open = False
                    selection_window.destroy()
                except Exception as e:
                    print(f"Error in credential selection: {e}")
                    self._selection_dialog_open = False
                    selection_window.destroy()
            
            def on_cancel():
                try:
                    print("🚫 Credential selection cancelled")
                    self._selection_dialog_open = False
                    selection_window.destroy()
                except Exception as e:
                    print(f"Error closing selection dialog: {e}")
                    self._selection_dialog_open = False
            
            def on_double_click(event):
                on_select()
            
            # Bind double-click to auto-select
            tree.bind('<Double-1>', on_double_click)
            
            # Enhanced buttons with improved error handling
            tk.Button(button_frame, text="Auto-Fill Selected", command=on_select, 
                     bg='#4CAF50', fg='white', font=('Arial', 10, 'bold'), 
                     padx=20).pack(side='left', padx=10)
            tk.Button(button_frame, text="Cancel", command=on_cancel,
                     bg='#f44336', fg='white', font=('Arial', 10), 
                     padx=20).pack(side='left', padx=10)
            
            # Auto-select first item
            if tree.get_children():
                tree.selection_set(tree.get_children()[0])
                tree.focus(tree.get_children()[0])
            
            # Focus on window
            selection_window.focus_set()
            
            print(f"📋 Showing credential selection dialog with {len(credentials)} accurate options")
            selection_window.wait_window()
            
            # Ensure flag is reset when dialog closes
            self._selection_dialog_open = False
            
        except Exception as e:
            print(f"Error showing enhanced credential selection: {e}")
            self._selection_dialog_open = False
            import traceback
            traceback.print_exc()
    
    def _perform_autofill(self, credential):
        """Perform the actual auto-filling of credentials."""
        try:
            import time
            from pynput.keyboard import Controller, Key
            
            print(f"Auto-filling credential for {credential['username']}@{credential['site_name']}")
            
            keyboard = Controller()
            
            # Small delay to ensure focus
            time.sleep(0.5)
            
            # Clear any existing text in field and type username
            keyboard.press(Key.ctrl)
            keyboard.press('a')
            keyboard.release('a')
            keyboard.release(Key.ctrl)
            
            time.sleep(0.1)
            keyboard.type(credential['username'])
            
            # Tab to password field
            time.sleep(0.2)
            keyboard.press(Key.tab)
            
            # Type password
            time.sleep(0.2)
            keyboard.type(credential['password'])
            
            print(f"Auto-fill completed for {credential['username']}")
            
            # Show success notification
            self._show_notification("Auto-Fill Complete", 
                                  f"Filled credentials for {credential['username']}@{credential['site_name']}")
            
        except Exception as e:
            print(f"Error performing autofill: {e}")
            self._show_notification("Auto-Fill Failed", 
                                  f"Could not auto-fill credentials: {str(e)}")
    
    def _show_notification(self, title, message, duration=3000):
        """Show desktop notification."""
        try:
            # Try Windows 10+ toast notifications first
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    timeout=duration // 1000
                )
                return
            except ImportError:
                pass
            
            # Fallback to tkinter notification
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            
            # Create a small notification window
            notification_window = tk.Toplevel(root)
            notification_window.title("SilentLock")
            notification_window.geometry("300x100")
            notification_window.resizable(False, False)
            
            # Position at bottom right
            notification_window.attributes('-topmost', True)
            x = notification_window.winfo_screenwidth() - 320
            y = notification_window.winfo_screenheight() - 150
            notification_window.geometry(f"+{x}+{y}")
            
            # Content
            tk.Label(notification_window, text=title, font=('Arial', 12, 'bold')).pack(pady=5)
            tk.Label(notification_window, text=message, wraplength=280).pack(pady=5)
            
            # Auto-close after duration
            notification_window.after(duration, notification_window.destroy)
            
            # Show and clean up
            notification_window.lift()
            notification_window.after(duration + 100, root.destroy)
            
        except Exception as e:
            print(f"Error showing notification: {e}")
    
    def set_credential_db(self, db_manager, master_password):
        """Set the credential database for auto-fill functionality."""
        self.credential_db = db_manager
        self.master_password = master_password

    def _is_login_page_context(self):
        """Check if current context appears to be a login page."""
        if not hasattr(self, 'form_data') or not self.form_data:
            return False
            
        title = self.form_data.get('window_title', '').lower()
        site_name = self.form_data.get('site_name', '').lower()
        url = self.form_data.get('url', '').lower()
        
        # Login page indicators
        login_indicators = [
            'login', 'signin', 'sign-in', 'sign in', 'auth', 'authentication',
            'password', 'username', 'account', 'portal', 'dashboard',
            'security', 'access', 'credentials', 'sso', 'oauth'
        ]
        
        context = f"{title} {site_name} {url}"
        return any(indicator in context for indicator in login_indicators)
        
    def _analyze_password_strength(self):
        """Analyze password strength in real-time."""
        if not self.actual_password:
            return
            
        password = self.actual_password
        length = len(password)
        
        # Basic strength indicators
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        strength = "WEAK"
        if length >= 8 and sum([has_upper, has_lower, has_digit, has_special]) >= 3:
            strength = "STRONG"
        elif length >= 6 and sum([has_upper, has_lower, has_digit, has_special]) >= 2:
            strength = "MEDIUM"
            
        if length >= 8:  # Only show strength for reasonable passwords
            print(f"🔒 Password Strength: {strength} | Length: {length} | Complexity: {'HIGH' if sum([has_upper, has_lower, has_digit, has_special]) >= 3 else 'LOW'}")
            
    def _validate_current_input(self):
        """Validate current input for potential issues."""
        try:
            current_window = self.form_data.get('site_name', 'Unknown')
            
            # Check for suspicious input patterns
            if not self.in_password_field and self.typed_text:
                # Username validation
                if len(self.typed_text) > 100:
                    print(f"⚠️ Very long username detected ({len(self.typed_text)} chars) on {current_window}")
                    
                if any(char in self.typed_text for char in '<>"\':'):
                    print(f"⚠️ Suspicious characters in username on {current_window}")
                    
            elif self.in_password_field and self.actual_password:
                # Password validation
                if len(self.actual_password) > 200:
                    print(f"⚠️ Very long password detected ({len(self.actual_password)} chars) on {current_window}")
                    
                # Check for potential credential paste
                if len(self.actual_password) - len(self.typed_text[:-1]) > 5:
                    print(f"📋 Potential password paste detected on {current_window}")
                    
        except Exception as e:
            print(f"Error in input validation: {e}")
            
    def _enhanced_login_monitoring_summary(self):
        """Provide enhanced monitoring summary."""
        try:
            site_name = self.form_data.get('site_name', 'Unknown')
            is_browser = self.form_data.get('is_browser', False)
            
            print(f"\n🎯 LOGIN MONITORING SUMMARY for {site_name}")
            print("=" * 50)
            print(f"📍 Context: {'Browser' if is_browser else 'Application'}")
            print(f"👤 Username Status: {'CAPTURED' if self.username_captured else 'MONITORING'}")
            if self.username_captured:
                print(f"   └─ Username: {self.potential_username[:5]}... ({len(self.potential_username)} chars)")
            
            print(f"🔐 Password Status: {'CAPTURED' if self.password_captured else 'MONITORING'}")
            if self.password_captured:
                print(f"   └─ Password: {'*' * min(len(self.potential_password), 8)} ({len(self.potential_password)} chars)")
                
            print(f"🔄 Current Field: {'PASSWORD' if self.in_password_field else 'USERNAME'}")
            print(f"📝 Current Input Length: {len(self.typed_text)}")
            print(f"⏰ Last Activity: {time.time() - self.last_input_time:.1f}s ago")
            
            if self.username_captured and self.password_captured:
                print("✅ READY FOR SAVE PROMPT")
            else:
                print("⏳ Waiting for complete credentials...")
            print("=" * 50)
            
        except Exception as e:
            print(f"Error in monitoring summary: {e}")

    def _process_comprehensive_browser_scan(self, event_data):
        """Comprehensive scanning of all browser tabs for login detection."""
        try:
            print("🌐 COMPREHENSIVE BROWSER TAB SCAN - Detecting all login tabs...")
            
            def scan_all_browser_tabs(hwnd, detected_tabs):
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return True
                        
                    window_title = win32gui.GetWindowText(hwnd)
                    if not window_title or len(window_title) < 3:
                        return True
                    
                    # Get process information
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    # Check if it's a browser
                    browser_processes = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe', 'safari.exe']
                    if not any(browser in process_name for browser in browser_processes):
                        return True
                    
                    # Analyze title for login indicators
                    title_lower = window_title.lower()
                    
                    # Enhanced login detection patterns
                    login_patterns = [
                        'login', 'log in', 'sign in', 'signin', 'log on', 'logon',
                        'authenticate', 'auth', 'portal', 'sso', 'access',
                        'account', 'username', 'password', 'credentials',
                        'student', 'blackboard', 'canvas', 'moodle', 'brightspace',
                        'university', 'college', 'edu', 'academic', 'library',
                        'google', 'microsoft', 'office', 'outlook', 'teams',
                        'facebook', 'github', 'linkedin', 'twitter', 'instagram'
                    ]
                    
                    # Educational site patterns
                    edu_patterns = [
                        '.edu', 'university', 'college', 'academic', 'student',
                        'blackboard', 'canvas', 'moodle', 'brightspace', 'd2l',
                        'library', 'portal', 'campus', 'school'
                    ]
                    
                    # URL-based detection
                    url_patterns = [
                        'login.', 'auth.', 'portal.', 'signin.', 'sso.',
                        'accounts.', 'my.', 'student.', 'staff.'
                    ]
                    
                    # Check for login indicators
                    is_login_page = False
                    
                    # Check basic login patterns
                    if any(pattern in title_lower for pattern in login_patterns):
                        is_login_page = True
                        print(f"   📋 Login pattern detected: {window_title}")
                    
                    # Check educational patterns
                    if any(pattern in title_lower for pattern in edu_patterns):
                        is_login_page = True
                        print(f"   🎓 Educational site detected: {window_title}")
                    
                    # Check URL patterns in title
                    if any(pattern in title_lower for pattern in url_patterns):
                        is_login_page = True
                        print(f"   🔗 URL login pattern detected: {window_title}")
                    
                    if is_login_page:
                        detected_tabs.append({
                            'hwnd': hwnd,
                            'title': window_title,
                            'process': process_name,
                            'browser': process_name.replace('.exe', '').title()
                        })
                        print(f"   ✅ Login tab found: {window_title} in {process_name}")
                        
                        # Queue window analysis
                        self.event_processor.add_event('window_change', {
                            'hwnd': hwnd,
                            'title': window_title,
                            'process_name': process_name
                        })
                
                except Exception as e:
                    print(f"   ❌ Error scanning window: {e}")
                    
                return True
            
            # Scan all windows
            detected_tabs = []
            win32gui.EnumWindows(scan_all_browser_tabs, detected_tabs)
            
            if detected_tabs:
                print(f"🌐 Found {len(detected_tabs)} browser tabs with potential login forms:")
                for tab in detected_tabs:
                    print(f"   • {tab['browser']}: {tab['title']}")
            else:
                print("🌐 No login tabs detected in browser scan")
                
        except Exception as e:
            print(f"❌ Error in comprehensive browser scan: {e}")

    def _process_comprehensive_app_scan(self, event_data):
        """Comprehensive scanning of all applications for login windows."""
        try:
            print("📱 COMPREHENSIVE APP SCAN - Detecting login applications...")
            
            def scan_all_app_windows(hwnd, detected_apps):
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return True
                        
                    window_title = win32gui.GetWindowText(hwnd)
                    if not window_title or len(window_title) < 2:
                        return True
                    
                    # Get process information
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    process = psutil.Process(pid)
                    process_name = process.name().lower()
                    
                    # Skip browsers (handled separately)
                    browser_processes = ['chrome.exe', 'firefox.exe', 'msedge.exe', 'opera.exe', 'brave.exe', 'safari.exe']
                    if any(browser in process_name for browser in browser_processes):
                        return True
                    
                    title_lower = window_title.lower()
                    
                    # Application login patterns
                    app_login_patterns = [
                        'login', 'log in', 'sign in', 'signin', 'authenticate',
                        'password', 'username', 'credentials', 'account',
                        'setup', 'configuration', 'settings', 'preferences',
                        'connect', 'connection', 'server', 'host'
                    ]
                    
                    # Specific application patterns
                    app_specific_patterns = {
                        'discord': ['discord', 'login', 'auth'],
                        'slack': ['slack', 'workspace', 'sign in'],
                        'teams': ['microsoft teams', 'teams', 'office'],
                        'zoom': ['zoom', 'meeting', 'conference'],
                        'steam': ['steam', 'valve', 'game'],
                        'battlenet': ['battle.net', 'blizzard', 'battlenet'],
                        'epic': ['epic games', 'unreal', 'fortnite'],
                        'putty': ['putty', 'ssh', 'telnet'],
                        'winscp': ['winscp', 'sftp', 'scp'],
                        'filezilla': ['filezilla', 'ftp'],
                        'outlook': ['outlook', 'mail', 'email'],
                        'thunderbird': ['thunderbird', 'mozilla']
                    }
                    
                    # Check for general login patterns
                    is_login_app = any(pattern in title_lower for pattern in app_login_patterns)
                    
                    # Check for specific app patterns
                    app_type = 'Unknown'
                    for app_name, patterns in app_specific_patterns.items():
                        if any(pattern in title_lower or pattern in process_name for pattern in patterns):
                            is_login_app = True
                            app_type = app_name.title()
                            break
                    
                    if is_login_app:
                        detected_apps.append({
                            'hwnd': hwnd,
                            'title': window_title,
                            'process': process_name,
                            'app_type': app_type
                        })
                        print(f"   📱 Login app found: {window_title} ({app_type})")
                        
                        # Queue window analysis
                        self.event_processor.add_event('window_change', {
                            'hwnd': hwnd,
                            'title': window_title,
                            'process_name': process_name
                        })
                
                except Exception as e:
                    print(f"   ❌ Error scanning app window: {e}")
                    
                return True
            
            # Scan all windows
            detected_apps = []
            win32gui.EnumWindows(scan_all_app_windows, detected_apps)
            
            if detected_apps:
                print(f"📱 Found {len(detected_apps)} applications with potential login windows:")
                for app in detected_apps:
                    print(f"   • {app['app_type']}: {app['title']}")
            else:
                print("📱 No login applications detected in app scan")
                
        except Exception as e:
            print(f"❌ Error in comprehensive app scan: {e}")


class FormDataExtractor:
    """Helper class for extracting form data from various sources."""
    
    @staticmethod
    def extract_domain_from_url(url: str) -> str:
        """Extract domain from URL for site identification."""
        if not url:
            return "Unknown"
        
        # Remove protocol
        if '://' in url:
            url = url.split('://', 1)[1]
        
        # Remove path
        if '/' in url:
            url = url.split('/', 1)[0]
        
        # Remove port
        if ':' in url:
            url = url.split(':', 1)[0]
        
        return url.lower()
    
    @staticmethod
    def clean_site_name(title: str) -> str:
        """Clean and extract site name from window title."""
        if not title:
            return "Unknown Site"
        
        # Remove common browser suffixes
        suffixes_to_remove = [
            '- Google Chrome',
            '- Mozilla Firefox',
            '- Microsoft Edge',
            '- Internet Explorer'
        ]
        
        cleaned_title = title
        for suffix in suffixes_to_remove:
            if cleaned_title.endswith(suffix):
                cleaned_title = cleaned_title[:-len(suffix)].strip()
        
        # Take first part before dash
        if ' - ' in cleaned_title:
            cleaned_title = cleaned_title.split(' - ')[0]
        
        return cleaned_title[:50]  # Limit length
