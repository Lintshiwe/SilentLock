"""
Windows startup integration for SilentLock password manager.
Handles auto-start functionality and system tray integration.
"""

import os
import sys
import winreg as reg
import tempfile
import subprocess
from pathlib import Path


class WindowsStartupManager:
    """Manages Windows startup integration for SilentLock."""
    
    def __init__(self, app_name="SilentLock", app_path=None):
        self.app_name = app_name
        self.app_path = app_path or sys.executable
        self.script_path = os.path.abspath(sys.argv[0])
        
        # Registry key for startup programs
        self.startup_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
        
    def is_startup_enabled(self):
        """Check if SilentLock is set to start with Windows."""
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, self.startup_key) as key:
                try:
                    value, _ = reg.QueryValueEx(key, self.app_name)
                    return True
                except FileNotFoundError:
                    return False
        except Exception as e:
            print(f"Error checking startup status: {e}")
            return False
    
    def enable_startup(self):
        """Enable SilentLock to start with Windows."""
        try:
            # Create command to run SilentLock
            if self.script_path.endswith('.py'):
                # If running from Python script
                command = f'"{self.app_path}" "{self.script_path}"'
            else:
                # If running from executable
                command = f'"{self.script_path}"'
            
            # Add to registry
            with reg.CreateKey(reg.HKEY_CURRENT_USER, self.startup_key) as key:
                reg.SetValueEx(key, self.app_name, 0, reg.REG_SZ, command)
            
            print("SilentLock enabled for Windows startup")
            return True
            
        except Exception as e:
            print(f"Error enabling startup: {e}")
            return False
    
    def disable_startup(self):
        """Disable SilentLock from starting with Windows."""
        try:
            with reg.OpenKey(reg.HKEY_CURRENT_USER, self.startup_key, 0, reg.KEY_ALL_ACCESS) as key:
                try:
                    reg.DeleteValue(key, self.app_name)
                    print("SilentLock disabled from Windows startup")
                    return True
                except FileNotFoundError:
                    # Already not in startup
                    return True
                    
        except Exception as e:
            print(f"Error disabling startup: {e}")
            return False
    
    def toggle_startup(self):
        """Toggle startup status."""
        if self.is_startup_enabled():
            return self.disable_startup()
        else:
            return self.enable_startup()


class SystemTrayManager:
    """Manages system tray integration (basic implementation)."""
    
    def __init__(self, app_instance=None):
        self.app_instance = app_instance
        self.tray_icon = None
    
    def create_tray_icon(self):
        """Create system tray icon (requires additional libraries)."""
        try:
            # This would require pystray or similar library
            # For now, just print message
            print("System tray integration would require additional libraries (pystray)")
            return False
            
        except Exception as e:
            print(f"Error creating tray icon: {e}")
            return False
    
    def show_tray_notification(self, title, message):
        """Show notification via system tray."""
        try:
            # Windows toast notification fallback
            import subprocess
            
            # Use PowerShell to show toast notification
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
            [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
            
            $template = @"
            <toast>
                <visual>
                    <binding template="ToastText02">
                        <text id="1">{title}</text>
                        <text id="2">{message}</text>
                    </binding>
                </visual>
            </toast>
"@
            
            $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
            $xml.LoadXml($template)
            $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("SilentLock").Show($toast)
            '''
            
            subprocess.run(["powershell", "-Command", ps_script], 
                         capture_output=True, text=True, timeout=10)
            
        except Exception as e:
            print(f"Error showing tray notification: {e}")


class AutoStartService:
    """Service for managing auto-start behavior."""
    
    def __init__(self):
        self.startup_manager = WindowsStartupManager()
        self.tray_manager = SystemTrayManager()
        self.config_file = os.path.join(os.path.expanduser("~"), ".silentlock_config")
    
    def setup_auto_start(self):
        """Setup auto-start configuration."""
        try:
            # Check if first run
            if not os.path.exists(self.config_file):
                self._first_run_setup()
            
            # Enable startup if configured
            config = self._load_config()
            if config.get('auto_start_enabled', False):
                self.startup_manager.enable_startup()
                
        except Exception as e:
            print(f"Error setting up auto-start: {e}")
    
    def _first_run_setup(self):
        """Handle first run setup."""
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            
            # Ask user if they want auto-start
            enable_auto = messagebox.askyesno(
                "SilentLock Setup",
                "Would you like SilentLock to start automatically when Windows starts?\n\n"
                "This will enable continuous password monitoring and auto-fill."
            )
            
            # Save configuration
            config = {
                'auto_start_enabled': enable_auto,
                'first_run_complete': True
            }
            self._save_config(config)
            
            # Enable startup if requested
            if enable_auto:
                self.startup_manager.enable_startup()
                messagebox.showinfo("Setup Complete", 
                                  "SilentLock will now start automatically with Windows!")
            
            root.destroy()
            
        except Exception as e:
            print(f"Error in first run setup: {e}")
    
    def _load_config(self):
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                import json
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
        
        return {}
    
    def _save_config(self, config):
        """Save configuration to file."""
        try:
            import json
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def check_startup_status(self):
        """Check and return startup status."""
        return {
            'registry_enabled': self.startup_manager.is_startup_enabled(),
            'config_enabled': self._load_config().get('auto_start_enabled', False)
        }
    
    def update_startup_setting(self, enabled):
        """Update startup setting."""
        try:
            # Update registry
            if enabled:
                success = self.startup_manager.enable_startup()
            else:
                success = self.startup_manager.disable_startup()
            
            if success:
                # Update config file
                config = self._load_config()
                config['auto_start_enabled'] = enabled
                self._save_config(config)
                
            return success
            
        except Exception as e:
            print(f"Error updating startup setting: {e}")
            return False


def create_silent_startup_launcher():
    """Create a silent launcher script for startup."""
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        main_script = os.path.join(os.path.dirname(app_dir), 'main.py')
        
        launcher_content = f'''
import sys
import os
import subprocess

# Hide console window
import ctypes
from ctypes import wintypes

def hide_console():
    """Hide the console window for silent startup."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass

if __name__ == "__main__":
    hide_console()
    
    # Set up paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = r"{main_script}"
    python_exe = sys.executable
    
    try:
        # Run SilentLock in the background
        subprocess.Popen([python_exe, main_script], 
                        creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        # Log error to file
        with open(os.path.join(script_dir, "startup_error.log"), "w") as f:
            f.write(f"Startup error: {{e}}")
'''
        
        launcher_path = os.path.join(app_dir, 'startup_launcher.py')
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        print(f"Created startup launcher: {launcher_path}")
        return launcher_path
        
    except Exception as e:
        print(f"Error creating startup launcher: {e}")
        return None