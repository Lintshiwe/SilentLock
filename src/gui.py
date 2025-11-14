"""
GUI interface for SilentLock password manager.
Provides user interface for managing credentials and settings.
"""

import sys
import os
import time
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import threading
from typing import Dict, List, Optional
from datetime import datetime
from .database import DatabaseManager
from .form_detector import LoginFormDetector, FormDataExtractor
from .enhanced_login_detector import EnhancedLoginFormDetector
from .realtime_activity_widget import RealTimeActivityWidget, CredentialUsageIndicator
from .floating_eye import FloatingEyeWidget, EyeSettings
from .startup_manager import AutoStartService
from .browser_importer import BrowserPasswordImporter
from .admin_gui import AdminPasswordReviewGUI
import webbrowser
import pyperclip
from PIL import Image, ImageDraw, ImageTk
import io
import base64


class SilentLockGUI:
    """Main GUI application for SilentLock password manager."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SilentLock Password Manager")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Set application icon - Enhanced for maximum Windows taskbar visibility
        self._set_application_icon()
        
        # Additional Windows-specific taskbar integration
        try:
            import tkinter.dnd
            # Enable Windows taskbar integration features
            if hasattr(self.root, 'wm_attributes'):
                # Ensure the window appears in taskbar
                self.root.wm_attributes('-toolwindow', False)
        except:
            pass
        
        # Hide main window initially until authentication
        self.root.withdraw()
        
        # Initialize components
        self.db_manager = DatabaseManager()
        self.form_detector = None
        self.enhanced_detector = None  # Enhanced login detector
        self.realtime_tracker = None   # Real-time activity tracker
        self.activity_widget = None    # Activity display widget
        self.usage_indicator = None    # Usage indicator helper
        self.floating_eye = None       # Floating eye monitor
        self.eye_settings = EyeSettings()  # Eye settings
        self.auto_start_service = AutoStartService()
        self.browser_importer = BrowserPasswordImporter()
        self.admin_gui = None  # Initialize admin_gui as None
        self.security_manager = None
        self.audit_logger = None
        self.master_password = None
        self.is_monitoring = False
        self.authenticated = False
        
        # Security components (injected from main app)
        self.security_manager = None
        self.audit_logger = None
        self.admin_gui = None
        
        # Setup GUI (but keep hidden)
        self._setup_styles()
        self._create_github_icon()
        self._create_widgets()
        self._setup_bindings()
        
        # Show login window first
        self._show_login_window()
    
    def _set_application_icon(self):
        """Set application icon with maximum Windows compatibility."""
        try:
            # Get paths to icon files
            base_path = os.path.dirname(os.path.dirname(__file__))
            ico_path = os.path.join(base_path, 'assets', 'logo.ico')
            png_path = os.path.join(base_path, 'assets', 'logo.png')
            
            # Method 1: ICO file (best for Windows taskbar)
            if os.path.exists(ico_path):
                self.root.iconbitmap(ico_path)
                print(f"✅ Application icon set from ICO: {ico_path}")
                
                # Windows-specific taskbar integration
                try:
                    # Force Windows to recognize the icon in taskbar
                    self.root.wm_iconbitmap(ico_path)
                    
                    # Set window class name for proper Windows integration (if supported)
                    try:
                        self.root.wm_class("SilentLock", "SilentLock Password Manager")
                    except AttributeError:
                        # wm_class not available on all tkinter versions
                        pass
                    
                    # Additional Windows taskbar attributes
                    if os.name == 'nt':  # Windows only
                        try:
                            import ctypes
                            from ctypes import wintypes
                            
                            # Get window handle
                            hwnd = int(self.root.wm_frame(), 16)
                            
                            # Set window icon in taskbar (multiple methods for redundancy)
                            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SilentLock.PasswordManager.1.0")
                            
                        except Exception as win_error:
                            print(f"⚠️ Windows-specific taskbar integration failed: {win_error}")
                
                except Exception as taskbar_error:
                    print(f"⚠️ Taskbar integration warning: {taskbar_error}")
                
                # Also set with iconphoto for redundancy
                try:
                    if os.path.exists(png_path):
                        icon_image = Image.open(png_path)
                        # Create multiple sizes for comprehensive Windows support
                        sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)]
                        icon_photos = []
                        
                        for size in sizes:
                            resized = icon_image.resize(size, Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(resized)
                            icon_photos.append(photo)
                            # Keep reference to prevent garbage collection
                            setattr(self.root, f'_icon_photo_{size[0]}x{size[1]}', photo)
                        
                        # Set all sizes for maximum compatibility
                        self.root.iconphoto(True, *icon_photos)
                        print(f"✅ Additional icon sizes set from PNG: {png_path}")
                except Exception as png_error:
                    print(f"⚠️ PNG icon fallback failed: {png_error}")
                    
            elif os.path.exists(png_path):
                # Method 2: PNG file only
                icon_image = Image.open(png_path)
                
                # Create multiple sizes for Windows compatibility
                icon_32 = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                icon_photo_32 = ImageTk.PhotoImage(icon_32)
                
                icon_16 = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                icon_photo_16 = ImageTk.PhotoImage(icon_16)
                
                # Set both sizes
                self.root.iconphoto(True, icon_photo_32, icon_photo_16)
                
                # Keep references to prevent garbage collection
                self.root._icon_photo_32 = icon_photo_32
                self.root._icon_photo_16 = icon_photo_16
                
                print(f"✅ Application icon set from PNG: {png_path}")
            else:
                print("⚠️ No logo files found in assets folder")
                
        except Exception as e:
            print(f"❌ Could not load application icon: {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_styles(self):
        """Setup ttk styles for better appearance."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Warning.TLabel', foreground='orange')
        
        # Default button style with proper corners
        style.configure('TButton', 
                       relief='solid',
                       borderwidth=1,
                       padding=(8, 4))
        style.map('TButton',
                 relief=[('pressed', 'sunken'), ('!pressed', 'solid')])
        
        # Admin button style
        style.configure('Admin.TButton', 
                       background='#dc3545', 
                       foreground='white', 
                       font=('Arial', 9, 'bold'),
                       relief='solid',
                       borderwidth=1)
        style.map('Admin.TButton',
                 background=[('active', '#c82333')],
                 relief=[('pressed', 'sunken'), ('!pressed', 'solid')])
        
        # GitHub button style
        style.configure('Github.TButton', 
                       background='#24292e', 
                       foreground='white', 
                       font=('Arial', 9, 'bold'),
                       padding=(10, 5),
                       relief='solid',
                       borderwidth=1)
        style.map('Github.TButton',
                 background=[('active', '#586069'), ('pressed', '#1d2125')],
                 relief=[('pressed', 'sunken'), ('!pressed', 'solid')])
    
    def _create_github_icon(self):
        """Create a real GitHub icon for the button."""
        try:
            # Create GitHub-style icon using PIL
            size = 16
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # GitHub Logo - simplified Octocat design
            # Main circle (head)
            draw.ellipse([3, 2, 13, 12], fill='white', outline='#24292e', width=1)
            
            # Cat ears
            draw.polygon([(5, 2), (6, 0), (7, 2)], fill='#24292e')
            draw.polygon([(9, 2), (10, 0), (11, 2)], fill='#24292e')
            
            # Eyes
            draw.ellipse([5, 5, 6, 6], fill='#24292e')
            draw.ellipse([10, 5, 11, 6], fill='#24292e')
            
            # Nose
            draw.rectangle([7, 7, 8, 8], fill='#24292e')
            
            # Body/tentacles
            draw.rectangle([7, 10, 9, 16], fill='#24292e')
            draw.rectangle([2, 12, 5, 14], fill='#24292e')
            draw.rectangle([11, 12, 14, 14], fill='#24292e')
            draw.rectangle([4, 14, 6, 16], fill='#24292e')
            draw.rectangle([10, 14, 12, 16], fill='#24292e')
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(img)
            self.github_icon = photo  # Keep reference
            
        except Exception:
            # Fallback: Use Unicode character
            self.github_icon = None
    
    def set_security_components(self, security_manager=None, audit_logger=None):
        """Set security components injected from main app."""
        self.security_manager = security_manager
        self.audit_logger = audit_logger
        
        # Initialize admin GUI with security components
        if self.audit_logger:
            self.admin_gui = AdminPasswordReviewGUI(self.db_manager, parent=self.root)
    
    def _create_header(self):
        """Create header with logo and application title."""
        try:
            # Header frame
            header_frame = ttk.Frame(self.root)
            header_frame.pack(fill='x', padx=10, pady=(10, 5))
            
            # Try to load and display logo
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
            if os.path.exists(logo_path):
                # Load logo
                logo_image = Image.open(logo_path)
                # Resize for header display (64x64 for nice visibility)
                logo_resized = logo_image.resize((64, 64), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_resized)
                
                # Logo label
                logo_label = ttk.Label(header_frame, image=self.logo_photo)
                logo_label.pack(side='left', padx=(0, 15))
                
                print("✅ Logo displayed in application header")
            
            # Title and version info frame
            title_frame = ttk.Frame(header_frame)
            title_frame.pack(side='left', fill='both', expand=True)
            
            # Application title
            title_label = ttk.Label(
                title_frame, 
                text="SilentLock Password Manager", 
                font=('Arial', 16, 'bold'),
                foreground='#2c3e50'
            )
            title_label.pack(anchor='w')
            
            # Subtitle
            subtitle_label = ttk.Label(
                title_frame, 
                text="Secure, Ethical Password Management v1.0", 
                font=('Arial', 10),
                foreground='#7f8c8d'
            )
            subtitle_label.pack(anchor='w')
            
            # Separator line
            separator = ttk.Separator(self.root, orient='horizontal')
            separator.pack(fill='x', padx=10, pady=(5, 10))
            
        except Exception as e:
            print(f"❌ Error creating header: {e}")
            # If header creation fails, just add a simple title
            title_label = ttk.Label(
                self.root, 
                text="SilentLock Password Manager v1.0", 
                font=('Arial', 14, 'bold')
            )
            title_label.pack(pady=10)
    
    def _create_widgets(self):
        """Create the main GUI widgets."""
        # Create header with logo
        self._create_header()
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create tabs
        self._create_credentials_tab()
        self._create_monitor_tab()
        self._create_settings_tab()
        
        # Status bar
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(fill='x', side='bottom')
        
        self.status_label = ttk.Label(self.status_bar, text="Ready")
        self.status_label.pack(side='left', padx=10)
        
        # GitHub link button (center)
        github_frame = ttk.Frame(self.status_bar)
        github_frame.pack(side='left', padx=20, expand=True)
        
        # Create a static GitHub button with real icon
        if hasattr(self, 'github_icon') and self.github_icon:
            # Use icon if available
            self.github_btn = ttk.Button(github_frame, 
                                        text=" GitHub", 
                                        image=self.github_icon,
                                        compound='left',
                                        command=self._open_github, 
                                        style='Github.TButton')
        else:
            # Fallback to Unicode icon - static display
            self.github_btn = ttk.Button(github_frame, text="⚫ GitHub", 
                                        command=self._open_github, 
                                        style='Github.TButton')
        
        self.github_btn.pack(side='left')
        
        # No hover effects - keep button text static
        
        self.monitor_status = ttk.Label(self.status_bar, text="Monitoring: OFF", foreground='red')
        self.monitor_status.pack(side='right', padx=10)
    
    def _create_credentials_tab(self):
        """Create the credentials management tab."""
        credentials_frame = ttk.Frame(self.notebook)
        self.notebook.add(credentials_frame, text="Credentials")
        
        # Toolbar
        toolbar = ttk.Frame(credentials_frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="Add Credential", command=self._add_credential).pack(side='left', padx=5)
        ttk.Button(toolbar, text="Edit", command=self._edit_credential).pack(side='left', padx=5)
        ttk.Button(toolbar, text="Delete", command=self._delete_credential).pack(side='left', padx=5)
        ttk.Button(toolbar, text="Import from Browser", command=self._import_browser_passwords).pack(side='left', padx=5)
        ttk.Button(toolbar, text="Refresh", command=self._refresh_credentials).pack(side='left', padx=5)
        
        # Admin access button (right side)
        ttk.Button(
            toolbar, text="🛡️ Admin", command=self._show_admin_access,
            style='Admin.TButton'
        ).pack(side='right', padx=5)
        
        # Search
        search_frame = ttk.Frame(credentials_frame)
        search_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self._on_search_changed)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side='left', padx=5)
        
        # Credentials list
        list_frame = ttk.Frame(credentials_frame)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Treeview for credentials with enhanced real-time usage display
        columns = ('Site Name', 'URL', 'Username', 'Last Used', 'Real-Time Activity')
        self.credentials_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Configure columns with appropriate widths
        column_widths = {
            'Site Name': 180,
            'URL': 200,
            'Username': 150,
            'Last Used': 120,
            'Real-Time Activity': 200
        }
        
        for col in columns:
            self.credentials_tree.heading(col, text=col)
            self.credentials_tree.column(col, width=column_widths.get(col, 150), minwidth=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.credentials_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient='horizontal', command=self.credentials_tree.xview)
        self.credentials_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.credentials_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Context menu
        self.credentials_tree.bind('<Button-3>', self._show_context_menu)
        self.credentials_tree.bind('<Double-1>', self._copy_password)
    
    def _create_monitor_tab(self):
        """Create the monitoring tab."""
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text="Monitor")
        
        # Monitor controls
        controls_frame = ttk.Frame(monitor_frame)
        controls_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(controls_frame, text="Form Detection Monitor", style='Title.TLabel').pack(anchor='w')
        
        button_frame = ttk.Frame(controls_frame)
        button_frame.pack(fill='x', pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Monitoring", command=self._start_monitoring)
        self.start_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Monitoring", command=self._stop_monitoring, state='disabled')
        self.stop_button.pack(side='left', padx=5)
        
        # Monitor status
        status_frame = ttk.LabelFrame(monitor_frame, text="Status")
        status_frame.pack(fill='x', padx=10, pady=10)
        
        self.monitor_status_label = ttk.Label(status_frame, text="Monitoring is stopped", style='Error.TLabel')
        self.monitor_status_label.pack(anchor='w', padx=10, pady=5)
        
        self.detection_count_label = ttk.Label(status_frame, text="Forms detected: 0")
        self.detection_count_label.pack(anchor='w', padx=10, pady=5)
        
        # Activity log
        log_frame = ttk.LabelFrame(monitor_frame, text="Activity Log")
        log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.activity_log = ScrolledText(log_frame, height=15, wrap='word')
        self.activity_log.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Detection counter
        self.detection_count = 0
    
    def _create_settings_tab(self):
        """Create the settings tab."""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Security settings
        security_frame = ttk.LabelFrame(settings_frame, text="Security")
        security_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(security_frame, text="Change Master Password", command=self._change_master_password).pack(anchor='w', padx=10, pady=5)
        ttk.Button(security_frame, text="Export Credentials", command=self._export_credentials).pack(anchor='w', padx=10, pady=5)
        ttk.Button(security_frame, text="Import Credentials", command=self._import_credentials).pack(anchor='w', padx=10, pady=5)
        ttk.Button(security_frame, text="Reset Auto-Import", command=self._reset_auto_import).pack(anchor='w', padx=10, pady=5)
        
        # Monitor settings
        monitor_settings_frame = ttk.LabelFrame(settings_frame, text="Monitor Settings")
        monitor_settings_frame.pack(fill='x', padx=10, pady=10)
        
        self.auto_start_var = tk.BooleanVar()
        ttk.Checkbutton(monitor_settings_frame, text="Start monitoring on launch", variable=self.auto_start_var).pack(anchor='w', padx=10, pady=5)
        
        self.notification_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(monitor_settings_frame, text="Show save notifications", variable=self.notification_var).pack(anchor='w', padx=10, pady=5)
        
        self.monitor_all_apps_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(monitor_settings_frame, text="Monitor ALL applications (comprehensive)", variable=self.monitor_all_apps_var, command=self._toggle_monitor_all_apps).pack(anchor='w', padx=10, pady=5)
        
        self.auto_import_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(monitor_settings_frame, text="Auto-import browser passwords on startup", variable=self.auto_import_var).pack(anchor='w', padx=10, pady=5)
        
        # Floating Eye toggle with enhanced description
        self.floating_eye_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(monitor_settings_frame, text="👁️ Enable realistic floating eye monitor (enhanced tracking)", variable=self.floating_eye_var, command=self._toggle_floating_eye).pack(anchor='w', padx=10, pady=5)
        
        # Windows startup settings
        startup_settings_frame = ttk.LabelFrame(settings_frame, text="Windows Startup")
        startup_settings_frame.pack(fill='x', padx=10, pady=10)
        
        self.windows_startup_var = tk.BooleanVar()
        startup_cb = ttk.Checkbutton(startup_settings_frame, 
                                   text="Start SilentLock automatically when Windows starts", 
                                   variable=self.windows_startup_var,
                                   command=self._toggle_windows_startup)
        startup_cb.pack(anchor='w', padx=10, pady=5)
        
        # Load current startup status
        try:
            status = self.auto_start_service.check_startup_status()
            self.windows_startup_var.set(status.get('registry_enabled', False))
        except Exception as e:
            print(f"Error checking startup status: {e}")
        
        startup_info = tk.Label(startup_settings_frame, 
                              text="When enabled, SilentLock will run in background and monitor for login forms automatically.",
                              wraplength=600, justify='left', fg='gray')
        startup_info.pack(anchor='w', padx=10, pady=(0, 10))
        
        # About
        about_frame = ttk.LabelFrame(settings_frame, text="About")
        about_frame.pack(fill='x', padx=10, pady=10)
        
        about_text = "SilentLock Password Manager v1.0\n\nA secure, ethical password manager for personal use.\nAll data is stored locally with strong encryption."
        ttk.Label(about_frame, text=about_text, justify='left').pack(anchor='w', padx=10, pady=10)
    
    def _add_realtime_activity_tab(self):
        """Add real-time activity tracking tab."""
        try:
            # Check if already added
            if hasattr(self, 'activity_tab_added') and self.activity_tab_added:
                return
            
            if not self.realtime_tracker:
                return
                
            # Create activity frame and add to notebook
            activity_frame = ttk.Frame(self.notebook)
            self.notebook.add(activity_frame, text="🔄 Real-Time Activity")
            
            # Create activity widget
            self.activity_widget = RealTimeActivityWidget(activity_frame, self.realtime_tracker)
            
            # Mark as added
            self.activity_tab_added = True
            
            print("✅ Real-time activity tab added successfully")
            
        except Exception as e:
            print(f"Error adding real-time activity tab: {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_bindings(self):
        """Setup keyboard bindings and events."""
        self.root.bind('<Control-n>', lambda e: self._add_credential())
        self.root.bind('<Delete>', lambda e: self._delete_credential())
        self.root.bind('<F5>', lambda e: self._refresh_credentials())
    
    def _show_login_window(self):
        """Show the login window first, before main application."""
        self.login_window = tk.Toplevel()
        self.login_window.title("SilentLock - Authentication")
        self.login_window.geometry("450x320")  # Reduced height to fit content better
        self.login_window.resizable(False, False)
        
        # Set icon for login window too
        try:
            ico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.ico')
            if os.path.exists(ico_path):
                self.login_window.iconbitmap(ico_path)
        except Exception as e:
            print(f"⚠️ Could not set login window icon: {e}")
        
        # Make login window modal and always on top
        self.login_window.transient()
        self.login_window.grab_set()
        self.login_window.protocol("WM_DELETE_WINDOW", self._on_login_cancel)
        
        # Center the login window
        self.login_window.geometry("+%d+%d" % (
            (self.login_window.winfo_screenwidth() // 2) - 225,
            (self.login_window.winfo_screenheight() // 2) - 160  # Adjusted for reduced height
        ))
        
        # Create login interface
        self._create_login_interface()
        
        # Debug: Force window update
        self.login_window.update_idletasks()
        self.login_window.update()
        
        # Check if master password exists
        if not self.db_manager.has_master_password():
            print("📝 Setting up new master password interface")
            self._setup_new_master_password()
        else:
            print("🔓 Setting up existing master password interface")
            self._prompt_existing_master_password()
            
        # Force another update to ensure content is visible
        self.login_window.update_idletasks()
    
    def _create_login_interface(self):
        """Create the login interface components."""
        main_frame = tk.Frame(self.login_window, bg='#f0f0f0', padx=25, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # SilentLock Logo/Title
        title_frame = tk.Frame(main_frame, bg='#f0f0f0')
        title_frame.pack(pady=(0, 15))
        
        # Load and display actual logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'logo.png')
            if os.path.exists(logo_path):
                # Load logo
                logo_image = Image.open(logo_path)
                # Resize for login display (70x70 for more compact display)
                logo_resized = logo_image.resize((70, 70), Image.Resampling.LANCZOS)
                self.login_logo_photo = ImageTk.PhotoImage(logo_resized)
                
                # Logo label
                logo_label = tk.Label(title_frame, image=self.login_logo_photo, bg='#f0f0f0')
                logo_label.pack()
                print("✅ Logo displayed in login window")
            else:
                # Fallback to icon if logo not found
                icon_label = tk.Label(title_frame, text="🔐", font=('Arial', 32), bg='#f0f0f0')
                icon_label.pack()
                print("⚠️ Logo file not found, using icon fallback")
        except Exception as e:
            # Fallback to icon if logo loading fails
            icon_label = tk.Label(title_frame, text="🔐", font=('Arial', 32), bg='#f0f0f0')
            icon_label.pack()
            print(f"⚠️ Could not load logo for login window: {e}")
        
        title_label = tk.Label(title_frame, text="SilentLock Password Manager", 
                             font=('Arial', 16, 'bold'), bg='#f0f0f0', fg='#2E8B57')
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame, text="Secure • Ethical • Personal", 
                                font=('Arial', 10), bg='#f0f0f0', fg='#666666')
        subtitle_label.pack()
        
        # Content frame for dynamic content
        self.login_content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        self.login_content_frame.pack(fill='both', expand=True)
    
    def _setup_new_master_password(self):
        """Setup interface for creating new master password."""
        # Clear content frame
        for widget in self.login_content_frame.winfo_children():
            widget.destroy()
        
        # Welcome message
        welcome_label = tk.Label(self.login_content_frame, 
                               text="Welcome to SilentLock!\nPlease create a master password to secure your credentials.",
                               font=('Arial', 11), bg='#f0f0f0', fg='#333333', justify='center')
        welcome_label.pack(pady=(0, 20))
        
        # Password fields
        tk.Label(self.login_content_frame, text="Master Password:", 
               font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.new_password_var = tk.StringVar()
        self.new_password_entry = tk.Entry(self.login_content_frame, textvariable=self.new_password_var, 
                                         show='*', width=30, font=('Arial', 10))
        self.new_password_entry.pack(pady=(2, 10), fill='x')
        self.new_password_entry.focus()
        
        tk.Label(self.login_content_frame, text="Confirm Password:", 
               font=('Arial', 10, 'bold'), bg='#f0f0f0').pack(anchor='w')
        
        self.confirm_password_var = tk.StringVar()
        self.confirm_password_entry = tk.Entry(self.login_content_frame, textvariable=self.confirm_password_var, 
                                             show='*', width=30, font=('Arial', 10))
        self.confirm_password_entry.pack(pady=(2, 20), fill='x')
        
        # Instructions for user
        instruction_label = tk.Label(self.login_content_frame, 
                                   text="Press Enter to create master password", 
                                   font=('Arial', 9), bg='#f0f0f0', fg='#666666')
        instruction_label.pack(pady=(5, 0))
        
        # Bind Enter key for password creation
        self.login_window.bind('<Return>', lambda e: self._create_master_password())
        
        # Bind Escape key to exit (alternative to Exit button)
        self.login_window.bind('<Escape>', lambda e: self._on_login_cancel())
    
    def _prompt_existing_master_password(self):
        """Show interface for entering existing master password."""
        print("🔓 Creating existing master password interface...")
        
        # Clear content frame
        for widget in self.login_content_frame.winfo_children():
            widget.destroy()
        
        # Login message
        login_label = tk.Label(self.login_content_frame, 
                             text="Please enter your master password to continue.",
                             font=('Arial', 11), bg='#f0f0f0', fg='#333333')
        login_label.pack(pady=(0, 15))
        print("📝 Login message created")
        
        # Password field
        password_label = tk.Label(self.login_content_frame, text="Master Password:", 
               font=('Arial', 10, 'bold'), bg='#f0f0f0')
        password_label.pack(anchor='w')
        print("🏷️ Password label created")
        
        self.login_password_var = tk.StringVar()
        self.login_password_entry = tk.Entry(self.login_content_frame, textvariable=self.login_password_var, 
                                           show='*', width=30, font=('Arial', 10))
        self.login_password_entry.pack(pady=(2, 10), fill='x')
        self.login_password_entry.focus()
        print("🔑 Password entry field created and focused")
        
        # Error label (hidden initially)
        self.error_label = tk.Label(self.login_content_frame, text="", 
                                  font=('Arial', 9), bg='#f0f0f0', fg='red')
        self.error_label.pack()
        
        # Instructions for user
        instruction_label = tk.Label(self.login_content_frame, 
                                   text="Press Enter to unlock", 
                                   font=('Arial', 9), bg='#f0f0f0', fg='#666666')
        instruction_label.pack(pady=(5, 0))
        
        # Bind Enter key for login
        self.login_window.bind('<Return>', lambda e: self._verify_master_password())
        
        # Bind Escape key to exit (alternative to Exit button)
        self.login_window.bind('<Escape>', lambda e: self._on_login_cancel())
        
        # Force update
        self.login_content_frame.update_idletasks()
        self.login_window.update_idletasks()
        print("✅ Master password interface setup complete (Enter key enabled)")
    
    def _create_master_password(self):
        """Create new master password and unlock application."""
        password = self.new_password_var.get()
        confirm = self.confirm_password_var.get()
        
        if not password:
            messagebox.showerror("Error", "Password cannot be empty!")
            return
        
        if len(password) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters long!")
            return
        
        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match!")
            return
        
        if self.db_manager.set_master_password(password):
            self.master_password = password
            self.authenticated = True
            self._show_main_window()
        else:
            messagebox.showerror("Error", "Failed to create master password!")
    
    def _verify_master_password(self):
        """Verify existing master password and unlock application."""
        password = self.login_password_var.get()
        
        if not password:
            self.error_label.config(text="Please enter your password")
            return
        
        if self.db_manager.verify_master_password(password):
            self.master_password = password
            self.authenticated = True
            self._show_main_window()
        else:
            self.error_label.config(text="Incorrect password. Please try again.")
            self.login_password_var.set("")  # Clear password field
            self.login_password_entry.focus()
    
    def _show_main_window(self):
        """Show the main application window after successful authentication."""
        try:
            # Close login window
            self.login_window.destroy()
            
            # Show main window
            self.root.deiconify()
            self.root.focus_force()
            self.root.lift()
            
            # Load credentials now that we're authenticated
            self._refresh_credentials()
            
            # Auto-import browser passwords if enabled
            if self.auto_import_var.get():
                self.root.after(2000, self._auto_import_browser_passwords)  # Delay 2 seconds
            
            # Show welcome notification
            self._show_notification("Welcome to SilentLock!", 
                                  "Password manager unlocked and ready to use")
            
            print("SilentLock main window opened successfully")
            
        except Exception as e:
            print(f"Error showing main window: {e}")
            messagebox.showerror("Error", f"Failed to open main window: {e}")
    
    def _on_login_cancel(self):
        """Handle login window cancel/close."""
        if messagebox.askyesno("Exit SilentLock", "Are you sure you want to exit?"):
            self.root.quit()
            sys.exit(0)
    
    def _check_master_password(self):
        """Legacy method - now handled by login window."""
        pass
    
    def _refresh_credentials(self):
        """Refresh the credentials list with real-time activity indicators."""
        if not self.master_password:
            return
        
        # Clear existing items
        for item in self.credentials_tree.get_children():
            self.credentials_tree.delete(item)
        
        # Load credentials
        credentials = self.db_manager.get_all_credentials(self.master_password)
        
        for cred in credentials:
            last_used = cred.get('last_used', 'Never')
            if last_used and last_used != 'Never':
                # Format the timestamp if it's available
                last_used = last_used if isinstance(last_used, str) else 'Recently'
            
            # Get real-time activity indicator if available
            activity_indicator = "🔹 No activity"
            if self.usage_indicator and hasattr(self.usage_indicator, 'get_usage_indicator'):
                try:
                    credential_id = cred.get('id')
                    if credential_id is not None:
                        activity_indicator = self.usage_indicator.get_usage_indicator(credential_id)
                    else:
                        # Fallback: try to get ID from site name and username
                        site_name = cred.get('site_name', '')
                        username = cred.get('username', '')
                        activity_indicator = f"🔸 Active for {site_name}" if site_name else "🔹 No activity"
                except Exception as e:
                    print(f"Warning: Could not get usage indicator for credential: {e}")
                    activity_indicator = "🔹 No activity"
            
            self.credentials_tree.insert('', 'end', values=(
                cred.get('site_name', 'Unknown'),
                cred.get('site_url', ''),
                cred.get('username', ''),
                last_used,
                activity_indicator
            ))
        
        self._update_status(f"Loaded {len(credentials)} credentials with real-time tracking")
    
    def _on_search_changed(self, *args):
        """Handle search input changes with real-time activity."""
        if not self.master_password:
            return
        
        query = self.search_var.get().strip()
        
        # Clear existing items
        for item in self.credentials_tree.get_children():
            self.credentials_tree.delete(item)
        
        if query:
            credentials = self.db_manager.search_credentials(query, self.master_password)
        else:
            credentials = self.db_manager.get_all_credentials(self.master_password)
        
        for cred in credentials:
            last_used = cred.get('last_used', 'Never')
            if last_used and last_used != 'Never':
                last_used = last_used if isinstance(last_used, str) else 'Recently'
            
            # Get real-time activity indicator with better error handling
            activity_indicator = "🔹 No activity"
            if self.usage_indicator and hasattr(self.usage_indicator, 'get_usage_indicator'):
                try:
                    credential_id = cred.get('id')
                    if credential_id is not None:
                        activity_indicator = self.usage_indicator.get_usage_indicator(credential_id)
                    else:
                        site_name = cred.get('site_name', '')
                        activity_indicator = f"🔸 Active for {site_name}" if site_name else "🔹 No activity"
                except Exception as e:
                    print(f"Warning: Could not get usage indicator for credential: {e}")
                    activity_indicator = "🔹 No activity"
            
            self.credentials_tree.insert('', 'end', values=(
                cred.get('site_name', 'Unknown'),
                cred.get('site_url', ''),
                cred.get('username', ''),
                last_used,
                activity_indicator
            ))
    
    def _add_credential(self):
        """Add a new credential manually with duplicate detection."""
        if not self.master_password:
            messagebox.showerror("Error", "Master password not set!")
            return
        
        dialog = CredentialDialog(self.root, title="Add Credential")
        if dialog.result:
            cred = dialog.result
            
            # Check for duplicates
            duplicates = self.db_manager.check_duplicate_credentials(
                cred['site_name'],
                cred['site_url'], 
                cred['username'],
                self.master_password
            )
            
            if duplicates['has_duplicates']:
                # Show duplicate detection dialog
                dup_dialog = DuplicateDetectionDialog(self.root, duplicates, cred)
                dup_dialog.dialog.wait_window()
                
                if dup_dialog.result == "cancel":
                    return
                elif dup_dialog.result == "update":
                    # Update existing credential
                    force_update = True
                elif dup_dialog.result == "keep_both":
                    # For exact matches, we need to modify the URL to make it unique
                    if duplicates.get('exact_match'):
                        # Add timestamp to make URL unique
                        import time
                        timestamp = str(int(time.time()))
                        cred['site_url'] = f"{cred['site_url']}#{timestamp}"
                        cred['site_name'] = f"{cred['site_name']} (Copy)"
                    force_update = False
                else:
                    return
            else:
                force_update = False
            
            # Store the credential
            if self.db_manager.store_credential(
                cred['site_name'],
                cred['site_url'],
                cred['username'],
                cred['password'],
                self.master_password,
                cred.get('notes', ''),
                force_update
            ):
                action = "updated" if duplicates['has_duplicates'] and dup_dialog.result == "update" else "saved"
                messagebox.showinfo("Success", f"Credential {action} successfully!")
                self._refresh_credentials()
            else:
                messagebox.showerror("Error", "Failed to save credential!")
    
    def _edit_credential(self):
        """Edit selected credential."""
        selection = self.credentials_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a credential to edit.")
            return
        
        item = self.credentials_tree.item(selection[0])
        values = item['values']
        
        if not values or len(values) < 5:  # Now we have 5 columns
            return
        
        site_name, site_url, username, _, _ = values  # Extract first 3, ignore last 2 (Last Used, Real-Time Activity)
        
        # Get current credential data
        cred_data = self.db_manager.get_credential(site_url, username, self.master_password)
        if not cred_data:
            messagebox.showerror("Error", "Could not load credential data!")
            return
        
        dialog = CredentialDialog(self.root, title="Edit Credential", initial_data=cred_data)
        if dialog.result:
            cred = dialog.result
            if self.db_manager.store_credential(
                cred['site_name'],
                cred['site_url'],
                cred['username'],
                cred['password'],
                self.master_password,
                cred.get('notes', '')
            ):
                messagebox.showinfo("Success", "Credential updated successfully!")
                self._refresh_credentials()
            else:
                messagebox.showerror("Error", "Failed to update credential!")
    
    def _delete_credential(self):
        """Delete selected credential."""
        selection = self.credentials_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a credential to delete.")
            return
        
        item = self.credentials_tree.item(selection[0])
        values = item['values']
        
        if not values:
            return
        
        site_name, site_url, username, _, _ = values  # Added extra _ for Real-Time Activity column
        
        if messagebox.askyesno("Confirm Delete", f"Delete credential for {username}@{site_name}?"):
            if self.db_manager.delete_credential(site_url, username):
                messagebox.showinfo("Success", "Credential deleted successfully!")
                self._refresh_credentials()
            else:
                messagebox.showerror("Error", "Failed to delete credential!")
    
    def _copy_password(self, event=None):
        """Copy password to clipboard (double-click) with real-time tracking."""
        selection = self.credentials_tree.selection()
        if not selection:
            return
        
        item = self.credentials_tree.item(selection[0])
        values = item['values']
        
        if not values or len(values) < 4:  # Updated for new column count
            return
        
        site_name, site_url, username, _, _ = values  # Added extra _ for Real-Time Activity column
        
        cred_data = self.db_manager.get_credential(site_url, username, self.master_password)
        if cred_data:
            pyperclip.copy(cred_data['password'])
            self._update_status(f"Password copied for {username}@{site_name}")
            
            # Log real-time activity for password access
            if self.realtime_tracker:
                try:
                    credential_id = cred_data.get('id', 0)
                    if credential_id and credential_id > 0:
                        self.realtime_tracker.add_usage(
                            credential_id, 
                            'accessed', 
                            f"Password copied for {site_name}"
                        )
                        print(f"📊 Real-time activity logged: Password accessed for {site_name}")
                        
                        # Refresh to show updated activity indicator
                        self._refresh_credentials()
                    else:
                        print(f"📊 Real-time activity skipped: No valid ID for {site_name}")
                except Exception as e:
                    print(f"Error logging password access activity: {e}")
    
    def _show_context_menu(self, event):
        """Show context menu for credentials."""
        # This could be expanded with more options
        pass
    
    def _show_admin_access(self):
        """Show administrator access interface."""
        try:
            if not self.admin_gui:
                messagebox.showerror("Error", "Admin interface not available")
                return
            
            # Log admin access attempt
            if self.audit_logger:
                self.audit_logger.log_admin_action(
                    admin_user_id="user",  # This would be the current user
                    action_type="access_attempt",
                    action_details={"interface": "password_review"},
                    success=True
                )
            
            # Show admin login
            self.admin_gui.show_admin_login()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open admin interface: {e}")
    
    def _open_github(self):
        """Open GitHub profile link with minimal visual feedback."""
        try:
            import webbrowser
            
            # Brief visual feedback only in status bar
            self._set_status("🌐 Opening GitHub profile...", "info")
            
            # Open GitHub profile
            webbrowser.open("https://github.com/lintshiwe")
            
            # Update status only
            self._set_status("🐙 GitHub profile opened - Follow @lintshiwe for updates!", "success")
            
            # Log the action
            if self.audit_logger:
                self.audit_logger.log_system_event(
                    event_type="external_link_access",
                    details={"link": "github.com/lintshiwe", "action": "follow_developer", "source": "main_interface"}
                )
                
        except Exception as e:
            self._set_status(f"Failed to open GitHub link: {e}", "error")
            if self.audit_logger:
                self.audit_logger.log_admin_action(
                    admin_user_id="user",
                    action_type="access_attempt", 
                    action_details={"interface": "password_review"},
                    success=False
                )
    
    def _start_monitoring(self):
        """Start enhanced form monitoring with success verification and real-time tracking."""
        if self.is_monitoring:
            return
        
        try:
            # Initialize enhanced form detector with success verification
            self.enhanced_detector = EnhancedLoginFormDetector(
                on_login_detected=self._on_login_detected,
                credential_db=self.db_manager,
                master_password=self.master_password
            )
            
            # Get the real-time tracker from enhanced detector
            self.realtime_tracker = self.enhanced_detector.get_realtime_tracker()
            
            # Initialize usage indicator helper
            self.usage_indicator = CredentialUsageIndicator(self.realtime_tracker)
            
            # Apply monitor all apps setting to base detector
            if hasattr(self.enhanced_detector.base_detector, 'monitor_all_apps'):
                self.enhanced_detector.base_detector.monitor_all_apps = self.monitor_all_apps_var.get()
            
            # Start enhanced monitoring
            self.enhanced_detector.start_monitoring()
            
            self.form_detector = self.enhanced_detector  # For compatibility
            self.is_monitoring = True
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            
            self.monitor_status_label.config(text="Enhanced monitoring active (with login verification)", style='Success.TLabel')
            self.monitor_status.config(text="Monitoring: ON (Enhanced)", foreground='green')
            
            self._log_activity("🚀 Enhanced monitoring started with login success verification")
            self._update_status("Enhanced form monitoring with success verification started")
            
            # Add real-time activity tracking to the monitor tab if not already added
            self._add_realtime_activity_tab()
            
            # Start floating eye if enabled
            self._start_floating_eye()
            
        except Exception as e:
            print(f"Error starting enhanced monitoring: {e}")
            messagebox.showerror("Error", f"Failed to start enhanced monitoring: {e}")
            # Fallback to basic monitoring
            self._start_basic_monitoring()
    
    def _start_basic_monitoring(self):
        """Fallback to basic monitoring if enhanced monitoring fails."""
        try:
            # Initialize basic form detector
            self.form_detector = LoginFormDetector(
                on_login_detected=self._on_login_detected,
                credential_db=self.db_manager,
                master_password=self.master_password
            )
            
            # Apply monitor all apps setting
            self.form_detector.monitor_all_apps = self.monitor_all_apps_var.get()
            
            self.form_detector.start_monitoring()
            
            self.is_monitoring = True
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            
            self.monitor_status_label.config(text="Basic monitoring active", style='Warning.TLabel')
            self.monitor_status.config(text="Monitoring: ON (Basic)", foreground='orange')
            
            self._log_activity("⚠️ Basic monitoring started (enhanced features unavailable)")
            self._update_status("Basic form monitoring started")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start basic monitoring: {e}")
    
    def _stop_monitoring(self):
        """Stop form monitoring."""
        if not self.is_monitoring:
            return
        
        # Stop enhanced detector if present
        if self.enhanced_detector:
            self.enhanced_detector.stop_monitoring()
            self.enhanced_detector = None
            
        # Stop basic detector if present  
        if self.form_detector:
            self.form_detector.stop_monitoring()
            self.form_detector = None
        
        # Stop activity widget updates
        if self.activity_widget:
            self.activity_widget.stop_updates()
        
        # Stop floating eye
        self._stop_floating_eye()
        
        self.is_monitoring = False
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        
        self.monitor_status_label.config(text="Monitoring is stopped", style='Error.TLabel')
        self.monitor_status.config(text="Monitoring: OFF", foreground='red')
        
        self._log_activity("⏹️ Monitoring stopped")
        self._update_status("Form monitoring stopped")
    
    def _toggle_monitor_all_apps(self):
        """Toggle monitoring of all applications."""
        monitor_all = self.monitor_all_apps_var.get()
        
        if self.form_detector:
            self.form_detector.monitor_all_apps = monitor_all
            
        status = "ALL applications" if monitor_all else "selected applications only"
        self._log_activity(f"Monitoring scope changed to: {status}")
        
        if monitor_all:
            self._update_status("Now monitoring ALL applications for login forms")
        else:
            self._update_status("Now monitoring selected applications only")
    
    def _on_login_detected(self, credential_data):
        """Handle detected login form submission with enhanced data validation and loop prevention."""
        try:
            # CRITICAL: Prevent infinite save dialogs
            current_time = time.time()
            credential_key = f"{credential_data.get('username', '')}@{credential_data.get('site_name', '')}"
            
            if hasattr(self, '_last_save_prompt_time'):
                if current_time - self._last_save_prompt_time < 10:  # 10 second cooldown
                    if hasattr(self, '_last_credential_key') and self._last_credential_key == credential_key:
                        print(f"🚫 Prevented duplicate save prompt for {credential_key} (cooldown)")
                        return
            
            self._last_save_prompt_time = current_time
            self._last_credential_key = credential_key
            
            self.detection_count += 1
            self.detection_count_label.config(text=f"Forms detected: {self.detection_count}")
            
            # Clean and validate credential data
            raw_site_name = credential_data.get('site_name', 'Unknown')
            raw_username = credential_data.get('username', '')
            
            print(f"🔍 RAW CREDENTIAL DATA: Site='{raw_site_name}', User='{raw_username}'")
            
            # Enhanced data cleaning for corrupted entries
            if len(raw_site_name) > 200 or '\n' in raw_site_name:
                print(f"🧹 Cleaning corrupted site name: '{raw_site_name[:50]}...'")
                # Site name looks corrupted, try to extract from URL or use simple name
                site_url = credential_data.get('site_url', '')
                if site_url:
                    try:
                        # Extract domain from URL
                        import urllib.parse
                        parsed = urllib.parse.urlparse(site_url if site_url.startswith('http') else f'http://{site_url}')
                        raw_site_name = parsed.netloc or 'Unknown Site'
                    except:
                        raw_site_name = 'Unknown Site'
                else:
                    # Use window title if available but clean it
                    window_title = credential_data.get('window_title', '')
                    if window_title and len(window_title) < 100:
                        raw_site_name = window_title.split(' - ')[0]  # Take first part
                    else:
                        raw_site_name = 'Unknown Site'
            
            # Clean username - should not be longer than reasonable length
            if len(raw_username) > 100 or '\n' in raw_username:
                print(f"🧹 Cleaning corrupted username: '{raw_username[:50]}...'")
                raw_username = 'User'  # Fallback for corrupted username
            
            site_name = FormDataExtractor.clean_site_name(raw_site_name)
            username = raw_username.strip()
            
            print(f"✅ CLEAN CREDENTIAL DATA: Site='{site_name}', User='{username}'")
            
            # Validate that we have reasonable data
            if not site_name or site_name == 'Unknown':
                site_name = 'Detected Login'
            
            if not username:
                username = 'User'
            
            self._log_activity(f"Login detected: {username}@{site_name}")
            
            # Show save prompt with cleaned data
            if self.notification_var.get():
                cleaned_credential_data = {
                    'site_name': site_name,
                    'site_url': credential_data.get('site_url', ''),
                    'username': username,
                    'password': credential_data.get('password', ''),
                    'window_title': credential_data.get('window_title', ''),
                    'notes': f"Auto-detected on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
                self.root.after(0, self._show_save_prompt, cleaned_credential_data)
                
        except Exception as e:
            self._log_activity(f"Error processing login detection: {e}")
            print(f"Error in login detection: {e}")
            import traceback
            traceback.print_exc()
    
    def _show_save_prompt(self, credential_data):
        """Show prompt to save detected credentials with duplicate detection and loop prevention."""
        try:
            # CRITICAL: Prevent infinite duplicate dialogs
            if hasattr(self, '_save_prompt_open') and self._save_prompt_open:
                print("🚫 Save prompt already open - preventing loop")
                return
                
            self._save_prompt_open = True
            
            site_name = FormDataExtractor.clean_site_name(credential_data.get('site_name', 'Unknown'))
            username = credential_data.get('username', '')
            site_url = credential_data.get('site_url', '')
            
            print(f"💾 SAVING PROMPT: Site='{site_name}', User='{username}', URL='{site_url[:50]}...'")
            
            # Check for duplicates first
            duplicates = self.db_manager.check_duplicate_credentials(
                site_name, site_url, username, self.master_password
            )
            
            # If exact duplicate exists, show different message
            if duplicates.get('exact_match'):
                existing = duplicates['exact_match']
                response = messagebox.askyesnocancel(
                    "Duplicate Credential Found",
                    f"A credential for {username}@{site_name} already exists!\n\n"
                    f"Existing password: {'•' * len(existing.get('password', ''))}\n"
                    f"New password: {'•' * len(credential_data.get('password', ''))}\n\n"
                    f"Would you like to update it?\n"
                    f"Click 'Yes' to update, 'No' to keep existing, 'Cancel' to ignore."
                )
                
                if response is True:  # Yes - Update
                    if self._store_credential_with_action(credential_data, "updated"):
                        self._log_activity(f"Updated credential for {username}@{site_name}")
                elif response is False:  # No - Keep existing
                    self._log_activity(f"Kept existing credential for {username}@{site_name}")
                # Cancel - do nothing
                
                self._save_prompt_open = False
                return
            
            # If other types of duplicates, show info but allow save
            elif duplicates['has_duplicates']:
                dup_count = (len(duplicates.get('same_site_different_user', [])) + 
                            len(duplicates.get('same_user_different_site', [])) + 
                            len(duplicates.get('similar_domains', [])))
                
                response = messagebox.askyesno(
                    "Related Credentials Found", 
                    f"Save login for {username}@{site_name}?\n\n"
                    f"Note: Found {dup_count} related credential(s) for this site/user."
                )
            else:
                # No duplicates, standard prompt
                response = messagebox.askyesno("Save Credential?", 
                                             f"Save login for {username}@{site_name}?")
            
            if response:
                if self._store_credential_with_action(credential_data, "saved"):
                    self._log_activity(f"Saved credential for {username}@{site_name}")
            else:
                self._log_activity(f"Declined to save credential for {username}@{site_name}")
                
            self._save_prompt_open = False
            
        except Exception as e:
            print(f"Error in save prompt: {e}")
            self._save_prompt_open = False
            import traceback
            traceback.print_exc()
    
    def _store_credential_with_action(self, credential_data, action):
        """Store credential and show appropriate notification with real-time tracking."""
        site_name = FormDataExtractor.clean_site_name(credential_data.get('site_name', 'Unknown'))
        username = credential_data.get('username', '')
        
        credential_id = self.db_manager.store_credential(
            site_name,
            credential_data.get('site_url', ''),
            username,
            credential_data.get('password', ''),
            self.master_password
        )
        
        if credential_id > 0:  # Changed from boolean check to ID check
            # Record real-time activity
            if self.realtime_tracker:
                try:
                    self.realtime_tracker.add_usage(
                        credential_id, 
                        action, 
                        f"Credential {action} for {site_name}"
                    )
                    print(f"📊 Real-time activity logged: {action} for {site_name}")
                except Exception as e:
                    print(f"Error logging real-time activity: {e}")
            
            self._show_notification(f"Credential {action.title()}!", 
                                  f"{action.title()} login for {username}@{site_name}")
            self._refresh_credentials()  # This will now show updated real-time indicators
            return True
        else:
            messagebox.showerror("Error", f"Failed to {action} credential!")
            return False
    
    def _show_notification(self, title, message, duration=3000):
        """Show desktop notification for important events."""
        try:
            # Try Windows 10+ toast notifications first
            try:
                from plyer import notification
                notification.notify(
                    title=title,
                    message=message,
                    app_name="SilentLock",
                    timeout=duration // 1000
                )
                return
            except ImportError:
                pass
            
            # Fallback to custom notification window
            notification_window = tk.Toplevel(self.root)
            notification_window.title("SilentLock")
            notification_window.geometry("350x120")
            notification_window.resizable(False, False)
            
            # Position at bottom right of screen
            notification_window.attributes('-topmost', True)
            x = notification_window.winfo_screenwidth() - 370
            y = notification_window.winfo_screenheight() - 180
            notification_window.geometry(f"+{x}+{y}")
            
            # Styling
            notification_window.configure(bg='#2E8B57')  # Sea green background
            
            # Icon and content frame
            content_frame = tk.Frame(notification_window, bg='#2E8B57')
            content_frame.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Title
            title_label = tk.Label(content_frame, text=title, 
                                 font=('Arial', 12, 'bold'),
                                 bg='#2E8B57', fg='white')
            title_label.pack(anchor='w')
            
            # Message
            message_label = tk.Label(content_frame, text=message, 
                                   wraplength=320, justify='left',
                                   bg='#2E8B57', fg='white')
            message_label.pack(anchor='w', pady=(5, 0))
            
            # Close button
            close_button = tk.Button(content_frame, text="✕", 
                                   command=notification_window.destroy,
                                   bg='#228B22', fg='white', 
                                   relief='flat', width=3)
            close_button.place(relx=1.0, rely=0, anchor='ne')
            
            # Auto-close after duration
            notification_window.after(duration, notification_window.destroy)
            
            # Fade in effect (simple)
            notification_window.lift()
            
        except Exception as e:
            print(f"Error showing notification: {e}")
            # Fallback to simple message box
            messagebox.showinfo(title, message)
    
    def _toggle_windows_startup(self):
        """Toggle Windows startup setting."""
        try:
            enabled = self.windows_startup_var.get()
            success = self.auto_start_service.update_startup_setting(enabled)
            
            if success:
                if enabled:
                    self._show_notification("Startup Enabled", 
                                          "SilentLock will now start automatically with Windows")
                    self._log_activity("Windows startup enabled")
                else:
                    self._show_notification("Startup Disabled", 
                                          "SilentLock will no longer start automatically with Windows")
                    self._log_activity("Windows startup disabled")
            else:
                # Revert checkbox if operation failed
                self.windows_startup_var.set(not enabled)
                messagebox.showerror("Error", 
                                   f"Failed to {'enable' if enabled else 'disable'} Windows startup")
                
        except Exception as e:
            print(f"Error toggling Windows startup: {e}")
            # Revert checkbox
            self.windows_startup_var.set(not self.windows_startup_var.get())
            messagebox.showerror("Error", f"Failed to update startup setting: {e}")
    
    def _change_master_password(self):
        """Change master password."""
        dialog = MasterPasswordDialog(self.root, title="Change Master Password")
        if dialog.result:
            new_password = dialog.result
            
            # Verify current password first
            current_dialog = MasterPasswordDialog(self.root, title="Enter Current Password", confirm=False)
            if current_dialog.result and self.db_manager.verify_master_password(current_dialog.result):
                
                # Re-encrypt all credentials with new password
                credentials = self.db_manager.get_all_credentials(self.master_password)
                
                if self.db_manager.set_master_password(new_password):
                    # Re-save all credentials with new master password
                    for cred in credentials:
                        self.db_manager.store_credential(
                            cred['site_name'],
                            cred['site_url'],
                            cred['username'],
                            cred['password'],
                            new_password,
                            cred.get('notes', '')
                        )
                    
                    self.master_password = new_password
                    messagebox.showinfo("Success", "Master password changed successfully!")
                else:
                    messagebox.showerror("Error", "Failed to change master password!")
            else:
                messagebox.showerror("Error", "Current password verification failed!")
    
    def _export_credentials(self):
        """Export credentials (placeholder)."""
        messagebox.showinfo("Info", "Export feature coming soon!")
    
    def _import_credentials(self):
        """Import credentials (placeholder)."""
        messagebox.showinfo("Info", "Import feature coming soon!")
    
    def _import_browser_passwords(self):
        """Import passwords from browsers with enhanced verification."""
        try:
            # Get available browsers
            available_browsers = self.browser_importer.get_available_browsers()
            
            if not available_browsers:
                messagebox.showinfo("Browser Import", 
                                  "No browsers with saved passwords found.\n\n" +
                                  "Supported browsers: Chrome, Edge, Firefox, Opera, Brave")
                return
            
            # Show browser selection dialog
            browser_dialog = BrowserSelectionDialog(self.root, available_browsers)
            selected_browser = browser_dialog.show()
            
            if not selected_browser:
                return  # User cancelled
            
            # Enhanced verification dialog
            verification_result = self._show_import_verification_dialog(selected_browser)
            if not verification_result:
                return  # User cancelled verification
            
            # Import passwords with verification settings
            self._update_status("Importing and verifying browser passwords...")
            try:
                passwords = self.browser_importer.import_browser_passwords(selected_browser['id'])
                
                if not passwords:
                    messagebox.showinfo("Browser Import", "No passwords found to import.")
                    return
                
                # Verify and analyze imported passwords
                verified_passwords = self._verify_imported_passwords(passwords, verification_result)
                
                if not verified_passwords:
                    messagebox.showwarning("Browser Import", 
                                         "Passwords found but verification failed or all passwords were rejected.")
                    return
                
                # Convert to SilentLock format
                converted_passwords = self.browser_importer.export_to_silentlock_format(verified_passwords)
                
                if not converted_passwords:
                    messagebox.showwarning("Browser Import", 
                                         "Passwords found but could not be decrypted.\n" +
                                         "This may be due to browser security settings.")
                    return
                
                # Show enhanced import preview with security analysis
                if self._show_enhanced_import_preview(converted_passwords, verification_result):
                    # User confirmed import
                    imported_count = 0
                    skipped_count = 0
                    
                    for pwd in converted_passwords:
                        # Apply verification filters
                        if self._should_import_password(pwd, verification_result):
                            success = self.db_manager.store_credential(
                                pwd['site_name'],
                                pwd['site_url'],
                                pwd['username'],
                                pwd['password'],
                                self.master_password
                            )
                            
                            if success:
                                imported_count += 1
                                
                                # Log import for audit
                                if self.audit_logger:
                                    self.audit_logger.log_system_event(
                                        event_type="password_import",
                                        details={
                                            "source": selected_browser['name'],
                                            "site": pwd['site_name'],
                                            "verified": True
                                        }
                                    )
                            else:
                                skipped_count += 1
                        else:
                            skipped_count += 1
                    
                    self._refresh_credentials()
                    
                    # Show import summary
                    summary_msg = f"Import completed!\n\n"
                    summary_msg += f"✅ Successfully imported: {imported_count} passwords\n"
                    if skipped_count > 0:
                        summary_msg += f"⚠️ Skipped: {skipped_count} passwords (due to verification filters)"
                    
                    messagebox.showinfo("Import Complete", summary_msg)
                    self._update_status(f"Imported {imported_count} passwords from {selected_browser['name']}")
                else:
                    self._update_status("Import cancelled by user")
                    
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import passwords: {str(e)}")
                self._update_status("Import failed")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error accessing browser data: {str(e)}")
        finally:
            self._update_status("Ready")
    
    def _show_import_preview(self, passwords):
        """Show preview of passwords to be imported."""
        preview_dialog = ImportPreviewDialog(self.root, passwords)
        return preview_dialog.show()
    
    def _auto_import_browser_passwords(self):
        """Automatically import ALL browser passwords without user intervention."""
        try:
            print("Starting auto-import process...")
            self._log_activity("Auto-import starting...")
            
            # Check if we have a saved flag to prevent repeated auto-imports
            import os
            auto_import_flag = os.path.join(os.path.dirname(__file__), '..', '.auto_imported')
            
            if os.path.exists(auto_import_flag):
                self._log_activity("Auto-import already completed previously")
                print("Auto-import already completed previously")
                return  # Already auto-imported before
            
            # Verify we have a master password and database connection
            if not self.master_password:
                self._log_activity("ERROR: No master password available for auto-import")
                print("ERROR: No master password for auto-import")
                return
                
            if not self.authenticated:
                self._log_activity("ERROR: User not authenticated for auto-import")
                print("ERROR: User not authenticated for auto-import")
                return
            
            print(f"Auto-import: Master password available: {bool(self.master_password)}")
            print(f"Auto-import: User authenticated: {self.authenticated}")
            
            self._update_status("Auto-scanning ALL browsers for passwords...")
            self._log_activity("Starting automatic browser password import from ALL available browsers...")
            
            # Get available browsers
            available_browsers = self.browser_importer.get_available_browsers()
            print(f"Auto-import: Found {len(available_browsers)} browsers")
            
            if not available_browsers:
                self._log_activity("No browsers with saved passwords found")
                print("No browsers found for import")
                return
            
            total_imported = 0
            imported_from = []
            
            # Import from ALL available browsers automatically
            for browser in available_browsers:
                try:
                    self._update_status(f"Auto-importing ALL passwords from {browser['name']}...")
                    self._log_activity(f"Processing {browser['password_count']} passwords from {browser['name']}...")
                    print(f"Processing {browser['name']} with {browser['password_count']} passwords...")
                    
                    # Import ALL passwords without any filtering or user prompts
                    passwords = self.browser_importer.import_browser_passwords(browser['id'])
                    print(f"Extracted {len(passwords) if passwords else 0} passwords from {browser['name']}")
                    
                    if passwords:
                        # Convert ALL to SilentLock format
                        converted_passwords = self.browser_importer.export_to_silentlock_format(passwords)
                        print(f"Converted {len(converted_passwords) if converted_passwords else 0} passwords for storage")
                        
                        if converted_passwords:
                            # Store ALL passwords automatically
                            imported_count = 0
                            duplicate_count = 0
                            
                            for pwd in converted_passwords:
                                try:
                                    # Check for comprehensive duplicates
                                    duplicates = self.db_manager.check_duplicate_credentials(
                                        pwd['site_name'], pwd['site_url'], pwd['username'], self.master_password
                                    )
                                    
                                    # For auto-import, only skip exact matches to avoid duplicates
                                    if not duplicates.get('exact_match'):
                                        # Store new password
                                        success = self.db_manager.store_credential(
                                            pwd['site_name'],  # site_name
                                            pwd['site_url'],   # site_url  
                                            pwd['username'],   # username
                                            pwd['password'],   # password
                                            self.master_password,  # master_password
                                            pwd.get('notes', '') + f" [Auto-imported from {browser['name']}]"  # notes
                                        )
                                        if success:
                                            imported_count += 1
                                            print(f"Stored password for {pwd['site_name']}")
                                        else:
                                            print(f"Failed to store password for {pwd['site_name']}")
                                    else:
                                        duplicate_count += 1
                                        print(f"Skipped duplicate for {pwd['site_name']}")
                                except Exception as e:
                                    print(f"Error processing password for {pwd.get('site_name', 'unknown')}: {e}")
                                    continue
                            
                            if imported_count > 0:
                                total_imported += imported_count
                                imported_from.append(f"{browser['name']} ({imported_count} new)")
                                
                            self._log_activity(f"Processed {browser['name']}: {imported_count} imported, {duplicate_count} duplicates skipped")
                            print(f"Processed {browser['name']}: {imported_count} imported, {duplicate_count} duplicates")
                        else:
                            self._log_activity(f"Could not process passwords from {browser['name']} (decryption failed)")
                            print(f"Failed to convert passwords from {browser['name']}")
                    else:
                        self._log_activity(f"No passwords found in {browser['name']}")
                        print(f"No passwords extracted from {browser['name']}")
                
                except Exception as e:
                    self._log_activity(f"Auto-import failed for {browser['name']}: {str(e)}")
                    print(f"Error importing from {browser['name']}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Create flag file to prevent repeated auto-imports (only if successful)
            if total_imported > 0:
                try:
                    with open(auto_import_flag, 'w') as f:
                        f.write(f"auto-import completed - {total_imported} passwords imported")
                    self._log_activity(f"Auto-import flag created - {total_imported} passwords successfully imported")
                except Exception as e:
                    self._log_activity(f"Warning: Could not create auto-import flag: {e}")
            else:
                self._log_activity("Auto-import flag NOT created - no passwords were imported")
            
            # Refresh credentials display
            self._refresh_credentials()
            
            # Show completion notification
            if total_imported > 0:
                browser_list = ", ".join(imported_from)
                self._show_notification("Auto-Import Complete!", 
                                      f"Successfully imported {total_imported} passwords from: {browser_list}")
                self._log_activity(f"Auto-import complete: {total_imported} total passwords imported")
                
                # Silent completion - no dialog box interruption
                print(f"Auto-import successful: {total_imported} passwords imported from {browser_list}")
            else:
                self._log_activity("Auto-import complete: No new passwords found")
                # Don't show notification for empty imports
                print("Auto-import completed but no passwords were imported")
            
            self._update_status("Auto-import completed")
            
        except Exception as e:
            self._log_activity(f"Auto-import error: {str(e)}")
            print(f"Auto-import error: {e}")
        finally:
            self._update_status("Ready")
    
    def _log_activity(self, message):
        """Log activity to the activity log."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.activity_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.activity_log.see(tk.END)
    
    def _update_status(self, message):
        """Update status bar message."""
        self.status_label.config(text=message)
        # Clear status after 5 seconds
        self.root.after(5000, lambda: self.status_label.config(text="Ready"))
    
    def _reset_auto_import(self):
        """Reset the auto-import flag to allow re-importing."""
        try:
            import os
            auto_import_flag = os.path.join(os.path.dirname(__file__), '..', '.auto_imported')
            
            if os.path.exists(auto_import_flag):
                os.remove(auto_import_flag)
                messagebox.showinfo("Reset Complete", 
                                  "Auto-import flag reset. Browser passwords will be imported again on next startup.")
                self._log_activity("Auto-import flag reset - will re-import on next startup")
            else:
                messagebox.showinfo("Info", "Auto-import flag not found. Passwords will be imported on next startup.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset auto-import flag: {str(e)}")
    
    def _start_floating_eye(self):
        """Start the floating eye monitor if enabled."""
        try:
            if self.eye_settings.enabled and (self.eye_settings.auto_start or self.is_monitoring):
                if not self.floating_eye:
                    self.floating_eye = FloatingEyeWidget(on_toggle_callback=self._toggle_monitoring_via_eye)
                
                self.floating_eye.set_monitoring(self.is_monitoring)
                self.floating_eye.show()
                print("👁️ Floating eye monitor started")
        except Exception as e:
            print(f"Error starting floating eye: {e}")
    
    def _stop_floating_eye(self):
        """Stop the floating eye monitor."""
        try:
            if self.floating_eye:
                self.floating_eye.hide()
                print("👁️ Floating eye monitor hidden")
        except Exception as e:
            print(f"Error stopping floating eye: {e}")
    
    def _toggle_monitoring_via_eye(self):
        """Toggle monitoring when eye is clicked."""
        try:
            if self.is_monitoring:
                self._stop_monitoring()
                if self.floating_eye:
                    self.floating_eye.hide()
                    # Auto-show after 5 seconds
                    self.root.after(5000, lambda: self._start_floating_eye() if self.eye_settings.enabled else None)
            else:
                self._start_monitoring()
        except Exception as e:
            print(f"Error toggling monitoring via eye: {e}")
    
    def _toggle_floating_eye(self):
        """Toggle floating eye visibility and enable enhanced monitoring when checkbox is clicked."""
        try:
            enabled = self.floating_eye_var.get()
            self.eye_settings.enabled = enabled
            
            if enabled:
                # Enable floating eye and enhanced monitoring
                self._start_floating_eye()
                print("👁️ Floating eye enabled - Enhanced monitoring activated!")
                print("🔍 Eye will monitor and record everything accurately when active")
                
                # If monitoring is already active, enhance it
                if self.is_monitoring and self.floating_eye:
                    self.floating_eye.enhanced_monitoring = True
                    
            else:
                # Disable floating eye
                self._stop_floating_eye()
                print("👁️ Floating eye disabled - Standard monitoring resumed")
                
                # Reset to standard monitoring
                if self.floating_eye:
                    self.floating_eye.enhanced_monitoring = False
                
        except Exception as e:
            print(f"Error toggling floating eye: {e}")
    
    def _add_realtime_activity_tab(self):
        """Add real-time activity tab to the interface."""
        try:
            # Check if tab already exists
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Real-Time Activity" in tab_text:
                    print("✅ Real-time activity tab already exists")
                    return
            
            # Create activity frame
            activity_frame = ttk.Frame(self.notebook)
            self.notebook.add(activity_frame, text="🔄 Real-Time Activity")
            
            # Add the activity widget
            if self.realtime_tracker:
                self.activity_widget = RealTimeActivityWidget(activity_frame, self.realtime_tracker)
                print("✅ Real-time activity tab added successfully")
            else:
                # Fallback message
                ttk.Label(activity_frame, 
                         text="Real-time activity tracking unavailable.\nPlease restart monitoring to enable.",
                         justify='center').pack(expand=True)
                print("⚠️ Real-time activity tab added with fallback message")
                
        except Exception as e:
            print(f"Error adding real-time activity tab: {e}")
    
    def _add_eye_settings_to_settings_tab(self):
        """Add floating eye settings to the settings tab."""
        try:
            # Find the settings frame (it should be the last tab)
            for i in range(self.notebook.index("end")):
                tab_text = self.notebook.tab(i, "text")
                if "Settings" in tab_text:
                    settings_frame = self.notebook.nametowidget(self.notebook.tabs()[i])
                    print("👁️ Eye settings integrated in monitor settings")
                    break
        except Exception as e:
            print(f"Error adding eye settings: {e}")
    
    def _apply_eye_settings(self):
        """Apply floating eye settings."""
        try:
            self.eye_settings.apply_settings()
            
            # Update floating eye if it exists
            if self.floating_eye:
                if self.eye_settings.enabled:
                    if self.is_monitoring:
                        self.floating_eye.show()
                else:
                    self.floating_eye.hide()
                    
                # Update blink interval
                self.floating_eye.blink_interval = self.eye_settings.blink_interval
                
            print(f"👁️ Eye settings applied: enabled={self.eye_settings.enabled}")
        except Exception as e:
            print(f"Error applying eye settings: {e}")
    
    def run(self):
        """Start the GUI application."""
        self.root.mainloop()
    
    def on_closing(self):
        """Handle application closing."""
        if self.is_monitoring:
            self._stop_monitoring()
        
        # Destroy floating eye
        if self.floating_eye:
            self.floating_eye.destroy()
            
        self.root.destroy()


class MasterPasswordDialog:
    """Dialog for master password input."""
    
    def __init__(self, parent, title="Master Password", confirm=True):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        frame = ttk.Frame(self.dialog)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Enter master password:", font=('Arial', 12)).pack(pady=10)
        
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(frame, textvariable=self.password_var, show='*', width=30)
        self.password_entry.pack(pady=5)
        self.password_entry.focus()
        
        if confirm:
            ttk.Label(frame, text="Confirm password:", font=('Arial', 12)).pack(pady=(20, 5))
            self.confirm_var = tk.StringVar()
            self.confirm_entry = ttk.Entry(frame, textvariable=self.confirm_var, show='*', width=30)
            self.confirm_entry.pack(pady=5)
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="OK", command=self._ok_clicked).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._cancel_clicked).pack(side='left', padx=5)
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._ok_clicked())
        self.dialog.bind('<Escape>', lambda e: self._cancel_clicked())
        
        self.confirm = confirm
        
        # Wait for dialog
        self.dialog.wait_window()
    
    def _ok_clicked(self):
        password = self.password_var.get()
        
        if not password:
            messagebox.showerror("Error", "Password cannot be empty!")
            return
        
        if self.confirm:
            confirm_password = self.confirm_var.get()
            if password != confirm_password:
                messagebox.showerror("Error", "Passwords do not match!")
                return
        
        self.result = password
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        self.dialog.destroy()


class DuplicateDetectionDialog:
    """Dialog for handling duplicate credential detection."""
    
    def __init__(self, parent, duplicates_info, new_credential):
        self.parent = parent
        self.duplicates_info = duplicates_info
        self.new_credential = new_credential
        self.result = None
        self._create_dialog()
    
    def _create_dialog(self):
        """Create the duplicate detection dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Duplicate Credentials Detected")
        self.dialog.geometry("700x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Warning icon and title
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(title_frame, text="⚠️", font=("Arial", 24)).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(title_frame, text="Duplicate Credentials Detected", 
                 font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # New credential info
        new_cred_frame = ttk.LabelFrame(main_frame, text="New Credential", padding="10")
        new_cred_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(new_cred_frame, text=f"Site: {self.new_credential.get('site_name', 'Unknown')}").pack(anchor=tk.W)
        ttk.Label(new_cred_frame, text=f"URL: {self.new_credential.get('site_url', 'Unknown')}").pack(anchor=tk.W)
        ttk.Label(new_cred_frame, text=f"Username: {self.new_credential.get('username', 'Unknown')}").pack(anchor=tk.W)
        ttk.Label(new_cred_frame, text=f"Password: {'•' * len(self.new_credential.get('password', ''))}").pack(anchor=tk.W)
        
        # Scrollable frame for duplicates
        duplicates_frame = ttk.LabelFrame(main_frame, text="Existing Credentials", padding="10")
        duplicates_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        
        # Create scrollable text widget
        scroll_frame = tk.Frame(duplicates_frame)
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(scroll_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, 
                                  height=12, font=("Consolas", 9))
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_widget.yview)
        
        # Populate duplicates information
        self._populate_duplicates()
        
        # Action buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(15, 0))
        
        # Action explanation
        ttk.Label(button_frame, text="What would you like to do?", 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        # Buttons
        btn_frame = ttk.Frame(button_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Update Existing", 
                  command=lambda: self._set_result("update")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Keep Both", 
                  command=lambda: self._set_result("keep_both")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Cancel", 
                  command=lambda: self._set_result("cancel")).pack(side=tk.LEFT, padx=(0, 10))
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        duplicates_frame.rowconfigure(0, weight=1)
        duplicates_frame.columnconfigure(0, weight=1)
        
    def _populate_duplicates(self):
        """Populate the duplicates text widget with information."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        
        # Exact match
        if self.duplicates_info.get('exact_match'):
            exact = self.duplicates_info['exact_match']
            self.text_widget.insert(tk.END, "🎯 EXACT MATCH FOUND:\n", "header")
            self.text_widget.insert(tk.END, f"   Site: {exact['site_name']}\n")
            self.text_widget.insert(tk.END, f"   URL: {exact['site_url']}\n")
            self.text_widget.insert(tk.END, f"   Username: {exact['username']}\n")
            self.text_widget.insert(tk.END, f"   Password: {'•' * len(exact.get('password', ''))}\n")
            self.text_widget.insert(tk.END, f"   Created: {exact.get('created_at', 'Unknown')}\n")
            self.text_widget.insert(tk.END, f"   Last Used: {exact.get('last_used', 'Never')}\n\n")
        
        # Same site, different user
        if self.duplicates_info.get('same_site_different_user'):
            self.text_widget.insert(tk.END, "👥 SAME SITE, DIFFERENT USERS:\n", "header")
            for cred in self.duplicates_info['same_site_different_user']:
                self.text_widget.insert(tk.END, f"   • {cred['username']} (Password: {'•' * len(cred.get('password', ''))})\n")
            self.text_widget.insert(tk.END, "\n")
        
        # Same user, different site
        if self.duplicates_info.get('same_user_different_site'):
            self.text_widget.insert(tk.END, "🌐 SAME USER, DIFFERENT SITES:\n", "header")
            for cred in self.duplicates_info['same_user_different_site']:
                self.text_widget.insert(tk.END, f"   • {cred['site_name']} ({cred['site_url']})\n")
            self.text_widget.insert(tk.END, "\n")
        
        # Similar domains
        if self.duplicates_info.get('similar_domains'):
            self.text_widget.insert(tk.END, "🔗 SIMILAR DOMAINS:\n", "header")
            for cred in self.duplicates_info['similar_domains']:
                self.text_widget.insert(tk.END, f"   • {cred['site_name']} ({cred['site_url']})\n")
            self.text_widget.insert(tk.END, "\n")
        
        # Configure text tags for styling
        self.text_widget.tag_configure("header", font=("Arial", 10, "bold"), foreground="darkblue")
        self.text_widget.config(state=tk.DISABLED)
    
    def _set_result(self, action):
        """Set the dialog result and close."""
        self.result = action
        self.dialog.destroy()


class CredentialDialog:
    """Dialog for adding/editing credentials."""
    
    def __init__(self, parent, title="Credential", initial_data=None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x350")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        frame = ttk.Frame(self.dialog)
        frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Site name
        ttk.Label(frame, text="Site Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.site_name_var = tk.StringVar(value=initial_data['site_name'] if initial_data else '')
        ttk.Entry(frame, textvariable=self.site_name_var, width=40).grid(row=0, column=1, pady=5, padx=(10, 0))
        
        # Site URL
        ttk.Label(frame, text="Site URL:").grid(row=1, column=0, sticky='w', pady=5)
        self.site_url_var = tk.StringVar(value=initial_data['site_url'] if initial_data else '')
        ttk.Entry(frame, textvariable=self.site_url_var, width=40).grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # Username
        ttk.Label(frame, text="Username:").grid(row=2, column=0, sticky='w', pady=5)
        self.username_var = tk.StringVar(value=initial_data['username'] if initial_data else '')
        ttk.Entry(frame, textvariable=self.username_var, width=40).grid(row=2, column=1, pady=5, padx=(10, 0))
        
        # Password
        ttk.Label(frame, text="Password:").grid(row=3, column=0, sticky='w', pady=5)
        self.password_var = tk.StringVar(value=initial_data['password'] if initial_data else '')
        self.password_entry = ttk.Entry(frame, textvariable=self.password_var, show='*', width=40)
        self.password_entry.grid(row=3, column=1, pady=5, padx=(10, 0))
        
        # Show password checkbox
        self.show_password_var = tk.BooleanVar()
        show_cb = ttk.Checkbutton(frame, text="Show password", variable=self.show_password_var, command=self._toggle_password)
        show_cb.grid(row=4, column=1, sticky='w', padx=(10, 0))
        
        # Notes
        ttk.Label(frame, text="Notes:").grid(row=5, column=0, sticky='nw', pady=5)
        self.notes_text = tk.Text(frame, width=30, height=4)
        self.notes_text.grid(row=5, column=1, pady=5, padx=(10, 0))
        
        if initial_data and 'notes' in initial_data:
            self.notes_text.insert('1.0', initial_data['notes'])
        
        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Save", command=self._save_clicked).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._cancel_clicked).pack(side='left', padx=5)
        
        # Configure grid weights
        frame.grid_columnconfigure(1, weight=1)
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._save_clicked())
        self.dialog.bind('<Escape>', lambda e: self._cancel_clicked())
        
        # Wait for dialog
        self.dialog.wait_window()
    
    def _toggle_password(self):
        """Toggle password visibility."""
        if self.show_password_var.get():
            self.password_entry.config(show='')
        else:
            self.password_entry.config(show='*')
    
    def _save_clicked(self):
        site_name = self.site_name_var.get().strip()
        site_url = self.site_url_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()
        notes = self.notes_text.get('1.0', tk.END).strip()
        
        if not all([site_name, site_url, username, password]):
            messagebox.showerror("Error", "All fields except notes are required!")
            return
        
        self.result = {
            'site_name': site_name,
            'site_url': site_url,
            'username': username,
            'password': password,
            'notes': notes
        }
        
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        self.dialog.destroy()
    
    def _show_import_verification_dialog(self, selected_browser):
        """Show enhanced verification dialog for import."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Verification Settings")
        dialog.geometry("600x500")
        dialog.resizable(False, False)
        
        # Center window
        dialog.geometry("+%d+%d" % (
            (dialog.winfo_screenwidth() // 2) - 300,
            (dialog.winfo_screenheight() // 2) - 250
        ))
        
        result = {}
        
        main_frame = tk.Frame(dialog, bg='#f8f9fa', padx=30, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        tk.Label(
            main_frame, text=f"🔍 Import Verification - {selected_browser['name']}",
            font=('Arial', 16, 'bold'), bg='#f8f9fa'
        ).pack(pady=(0, 20))
        
        # Verification options
        tk.Label(
            main_frame, text="Select verification and filtering options:",
            font=('Arial', 11, 'bold'), bg='#f8f9fa'
        ).pack(anchor='w', pady=(0, 10))
        
        # Security checks
        security_frame = tk.LabelFrame(main_frame, text="Security Verification", bg='#f8f9fa')
        security_frame.pack(fill='x', pady=(0, 15))
        
        check_weak_var = tk.BooleanVar(value=True)
        tk.Checkbutton(security_frame, text="Skip weak passwords (< 8 characters or common passwords)", 
                      variable=check_weak_var, bg='#f8f9fa').pack(anchor='w', padx=10, pady=2)
        
        check_duplicates_var = tk.BooleanVar(value=True)
        tk.Checkbutton(security_frame, text="Skip duplicate passwords already in SilentLock", 
                      variable=check_duplicates_var, bg='#f8f9fa').pack(anchor='w', padx=10, pady=2)
        
        check_empty_var = tk.BooleanVar(value=True)
        tk.Checkbutton(security_frame, text="Skip entries with empty username or password", 
                      variable=check_empty_var, bg='#f8f9fa').pack(anchor='w', padx=10, pady=2)
        
        # Content filters
        content_frame = tk.LabelFrame(main_frame, text="Content Filters", bg='#f8f9fa')
        content_frame.pack(fill='x', pady=(0, 15))
        
        filter_test_var = tk.BooleanVar(value=True)
        tk.Checkbutton(content_frame, text="Skip test/temporary passwords (containing 'test', 'temp', etc.)", 
                      variable=filter_test_var, bg='#f8f9fa').pack(anchor='w', padx=10, pady=2)
        
        filter_localhost_var = tk.BooleanVar(value=False)
        tk.Checkbutton(content_frame, text="Skip localhost/development site passwords", 
                      variable=filter_localhost_var, bg='#f8f9fa').pack(anchor='w', padx=10, pady=2)
        
        # Import options
        options_frame = tk.LabelFrame(main_frame, text="Import Options", bg='#f8f9fa')
        options_frame.pack(fill='x', pady=(0, 15))
        
        require_confirmation_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Show detailed preview before importing", 
                      variable=require_confirmation_var, bg='#f8f9fa').pack(anchor='w', padx=10, pady=2)
        
        backup_existing_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="Create backup before importing", 
                      variable=backup_existing_var, bg='#f8f9fa').pack(anchor='w', padx=10, pady=2)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(pady=(20, 0))
        
        def proceed():
            result.update({
                'check_weak': check_weak_var.get(),
                'check_duplicates': check_duplicates_var.get(),
                'check_empty': check_empty_var.get(),
                'filter_test': filter_test_var.get(),
                'filter_localhost': filter_localhost_var.get(),
                'require_confirmation': require_confirmation_var.get(),
                'backup_existing': backup_existing_var.get(),
                'proceed': True
            })
            dialog.destroy()
        
        def cancel():
            result['proceed'] = False
            dialog.destroy()
        
        tk.Button(button_frame, text="Proceed with Import", command=proceed,
                 bg='#28a745', fg='white', font=('Arial', 11, 'bold'), padx=20, pady=8).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="Cancel", command=cancel,
                 bg='#6c757d', fg='white', font=('Arial', 11, 'bold'), padx=20, pady=8).pack(side='left')
        
        dialog.wait_window()
        return result if result.get('proceed') else None
    
    def _verify_imported_passwords(self, passwords, verification_settings):
        """Verify imported passwords based on settings."""
        verified = []
        
        for pwd in passwords:
            # Skip if empty fields and setting enabled
            if verification_settings.get('check_empty', True):
                if not pwd.get('username') or not pwd.get('password') or not pwd.get('url'):
                    continue
            
            # Skip weak passwords
            if verification_settings.get('check_weak', True):
                password = pwd.get('password', '')
                if len(password) < 8 or password.lower() in ['password', '123456', 'qwerty', 'abc123']:
                    continue
            
            # Skip test passwords
            if verification_settings.get('filter_test', True):
                username = pwd.get('username', '').lower()
                password = pwd.get('password', '').lower()
                url = pwd.get('url', '').lower()
                
                test_keywords = ['test', 'temp', 'demo', 'example', 'sample']
                if any(keyword in username or keyword in password or keyword in url for keyword in test_keywords):
                    continue
            
            # Skip localhost if enabled
            if verification_settings.get('filter_localhost', False):
                url = pwd.get('url', '').lower()
                if 'localhost' in url or '127.0.0.1' in url or 'local.' in url:
                    continue
            
            # Skip duplicates
            if verification_settings.get('check_duplicates', True):
                # Check if password already exists
                if self._password_exists(pwd.get('url', ''), pwd.get('username', '')):
                    continue
            
            verified.append(pwd)
        
        return verified
    
    def _password_exists(self, url, username):
        """Check if password already exists in database."""
        try:
            existing = self.db_manager.get_credentials()
            for cred in existing:
                if cred.get('site_url') == url and cred.get('username') == username:
                    return True
        except:
            pass
        return False
    
    def _should_import_password(self, pwd, verification_settings):
        """Determine if password should be imported based on settings."""
        return True  # All filtering done in _verify_imported_passwords
    
    def _show_enhanced_import_preview(self, passwords, verification_settings):
        """Show enhanced import preview with security analysis."""
        if not verification_settings.get('require_confirmation', True):
            return True  # Skip preview if not required
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Import Preview & Security Analysis")
        dialog.geometry("800x600")
        
        # Center window
        dialog.geometry("+%d+%d" % (
            (dialog.winfo_screenwidth() // 2) - 400,
            (dialog.winfo_screenheight() // 2) - 300
        ))
        
        main_frame = tk.Frame(dialog, bg='#f8f9fa', padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title and summary
        tk.Label(
            main_frame, text="🔍 Import Preview & Security Analysis",
            font=('Arial', 16, 'bold'), bg='#f8f9fa'
        ).pack(pady=(0, 10))
        
        # Summary stats
        stats_frame = tk.Frame(main_frame, bg='#e3f2fd', relief='ridge', bd=1)
        stats_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(
            stats_frame, text=f"📊 Ready to import {len(passwords)} verified passwords",
            font=('Arial', 12, 'bold'), bg='#e3f2fd', fg='#1976d2'
        ).pack(pady=10)
        
        # Password list
        tk.Label(main_frame, text="Passwords to be imported:", font=('Arial', 11, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        # Tree view for passwords
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True, pady=(5, 15))
        
        columns = ("Site", "Username", "Security", "Notes")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=12)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Populate tree
        for pwd in passwords[:50]:  # Limit to first 50 for performance
            site_name = pwd.get('site_name', 'Unknown')
            username = pwd.get('username', 'No username')
            
            # Simple security analysis
            password = pwd.get('password', '')
            if len(password) >= 12:
                security = "🔒 Strong"
            elif len(password) >= 8:
                security = "🔓 Medium"
            else:
                security = "⚠️ Weak"
            
            notes = f"Length: {len(password)} chars"
            
            tree.insert('', 'end', values=(site_name[:30], username[:20], security, notes))
        
        if len(passwords) > 50:
            tree.insert('', 'end', values=(f"... and {len(passwords) - 50} more", "", "", ""))
        
        # Buttons
        result = [False]
        
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(pady=(15, 0))
        
        def confirm_import():
            result[0] = True
            dialog.destroy()
        
        def cancel_import():
            dialog.destroy()
        
        tk.Button(button_frame, text="✅ Import All Passwords", command=confirm_import,
                 bg='#28a745', fg='white', font=('Arial', 11, 'bold'), padx=20, pady=8).pack(side='left', padx=(0, 10))
        tk.Button(button_frame, text="❌ Cancel Import", command=cancel_import,
                 bg='#dc3545', fg='white', font=('Arial', 11, 'bold'), padx=20, pady=8).pack(side='left')
        
        dialog.wait_window()
        return result[0]


class BrowserSelectionDialog:
    """Dialog for selecting browser to import from."""
    
    def __init__(self, parent, available_browsers):
        self.parent = parent
        self.available_browsers = available_browsers
        self.result = None
    
    def show(self):
        """Show browser selection dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Import Browser Passwords")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            (self.dialog.winfo_screenwidth() // 2) - 200,
            (self.dialog.winfo_screenheight() // 2) - 150
        ))
        
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Select Browser to Import From",
                             font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Browser list
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        self.browser_listbox = tk.Listbox(list_frame, height=8)
        scrollbar = tk.Scrollbar(list_frame, orient='vertical', command=self.browser_listbox.yview)
        self.browser_listbox.configure(yscrollcommand=scrollbar.set)
        
        for browser in self.available_browsers:
            display_text = f"{browser['name']} ({browser['password_count']} passwords)"
            self.browser_listbox.insert(tk.END, display_text)
        
        self.browser_listbox.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Select first item by default
        if self.available_browsers:
            self.browser_listbox.selection_set(0)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack()
        
        import_button = tk.Button(button_frame, text="Import", command=self._import_clicked,
                                bg='#2E8B57', fg='white', font=('Arial', 10, 'bold'),
                                padx=20, pady=8, relief='flat')
        import_button.pack(side='left', padx=(0, 10))
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=self._cancel_clicked,
                                bg='#DC143C', fg='white', font=('Arial', 10),
                                padx=20, pady=8, relief='flat')
        cancel_button.pack(side='left')
        
        # Bind double-click
        self.browser_listbox.bind('<Double-Button-1>', lambda e: self._import_clicked())
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result
    
    def _import_clicked(self):
        """Handle import button click."""
        selection = self.browser_listbox.curselection()
        if selection:
            self.result = self.available_browsers[selection[0]]
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        """Handle cancel button click."""
        self.dialog.destroy()


class ImportPreviewDialog:
    """Dialog for previewing passwords before import."""
    
    def __init__(self, parent, passwords):
        self.parent = parent
        self.passwords = passwords
        self.result = False
    
    def show(self):
        """Show import preview dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Import Preview")
        self.dialog.geometry("600x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            (self.dialog.winfo_screenwidth() // 2) - 300,
            (self.dialog.winfo_screenheight() // 2) - 250
        ))
        
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_text = f"Import Preview - {len(self.passwords)} passwords found"
        title_label = tk.Label(main_frame, text=title_text, font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # Info
        info_label = tk.Label(main_frame, 
                            text="The following passwords will be imported into SilentLock:",
                            font=('Arial', 10))
        info_label.pack(pady=(0, 15))
        
        # Password list
        list_frame = tk.Frame(main_frame)
        list_frame.pack(fill='both', expand=True, pady=(0, 20))
        
        columns = ('Site', 'Username', 'URL')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.tree.heading('Site', text='Site Name')
        self.tree.heading('Username', text='Username')
        self.tree.heading('URL', text='URL')
        
        self.tree.column('Site', width=150)
        self.tree.column('Username', width=150)
        self.tree.column('URL', width=250)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tree and scrollbars
        self.tree.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')
        
        # Populate tree
        for pwd in self.passwords:
            self.tree.insert('', 'end', values=(
                pwd['site_name'],
                pwd['username'],
                pwd['site_url'][:50] + '...' if len(pwd['site_url']) > 50 else pwd['site_url']
            ))
        
        # Warning
        warning_frame = tk.Frame(main_frame, bg='#FFF3CD', relief='solid', bd=1)
        warning_frame.pack(fill='x', pady=(0, 20))
        
        warning_label = tk.Label(warning_frame, 
                               text="⚠️ Existing passwords for the same sites will NOT be overwritten.",
                               bg='#FFF3CD', font=('Arial', 9), fg='#856404')
        warning_label.pack(pady=8)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack()
        
        import_button = tk.Button(button_frame, text="Import All", command=self._import_clicked,
                                bg='#2E8B57', fg='white', font=('Arial', 10, 'bold'),
                                padx=30, pady=10, relief='flat')
        import_button.pack(side='left', padx=(0, 15))
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=self._cancel_clicked,
                                bg='#DC143C', fg='white', font=('Arial', 10),
                                padx=30, pady=10, relief='flat')
        cancel_button.pack(side='left')
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result
    
    def _import_clicked(self):
        """Handle import button click."""
        self.result = True
        self.dialog.destroy()
    
    def _cancel_clicked(self):
        """Handle cancel button click."""
        self.dialog.destroy()


# Try to import pyperclip, fall back to basic clipboard if not available
try:
    import pyperclip
except ImportError:
    class MockPyperclip:
        @staticmethod
        def copy(text):
            print(f"Would copy to clipboard: {text}")
    
    pyperclip = MockPyperclip()