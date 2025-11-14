#!/usr/bin/env python3
"""
SilentLock Password Manager
Main application entry point.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox
import threading
import time
import traceback

# Add src directory to path
src_dir = os.path.join(os.path.dirname(__file__), 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from src.gui import SilentLockGUI
    from src.database import DatabaseManager
    from src.startup_manager import AutoStartService
    from src.security_hardening import get_security_manager, SecurityHardening
    from src.audit_logger import AuditLogger
    from src.splash_screen import SplashScreen
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)


class SilentLockApp:
    """Main application class for SilentLock password manager."""
    
    def __init__(self):
        self.gui = None
        self.is_running = False
        self.auto_start_service = AutoStartService()
        self.security_manager = None
        self.audit_logger = None
        self.db_manager = None
    
    def start(self):
        """Start the SilentLock application."""
        try:
            print("Starting SilentLock Password Manager...")
            
            # Check for required dependencies
            self._check_dependencies()
            
            # Initialize security hardening
            print("Initializing security hardening...")
            self.security_manager = get_security_manager()
            
            if self.security_manager:
                # Start security monitoring
                self.security_manager.start_monitoring()
                print("✓ Security hardening enabled")
                
                # Check for threats
                threat_check = self.security_manager.check_threats()
                if threat_check['threats_detected']:
                    print(f"⚠️ Security threats detected: {threat_check['threat_count']}")
                    for threat in threat_check['threats']:
                        print(f"  - {threat['type']}: {threat['description']}")
                else:
                    print("✓ No immediate threats detected")
            else:
                print("⚠️ Security hardening not available - some features may be limited")
            
            # Initialize database
            print("Initializing database...")
            self.db_manager = DatabaseManager()
            
            # Initialize audit logging
            print("Initializing audit logging...")
            self.audit_logger = AuditLogger(self.db_manager)
            
            # Log application startup
            self.audit_logger.log_system_event(
                event_type="application_start",
                details={
                    "version": "1.0",
                    "security_hardening": self.security_manager is not None,
                    "python_version": sys.version,
                    "platform": os.name
                }
            )
            
            # Setup auto-start on first run
            self.auto_start_service.setup_auto_start()
            
            # Initialize GUI with security components
            self.gui = SilentLockGUI()
            
            # Inject security components into GUI
            if hasattr(self.gui, 'set_security_components'):
                self.gui.set_security_components(
                    security_manager=self.security_manager,
                    audit_logger=self.audit_logger
                )
            
            self.gui.root.protocol("WM_DELETE_WINDOW", self.on_closing)
            
            self.is_running = True
            print("SilentLock started successfully!")
            print("Note: For full monitoring capabilities, run as Administrator")
            
            # Auto-start monitoring if configured
            if self._should_auto_start_monitoring():
                print("Auto-starting monitoring...")
                self.gui.root.after(1000, self.gui._start_monitoring)  # Start after 1 second
            
            # Start GUI main loop
            self.gui.run()
            
        except Exception as e:
            error_msg = f"Failed to start SilentLock: {e}"
            print(error_msg)
            print("\nDetailed error:")
            traceback.print_exc()
            
            # Try to show error in GUI if possible
            try:
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("SilentLock Error", f"{error_msg}\n\nCheck console for details.")
                root.destroy()
            except:
                pass
            
            sys.exit(1)
    
    def _check_dependencies(self):
        """Check if all required dependencies are available."""
        required_modules = [
            ('cryptography', 'Encryption library'),
            ('pynput', 'Input monitoring'),
            ('win32gui', 'Windows GUI access'),
            ('psutil', 'Process monitoring'),
            ('pyotp', '2FA authentication'),
            ('qrcode', 'QR code generation'),
            ('requests', 'HTTP requests'),
            ('zxcvbn', 'Password strength analysis')
        ]
        
        missing_modules = []
        for module_name, description in required_modules:
            try:
                __import__(module_name)
            except ImportError:
                missing_modules.append(f"{module_name} ({description})")
        
        if missing_modules:
            error_msg = f"Missing required dependencies:\n" + "\n".join(f"- {m}" for m in missing_modules)
            error_msg += f"\n\nPlease install missing packages:\npip install -r requirements.txt"
            print(error_msg)
            raise ImportError(error_msg)
    
    def _should_auto_start_monitoring(self):
        """Check if monitoring should start automatically."""
        try:
            config = self.auto_start_service._load_config()
            # Auto-start monitoring if the app was started via Windows startup
            return config.get('auto_start_enabled', False)
        except Exception:
            return False
    
    def on_closing(self):
        """Handle application closing."""
        try:
            print("Shutting down SilentLock...")
            
            # Log application shutdown
            if self.audit_logger:
                self.audit_logger.log_system_event(
                    event_type="application_shutdown",
                    details={"clean_shutdown": True}
                )
            
            if self.gui:
                # Stop monitoring if running
                if hasattr(self.gui, 'is_monitoring') and self.gui.is_monitoring:
                    print("Stopping monitoring...")
                    self.gui._stop_monitoring()
                
                # Close GUI
                self.gui.on_closing()
            
            # Stop security manager
            if self.security_manager:
                print("Stopping security monitoring...")
                self.security_manager.stop_monitoring()
                print("✓ Security monitoring stopped")
            
            # Close database connection
            if self.db_manager:
                self.db_manager.close_connection()
            
            self.is_running = False
            print("SilentLock closed successfully.")
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            if self.audit_logger:
                self.audit_logger.log_system_event(
                    event_type="application_shutdown",
                    details={"clean_shutdown": False, "error": str(e)},
                    success=False,
                    error_message=str(e)
                )
        
        finally:
            sys.exit(0)


def main():
    """Main entry point."""
    print("="*50)
    print("SilentLock Password Manager v1.0")
    print("Secure, Ethical Password Management")
    print("="*50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required!")
        sys.exit(1)
    
    # Show splash screen during initialization
    splash = SplashScreen()
    
    try:
        # Initialize application while splash is shown
        app = SilentLockApp()
        
        # Wait for splash to finish (small delay for user to see it)
        time.sleep(2)
        splash.close()
        
        # Start main application
        app.start()
        
    except Exception as e:
        print(f"Error during startup: {e}")
        try:
            splash.close()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()