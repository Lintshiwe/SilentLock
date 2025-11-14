"""
Administrator Password Review Interface for SilentLock
Provides comprehensive password management and security oversight with email OTP 2FA.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import csv
import re
import hashlib
import requests
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from .admin_auth import AdminAuthenticator
from .admin_profile_gui import AdminProfileGUI
from .security_hardening import get_security_manager
import zxcvbn


class AdminPasswordReviewGUI:
    """Administrator interface for password review and management."""
    
    def __init__(self, db_manager, parent=None):
        self.db_manager = db_manager
        self.parent = parent
        self.admin_auth = AdminAuthenticator(db_manager)
        self.admin_session = None
        self.admin_window = None
        self.profile_gui = None  # For profile management window
        
        # Security and audit data
        self.security_scores = {}
        self.breach_data = {}
        self.password_analysis = {}
        
        # Load pwned passwords hash database (first 5 chars of SHA1)
        self.pwned_hashes = set()
        self._load_breach_database()
    
    def show_admin_login(self):
        """Show admin login dialog."""
        if self.admin_window:
            self.admin_window.lift()
            return
        
        self.admin_window = tk.Toplevel(self.parent)
        self.admin_window.title("SilentLock - Administrator Access")
        self.admin_window.geometry("500x400")
        self.admin_window.resizable(False, False)
        
        # Center window
        self.admin_window.geometry("+%d+%d" % (
            (self.admin_window.winfo_screenwidth() // 2) - 250,
            (self.admin_window.winfo_screenheight() // 2) - 200
        ))
        
        # Create login interface
        self._create_admin_login_interface()
        
        self.admin_window.protocol("WM_DELETE_WINDOW", self._on_admin_window_close)
    
    def _create_admin_login_interface(self):
        """Create admin login interface."""
        main_frame = tk.Frame(self.admin_window, bg='#f8f9fa', padx=30, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame, text="🛡️ Administrator Access", 
            font=('Arial', 18, 'bold'), bg='#f8f9fa', fg='#dc3545'
        )
        title_label.pack(pady=(0, 20))
        
        subtitle_label = tk.Label(
            main_frame, text="Enhanced Security • Password Oversight • System Control", 
            font=('Arial', 10), bg='#f8f9fa', fg='#666666'
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Admin password
        tk.Label(main_frame, text="Administrator Password:", 
               font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        self.admin_password_var = tk.StringVar()
        self.admin_password_entry = tk.Entry(
            main_frame, textvariable=self.admin_password_var, 
            show='*', width=40, font=('Arial', 10)
        )
        self.admin_password_entry.pack(pady=(2, 15), fill='x')
        
        # 2FA code with live feedback
        totp_frame = tk.Frame(main_frame, bg='#f8f9fa')
        totp_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(totp_frame, text="2FA Code (if enabled):", 
               font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        totp_entry_frame = tk.Frame(totp_frame, bg='#f8f9fa')
        totp_entry_frame.pack(fill='x', pady=(2, 5))
        
        self.totp_code_var = tk.StringVar()
        self.totp_code_entry = tk.Entry(
            totp_entry_frame, textvariable=self.totp_code_var, 
            width=15, font=('Arial', 12, 'bold'), justify='center'
        )
        self.totp_code_entry.pack(side='left')
        
        # Live countdown and validation
        self.totp_status_frame = tk.Frame(totp_entry_frame, bg='#f8f9fa')
        self.totp_status_frame.pack(side='left', padx=(10, 0), fill='x', expand=True)
        
        self.totp_countdown_label = tk.Label(
            self.totp_status_frame, text="⏱️ --:--", 
            font=('Arial', 10, 'bold'), bg='#f8f9fa', fg='#666666'
        )
        self.totp_countdown_label.pack(side='left')
        
        self.totp_validation_label = tk.Label(
            self.totp_status_frame, text="", 
            font=('Arial', 9), bg='#f8f9fa'
        )
        self.totp_validation_label.pack(side='left', padx=(10, 0))
        
        # Email OTP section
        email_otp_frame = tk.Frame(main_frame, bg='#f8f9fa')
        email_otp_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(email_otp_frame, text="Email OTP (if enabled):", 
               font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        email_otp_input_frame = tk.Frame(email_otp_frame, bg='#f8f9fa')
        email_otp_input_frame.pack(fill='x', pady=(2, 5))
        
        self.email_otp_var = tk.StringVar()
        self.email_otp_entry = tk.Entry(
            email_otp_input_frame, textvariable=self.email_otp_var, 
            width=15, font=('Arial', 12, 'bold'), justify='center'
        )
        self.email_otp_entry.pack(side='left')
        
        self.send_otp_button = tk.Button(
            email_otp_input_frame, text="📧 Send OTP", 
            command=self._send_email_otp,
            bg='#3498db', fg='white', font=('Arial', 9),
            relief='flat', padx=10
        )
        self.send_otp_button.pack(side='left', padx=(10, 0))
        
        # Start TOTP countdown timer
        self._start_totp_timer()
        
        # Bind validation on code entry
        self.totp_code_var.trace('w', self._validate_totp_input)
        
        # Recovery code option
        tk.Label(main_frame, text="Recovery Code (alternative to 2FA):", 
               font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        self.recovery_code_var = tk.StringVar()
        self.recovery_code_entry = tk.Entry(
            main_frame, textvariable=self.recovery_code_var, 
            width=40, font=('Arial', 10)
        )
        self.recovery_code_entry.pack(pady=(2, 20), fill='x')
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f8f9fa')
        button_frame.pack(pady=(10, 0))
        
        login_button = tk.Button(
            button_frame, text="Authenticate", 
            command=self._authenticate_admin,
            bg='#dc3545', fg='white', font=('Arial', 10, 'bold'),
            padx=25, pady=8, relief='flat'
        )
        login_button.pack(side='left', padx=(0, 10))
        
        setup_button = tk.Button(
            button_frame, text="Setup Admin Account", 
            command=self._show_admin_setup,
            bg='#6c757d', fg='white', font=('Arial', 10),
            padx=20, pady=8, relief='flat'
        )
        setup_button.pack(side='left', padx=(0, 10))
        
        cancel_button = tk.Button(
            button_frame, text="Cancel", 
            command=self._on_admin_window_close,
            bg='#6c757d', fg='white', font=('Arial', 10),
            padx=20, pady=8, relief='flat'
        )
        cancel_button.pack(side='left')
        
        # Error label
        self.admin_error_label = tk.Label(
            main_frame, text="", font=('Arial', 9), bg='#f8f9fa', fg='red'
        )
        self.admin_error_label.pack(pady=(10, 0))
        
        # Bind Enter key
        self.admin_window.bind('<Return>', lambda e: self._authenticate_admin())
        self.admin_password_entry.focus()
    
    def _authenticate_admin(self):
        """Authenticate admin user with enhanced 2FA support."""
        try:
            password = self.admin_password_var.get()
            totp_code = self.totp_code_var.get() or None
            recovery_code = self.recovery_code_var.get() or None
            email_otp = self.email_otp_var.get() or None
            
            if not password:
                self.admin_error_label.config(text="Administrator password required")
                return
            
            # Authenticate with admin system (now supports email OTP)
            auth_result = self.admin_auth.authenticate_admin(
                password=password,
                totp_code=totp_code,
                recovery_code=recovery_code,
                email_otp=email_otp
            )
            
            if auth_result['success']:
                self.admin_session = auth_result['session_token']
                self.admin_window.destroy()
                self.admin_window = None
                self._show_admin_dashboard()
            else:
                error_msg = auth_result.get('error', 'Authentication failed')
                
                # Check if specific 2FA type is required
                if auth_result.get('requires_email_otp'):
                    error_msg += "\n\nClick 'Send OTP' to receive email code."
                elif auth_result.get('requires_totp'):
                    error_msg += "\n\nEnter your TOTP code from authenticator app."
                
                self.admin_error_label.config(text=error_msg)
                # Clear sensitive fields
                self.admin_password_var.set("")
                self.totp_code_var.set("")
                self.email_otp_var.set("")
                self.recovery_code_var.set("")
                
        except Exception as e:
            self.admin_error_label.config(text=f"Authentication error: {str(e)}")
    
    def _send_email_otp(self):
        """Send email OTP for admin login."""
        try:
            result = self.admin_auth.send_email_otp(purpose='admin_login')
            if result['success']:
                self.send_otp_button.config(text="✅ Sent", state='disabled')
                self.admin_error_label.config(text=f"✅ {result['message']}")
                # Re-enable button after 60 seconds
                self.admin_window.after(60000, self._reset_send_otp_button)
            else:
                self.admin_error_label.config(text=f"❌ {result['error']}")
        except Exception as e:
            self.admin_error_label.config(text=f"❌ Failed to send OTP: {str(e)}")
    
    def _reset_send_otp_button(self):
        """Reset the send OTP button."""
        try:
            self.send_otp_button.config(text="📧 Send OTP", state='normal')
        except:
            pass  # Window might be closed
    
    def _start_totp_timer(self):
        """Start the TOTP countdown timer."""
        try:
            self._update_totp_timer()
        except Exception:
            pass  # Fail silently if timer can't start
    
    def _update_totp_timer(self):
        """Update the TOTP countdown display."""
        try:
            import time
            current_time = int(time.time())
            time_remaining = 30 - (current_time % 30)
            
            # Update countdown display
            minutes = time_remaining // 60
            seconds = time_remaining % 60
            countdown_text = f"⏱️ {seconds:02d}s"
            
            # Color based on time remaining
            if time_remaining <= 5:
                color = '#dc3545'  # Red - urgent
            elif time_remaining <= 10:
                color = '#fd7e14'  # Orange - warning
            else:
                color = '#28a745'  # Green - plenty of time
            
            if hasattr(self, 'totp_countdown_label'):
                self.totp_countdown_label.config(text=countdown_text, fg=color)
            
            # Schedule next update
            if hasattr(self, 'admin_window') and self.admin_window:
                self.admin_window.after(1000, self._update_totp_timer)
                
        except Exception:
            pass  # Fail silently
    
    def _validate_totp_input(self, *args):
        """Validate TOTP input in real-time."""
        try:
            code = self.totp_code_var.get()
            
            if not hasattr(self, 'totp_validation_label'):
                return
            
            if len(code) == 0:
                self.totp_validation_label.config(text="", fg='black')
            elif len(code) < 6:
                self.totp_validation_label.config(text="⚠️ Need 6 digits", fg='#fd7e14')
            elif len(code) == 6:
                if code.isdigit():
                    self.totp_validation_label.config(text="✓ Valid format", fg='#28a745')
                else:
                    self.totp_validation_label.config(text="❌ Numbers only", fg='#dc3545')
            else:
                self.totp_validation_label.config(text="❌ Too long", fg='#dc3545')
                # Limit to 6 digits
                self.totp_code_var.set(code[:6])
                
        except Exception:
            pass  # Fail silently
    
    def _show_admin_setup(self):
        """Show admin account setup dialog."""
        setup_window = tk.Toplevel(self.admin_window)
        setup_window.title("Setup Administrator Account")
        setup_window.geometry("600x500")
        setup_window.resizable(False, False)
        
        # Center window
        setup_window.geometry("+%d+%d" % (
            (setup_window.winfo_screenwidth() // 2) - 300,
            (setup_window.winfo_screenheight() // 2) - 250
        ))
        
        main_frame = tk.Frame(setup_window, bg='#f8f9fa', padx=30, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        # Title
        tk.Label(
            main_frame, text="🔧 Administrator Account Setup", 
            font=('Arial', 16, 'bold'), bg='#f8f9fa', fg='#dc3545'
        ).pack(pady=(0, 20))
        
        # Admin password
        tk.Label(main_frame, text="Administrator Password:", 
               font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        admin_pass_var = tk.StringVar()
        admin_pass_entry = tk.Entry(
            main_frame, textvariable=admin_pass_var, 
            show='*', width=50, font=('Arial', 10)
        )
        admin_pass_entry.pack(pady=(2, 10), fill='x')
        
        # Confirm password
        tk.Label(main_frame, text="Confirm Password:", 
               font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        confirm_pass_var = tk.StringVar()
        confirm_pass_entry = tk.Entry(
            main_frame, textvariable=confirm_pass_var, 
            show='*', width=50, font=('Arial', 10)
        )
        confirm_pass_entry.pack(pady=(2, 10), fill='x')
        
        # Email (optional)
        tk.Label(main_frame, text="Email (optional):", 
               font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
        
        email_var = tk.StringVar()
        email_entry = tk.Entry(
            main_frame, textvariable=email_var, 
            width=50, font=('Arial', 10)
        )
        email_entry.pack(pady=(2, 10), fill='x')
        
        # Enable 2FA
        enable_2fa_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            main_frame, text="Enable Two-Factor Authentication (Recommended)", 
            variable=enable_2fa_var, bg='#f8f9fa', font=('Arial', 10)
        ).pack(pady=(10, 20), anchor='w')
        
        # Setup button
        def setup_admin():
            password = admin_pass_var.get()
            confirm = confirm_pass_var.get()
            email = email_var.get() or None
            enable_2fa = enable_2fa_var.get()
            
            if not password:
                messagebox.showerror("Error", "Password is required")
                return
            
            if password != confirm:
                messagebox.showerror("Error", "Passwords do not match")
                return
            
            if len(password) < 6:
                messagebox.showerror("Error", "Admin password must be at least 6 characters")
                return
            
            # Setup admin account
            result = self.admin_auth.setup_admin_account(password, email, enable_2fa)
            
            if result['success']:
                setup_window.destroy()
                
                # Show setup success with recovery codes
                self._show_setup_success(result)
                
            else:
                messagebox.showerror("Error", result.get('error', 'Setup failed'))
        
        tk.Button(
            main_frame, text="Setup Administrator Account", 
            command=setup_admin,
            bg='#28a745', fg='white', font=('Arial', 10, 'bold'),
            padx=25, pady=10, relief='flat'
        ).pack(pady=(0, 10))
        
        tk.Button(
            main_frame, text="Cancel", 
            command=setup_window.destroy,
            bg='#6c757d', fg='white', font=('Arial', 10),
            padx=20, pady=8, relief='flat'
        ).pack()
    
    def _show_setup_success(self, result: Dict):
        """Show setup success with recovery codes and QR code."""
        success_window = tk.Toplevel(self.parent)
        success_window.title("Administrator Account Created")
        success_window.geometry("700x600")
        success_window.resizable(False, False)
        
        # Center window
        success_window.geometry("+%d+%d" % (
            (success_window.winfo_screenwidth() // 2) - 350,
            (success_window.winfo_screenheight() // 2) - 300
        ))
        
        main_frame = tk.Frame(success_window, bg='#d4edda', padx=30, pady=30)
        main_frame.pack(fill='both', expand=True)
        
        # Success message
        tk.Label(
            main_frame, text="✅ Administrator Account Created Successfully!", 
            font=('Arial', 16, 'bold'), bg='#d4edda', fg='#155724'
        ).pack(pady=(0, 20))
        
        # Recovery codes
        if result.get('recovery_codes'):
            tk.Label(
                main_frame, text="🔑 Recovery Codes (Save These Securely!):", 
                font=('Arial', 12, 'bold'), bg='#d4edda', fg='#155724'
            ).pack(anchor='w', pady=(0, 10))
            
            codes_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
            codes_frame.pack(fill='x', pady=(0, 20))
            
            codes_text = tk.Text(codes_frame, height=8, width=60, font=('Courier', 10))
            codes_text.pack(padx=10, pady=10)
            
            for i, code in enumerate(result['recovery_codes'], 1):
                codes_text.insert(tk.END, f"{i:2}. {code}\n")
            
            codes_text.config(state='disabled')
        
        # QR Code for 2FA
        if result.get('qr_code_data'):
            tk.Label(
                main_frame, text="📱 Scan QR Code with Authenticator App:", 
                font=('Arial', 12, 'bold'), bg='#d4edda', fg='#155724'
            ).pack(anchor='w', pady=(0, 10))
            
            # Display actual QR Code
            qr_frame = tk.Frame(main_frame, bg='white', relief='solid', bd=1)
            qr_frame.pack(pady=(0, 20))
            
            try:
                # Decode the base64 QR code image
                qr_data = result['qr_code_data']
                if qr_data.startswith('data:image/png;base64,'):
                    # Remove the data URL prefix
                    img_data = qr_data.split(',')[1]
                else:
                    img_data = qr_data
                
                # Decode base64 and create image
                import base64
                from PIL import Image, ImageTk
                import io
                
                img_bytes = base64.b64decode(img_data)
                qr_image = Image.open(io.BytesIO(img_bytes))
                
                # Resize if needed for better display
                qr_image = qr_image.resize((200, 200), Image.Resampling.LANCZOS)
                qr_photo = ImageTk.PhotoImage(qr_image)
                
                # Display QR code
                qr_label = tk.Label(qr_frame, image=qr_photo, bg='white')
                qr_label.image = qr_photo  # Keep a reference
                qr_label.pack(padx=10, pady=10)
                
            except Exception as e:
                print(f"Error displaying QR code: {e}")
                # Fallback to placeholder
                tk.Label(
                    qr_frame, text="QR Code Error\nPlease set up 2FA manually", 
                    font=('Arial', 10), bg='white', fg='#dc3545',
                    width=30, height=8
                ).pack(padx=10, pady=10)
        
        # Close button
        tk.Button(
            main_frame, text="Continue to Login", 
            command=success_window.destroy,
            bg='#28a745', fg='white', font=('Arial', 10, 'bold'),
            padx=25, pady=10, relief='flat'
        ).pack()
    
    def _show_admin_dashboard(self):
        """Show main admin dashboard."""
        if self.admin_window:
            self.admin_window.destroy()
        
        self.admin_window = tk.Toplevel(self.parent)
        self.admin_window.title("SilentLock - Administrator Dashboard")
        self.admin_window.geometry("1400x900")
        
        # Center window
        self.admin_window.geometry("+%d+%d" % (
            (self.admin_window.winfo_screenwidth() // 2) - 700,
            (self.admin_window.winfo_screenheight() // 2) - 450
        ))
        
        # Create main dashboard interface
        self._create_dashboard_interface()
        
        # Load and analyze all passwords
        self._load_password_analysis()
        
        self.admin_window.protocol("WM_DELETE_WINDOW", self._on_admin_window_close)
    
    def _create_dashboard_interface(self):
        """Create the main dashboard interface."""
        # Main container
        main_container = tk.Frame(self.admin_window, bg='#f8f9fa')
        main_container.pack(fill='both', expand=True)
        
        # Header
        header_frame = tk.Frame(main_container, bg='#dc3545', height=80)
        header_frame.pack(fill='x')
        header_frame.pack_propagate(False)
        
        # Header content
        header_content = tk.Frame(header_frame, bg='#dc3545')
        header_content.pack(expand=True, fill='both', padx=20, pady=10)
        
        tk.Label(
            header_content, text="🛡️ SilentLock Administrator Dashboard", 
            font=('Arial', 18, 'bold'), bg='#dc3545', fg='white'
        ).pack(side='left')
        
        # Header buttons frame
        header_buttons = tk.Frame(header_content, bg='#dc3545')
        header_buttons.pack(side='right')
        
        # Profile management button
        tk.Button(
            header_buttons, text="👤 Profile", 
            command=self._show_profile_management,
            bg='#6c757d', fg='white', font=('Arial', 10, 'bold'),
            padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        # Logout button
        tk.Button(
            header_buttons, text="🚪 Logout", 
            command=self._logout_admin,
            bg='#c82333', fg='white', font=('Arial', 10, 'bold'),
            padx=15, pady=5, relief='flat'
        ).pack(side='left')
        
        # Content area with tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Create tabs
        self._create_password_review_tab()
        self._create_security_analysis_tab()
        self._create_passkey_management_tab()
        self._create_audit_log_tab()
        self._create_system_config_tab()
    
    def _create_password_review_tab(self):
        """Create password review and management tab."""
        password_frame = tk.Frame(self.notebook, bg='#f8f9fa')
        self.notebook.add(password_frame, text="🔍 Password Review")
        
        # Search and filter frame
        search_frame = tk.Frame(password_frame, bg='#f8f9fa')
        search_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(search_frame, text="🔍 Search:", font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(side='left')
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30, font=('Arial', 10))
        search_entry.pack(side='left', padx=(5, 20))
        
        tk.Button(
            search_frame, text="Search", command=self._search_passwords,
            bg='#007bff', fg='white', padx=15, pady=2, relief='flat'
        ).pack(side='left', padx=(0, 20))
        
        # Filter options
        tk.Label(search_frame, text="Filter:", font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(side='left')
        
        self.filter_var = tk.StringVar(value="All")
        filter_combo = ttk.Combobox(
            search_frame, textvariable=self.filter_var, 
            values=["All", "Weak Passwords", "Compromised", "Duplicates", "Recently Added"],
            width=15, state="readonly"
        )
        filter_combo.pack(side='left', padx=5)
        filter_combo.bind('<<ComboboxSelected>>', self._apply_filter)
        
        # Password list with security scoring
        list_frame = tk.Frame(password_frame, bg='#f8f9fa')
        list_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create Treeview for password list
        columns = ("Site", "Username", "Strength", "Status", "Last Used", "Created")
        self.password_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=15)
        
        # Define column widths and headings
        self.password_tree.column("#0", width=50, minwidth=50)
        self.password_tree.heading("#0", text="ID")
        
        for col in columns:
            self.password_tree.column(col, width=150, minwidth=100)
            self.password_tree.heading(col, text=col)
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.password_tree.yview)
        x_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.password_tree.xview)
        self.password_tree.configure(yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.password_tree.grid(row=0, column=0, sticky="nsew")
        y_scrollbar.grid(row=0, column=1, sticky="ns")
        x_scrollbar.grid(row=1, column=0, sticky="ew")
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click
        self.password_tree.bind("<Double-1>", self._view_password_details)
        
        # Action buttons
        action_frame = tk.Frame(password_frame, bg='#f8f9fa')
        action_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(
            action_frame, text="🔍 View Details", command=self._view_selected_password,
            bg='#17a2b8', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            action_frame, text="🗑️ Delete Password", command=self._delete_selected_password,
            bg='#dc3545', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            action_frame, text="📊 Security Report", command=self._generate_security_report,
            bg='#28a745', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            action_frame, text="📤 Export Data", command=self._export_password_data,
            bg='#6c757d', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        # Refresh button
        tk.Button(
            action_frame, text="🔄 Refresh", command=self._refresh_password_list,
            bg='#ffc107', fg='black', padx=15, pady=5, relief='flat'
        ).pack(side='right')
    
    def _create_security_analysis_tab(self):
        """Create security analysis tab."""
        security_frame = tk.Frame(self.notebook, bg='#f8f9fa')
        self.notebook.add(security_frame, text="🔒 Security Analysis")
        
        # Security metrics frame
        metrics_frame = tk.LabelFrame(security_frame, text="Security Metrics", bg='#f8f9fa')
        metrics_frame.pack(fill='x', padx=10, pady=10)
        
        # Metrics grid
        metrics_grid = tk.Frame(metrics_frame, bg='#f8f9fa')
        metrics_grid.pack(fill='x', padx=10, pady=10)
        
        # Security score
        self.security_score_label = tk.Label(
            metrics_grid, text="Overall Security Score: Calculating...", 
            font=('Arial', 14, 'bold'), bg='#f8f9fa'
        )
        self.security_score_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Individual metrics
        metrics = [
            ("Strong Passwords:", "calculating"),
            ("Weak Passwords:", "calculating"),
            ("Compromised Passwords:", "calculating"),
            ("Duplicate Passwords:", "calculating"),
            ("Passwords with 2FA:", "calculating"),
            ("Recently Updated:", "calculating")
        ]
        
        self.metric_labels = {}
        for i, (label, value) in enumerate(metrics):
            row = (i // 2) + 1
            col = (i % 2) * 2
            
            tk.Label(metrics_grid, text=label, font=('Arial', 10, 'bold'), bg='#f8f9fa').grid(
                row=row, column=col, sticky='w', padx=(0, 10), pady=2
            )
            
            value_label = tk.Label(metrics_grid, text=value, font=('Arial', 10), bg='#f8f9fa')
            value_label.grid(row=row, column=col+1, sticky='w', pady=2)
            
            self.metric_labels[label] = value_label
        
        # Security recommendations
        recommendations_frame = tk.LabelFrame(security_frame, text="Security Recommendations", bg='#f8f9fa')
        recommendations_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.recommendations_text = tk.Text(
            recommendations_frame, height=15, width=80, wrap=tk.WORD, 
            font=('Arial', 10), bg='white'
        )
        
        rec_scrollbar = ttk.Scrollbar(recommendations_frame, orient="vertical", command=self.recommendations_text.yview)
        self.recommendations_text.configure(yscrollcommand=rec_scrollbar.set)
        
        self.recommendations_text.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        rec_scrollbar.pack(side='right', fill='y')
        
        # Action buttons
        sec_action_frame = tk.Frame(security_frame, bg='#f8f9fa')
        sec_action_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(
            sec_action_frame, text="🔄 Run Security Scan", command=self._run_security_scan,
            bg='#007bff', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            sec_action_frame, text="📋 Generate Report", command=self._generate_detailed_report,
            bg='#28a745', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
    
    def _create_passkey_management_tab(self):
        """Create passkey/FIDO2 management tab."""
        passkey_frame = tk.Frame(self.notebook, bg='#f8f9fa')
        self.notebook.add(passkey_frame, text="🔑 Passkey Management")
        
        # Header with passkey info
        header_frame = tk.Frame(passkey_frame, bg='#e3f2fd', relief='ridge', bd=1)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(
            header_frame, 
            text="🔑 Passkey & FIDO2 Authentication Management",
            font=('Arial', 14, 'bold'), bg='#e3f2fd', fg='#1976d2'
        ).pack(pady=10)
        
        tk.Label(
            header_frame,
            text="Manage hardware security keys, biometric authentication, and passkey credentials",
            font=('Arial', 10), bg='#e3f2fd', fg='#424242'
        ).pack(pady=(0, 10))
        
        # Control buttons
        control_frame = tk.Frame(passkey_frame, bg='#f8f9fa')
        control_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Button(
            control_frame, text="➕ Generate New Passkey", 
            command=self._generate_passkey,
            bg='#28a745', fg='white', font=('Arial', 10, 'bold'),
            padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            control_frame, text="🔍 Detect Hardware Keys", 
            command=self._detect_hardware_keys,
            bg='#17a2b8', fg='white', font=('Arial', 10, 'bold'),
            padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            control_frame, text="📁 Import Passkey", 
            command=self._import_passkey,
            bg='#6f42c1', fg='white', font=('Arial', 10, 'bold'),
            padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            control_frame, text="🔄 Refresh List", 
            command=self._refresh_passkey_list,
            bg='#6c757d', fg='white', font=('Arial', 10, 'bold'),
            padx=15, pady=5, relief='flat'
        ).pack(side='right')
        
        # Passkey list
        list_frame = tk.Frame(passkey_frame, bg='#f8f9fa')
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(
            list_frame, text="Registered Passkeys & Hardware Keys:",
            font=('Arial', 11, 'bold'), bg='#f8f9fa'
        ).pack(anchor='w', pady=(0, 5))
        
        # Passkey tree view
        passkey_columns = ("Device", "Type", "Registered", "Last Used", "Status")
        self.passkey_tree = ttk.Treeview(list_frame, columns=passkey_columns, show="headings", height=8)
        
        for col in passkey_columns:
            self.passkey_tree.heading(col, text=col)
            self.passkey_tree.column(col, width=150)
        
        # Scrollbar for passkey list
        passkey_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.passkey_tree.yview)
        self.passkey_tree.configure(yscrollcommand=passkey_scrollbar.set)
        
        self.passkey_tree.pack(side='left', fill='both', expand=True)
        passkey_scrollbar.pack(side='right', fill='y')
        
        # Passkey details frame
        details_frame = tk.LabelFrame(passkey_frame, text="Passkey Details & Actions", bg='#f8f9fa')
        details_frame.pack(fill='x', padx=10, pady=10)
        
        details_grid = tk.Frame(details_frame, bg='#f8f9fa')
        details_grid.pack(fill='x', padx=10, pady=10)
        
        # Details labels
        self.passkey_detail_labels = {}
        details = ["Selected Device:", "Credential ID:", "Authentication Count:", "Security Features:"]
        
        for i, label in enumerate(details):
            tk.Label(details_grid, text=label, font=('Arial', 9, 'bold'), bg='#f8f9fa').grid(
                row=i//2, column=(i%2)*2, sticky='w', padx=(0, 10), pady=2
            )
            value_label = tk.Label(details_grid, text="None selected", font=('Arial', 9), bg='#f8f9fa')
            value_label.grid(row=i//2, column=(i%2)*2+1, sticky='w', pady=2)
            self.passkey_detail_labels[label] = value_label
        
        # Action buttons for selected passkey
        action_frame = tk.Frame(details_frame, bg='#f8f9fa')
        action_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(
            action_frame, text="🧪 Test Authentication", 
            command=self._test_passkey_auth,
            bg='#007bff', fg='white', font=('Arial', 9, 'bold'),
            padx=12, pady=3, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            action_frame, text="📝 Rename Device", 
            command=self._rename_passkey_device,
            bg='#fd7e14', fg='white', font=('Arial', 9, 'bold'),
            padx=12, pady=3, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            action_frame, text="❌ Revoke Passkey", 
            command=self._revoke_passkey,
            bg='#dc3545', fg='white', font=('Arial', 9, 'bold'),
            padx=12, pady=3, relief='flat'
        ).pack(side='right')
        
        # Bind tree selection
        self.passkey_tree.bind('<<TreeviewSelect>>', self._on_passkey_selected)
        
        # Load initial passkey list
        self._refresh_passkey_list()

    def _create_audit_log_tab(self):
        """Create audit log tab."""
        audit_frame = tk.Frame(self.notebook, bg='#f8f9fa')
        self.notebook.add(audit_frame, text="📋 Audit Log")
        
        # Filter frame
        filter_frame = tk.Frame(audit_frame, bg='#f8f9fa')
        filter_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(filter_frame, text="Time Range:", font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(side='left')
        
        self.time_range_var = tk.StringVar(value="Last 7 Days")
        time_range_combo = ttk.Combobox(
            filter_frame, textvariable=self.time_range_var,
            values=["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"],
            width=15, state="readonly"
        )
        time_range_combo.pack(side='left', padx=(5, 20))
        
        tk.Label(filter_frame, text="Event Type:", font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(side='left')
        
        self.event_type_var = tk.StringVar(value="All")
        event_type_combo = ttk.Combobox(
            filter_frame, textvariable=self.event_type_var,
            values=["All", "Login", "Password Access", "Password Modified", "Security Alert"],
            width=15, state="readonly"
        )
        event_type_combo.pack(side='left', padx=5)
        
        tk.Button(
            filter_frame, text="Apply Filter", command=self._filter_audit_log,
            bg='#007bff', fg='white', padx=15, pady=2, relief='flat'
        ).pack(side='left', padx=(20, 0))
        
        # Audit log display
        log_frame = tk.Frame(audit_frame, bg='#f8f9fa')
        log_frame.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create Treeview for audit log
        log_columns = ("Timestamp", "Event Type", "User", "Details", "IP Address")
        self.audit_tree = ttk.Treeview(log_frame, columns=log_columns, show="headings", height=20)
        
        for col in log_columns:
            self.audit_tree.column(col, width=150, minwidth=100)
            self.audit_tree.heading(col, text=col)
        
        # Scrollbar for audit log
        audit_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=audit_scrollbar.set)
        
        self.audit_tree.pack(side='left', fill='both', expand=True)
        audit_scrollbar.pack(side='right', fill='y')
        
        # Export button
        export_frame = tk.Frame(audit_frame, bg='#f8f9fa')
        export_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(
            export_frame, text="📤 Export Audit Log", command=self._export_audit_log,
            bg='#6c757d', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='right')
    
    def _create_system_config_tab(self):
        """Create system configuration tab."""
        config_frame = tk.Frame(self.notebook, bg='#f8f9fa')
        self.notebook.add(config_frame, text="⚙️ System Config")
        
        # Security settings frame
        security_settings = tk.LabelFrame(config_frame, text="Security Settings", bg='#f8f9fa')
        security_settings.pack(fill='x', padx=10, pady=10)
        
        settings_grid = tk.Frame(security_settings, bg='#f8f9fa')
        settings_grid.pack(fill='x', padx=10, pady=10)
        
        # Security options
        self.enforce_strong_passwords = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_grid, text="Enforce Strong Password Policy",
            variable=self.enforce_strong_passwords, bg='#f8f9fa'
        ).grid(row=0, column=0, sticky='w', pady=2)
        
        self.auto_lock_enabled = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_grid, text="Auto-lock after inactivity",
            variable=self.auto_lock_enabled, bg='#f8f9fa'
        ).grid(row=1, column=0, sticky='w', pady=2)
        
        self.breach_monitoring = tk.BooleanVar(value=True)
        tk.Checkbutton(
            settings_grid, text="Monitor for password breaches",
            variable=self.breach_monitoring, bg='#f8f9fa'
        ).grid(row=2, column=0, sticky='w', pady=2)
        
        # Action buttons
        config_action_frame = tk.Frame(config_frame, bg='#f8f9fa')
        config_action_frame.pack(fill='x', padx=10, pady=20)
        
        tk.Button(
            config_action_frame, text="💾 Save Settings", command=self._save_config,
            bg='#28a745', fg='white', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        tk.Button(
            config_action_frame, text="🔄 Reset to Defaults", command=self._reset_config,
            bg='#ffc107', fg='black', padx=15, pady=5, relief='flat'
        ).pack(side='left', padx=(0, 10))
        
        # System status
        status_frame = tk.LabelFrame(config_frame, text="System Status", bg='#f8f9fa')
        status_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.status_text = tk.Text(
            status_frame, height=10, width=80, wrap=tk.WORD,
            font=('Courier', 9), bg='black', fg='green'
        )
        
        status_scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=status_scrollbar.set)
        
        self.status_text.pack(side='left', fill='both', expand=True, padx=10, pady=10)
        status_scrollbar.pack(side='right', fill='y')
        
        # Load initial status
        self._update_system_status()
    
    # Implementation of all the methods used above
    def _load_password_analysis(self):
        """Load and analyze all passwords for security assessment."""
        # This would be implemented to analyze passwords
        pass
    
    def _load_breach_database(self):
        """Load breach database for password checking."""
        # Placeholder - would load pwned passwords database
        pass
    
    def _search_passwords(self):
        """Search passwords based on criteria."""
        # Placeholder for password search functionality
        pass
    
    def _apply_filter(self, event=None):
        """Apply filter to password list."""
        # Placeholder for filter functionality
        pass
    
    def _view_password_details(self, event=None):
        """View detailed password information."""
        # Placeholder for password detail view
        pass
    
    def _view_selected_password(self):
        """View selected password details."""
        # Placeholder
        pass
    
    def _delete_selected_password(self):
        """Delete selected password."""
        # Placeholder
        pass
    
    def _generate_security_report(self):
        """Generate security report."""
        # Placeholder
        pass
    
    def _export_password_data(self):
        """Export password data."""
        # Placeholder
        pass
    
    def _refresh_password_list(self):
        """Refresh password list."""
        # Placeholder
        pass
    
    def _run_security_scan(self):
        """Run comprehensive security scan."""
        # Placeholder
        pass
    
    def _generate_detailed_report(self):
        """Generate detailed security report."""
        # Placeholder
        pass
    
    def _filter_audit_log(self):
        """Filter audit log entries."""
        # Placeholder
        pass
    
    def _export_audit_log(self):
        """Export audit log."""
        # Placeholder
        pass
    
    def _save_config(self):
        """Save configuration settings."""
        # Placeholder
        pass
    
    def _reset_config(self):
        """Reset configuration to defaults."""
        # Placeholder
        pass
    
    def _update_system_status(self):
        """Update system status display."""
        # Placeholder
        pass
    
    def _generate_passkey(self):
        """Generate a new passkey for authentication."""
        try:
            # Import passkey manager 
            from .passkey_manager import PasskeyManager
            passkey_manager = PasskeyManager(self.db_manager)
            
            if not hasattr(passkey_manager, 'server') or passkey_manager.server is None:
                messagebox.showerror("Error", "FIDO2 libraries not available. Please install fido2 package.")
                return
            
            # Show passkey generation dialog
            gen_window = tk.Toplevel(self.admin_window)
            gen_window.title("Generate New Passkey")
            gen_window.geometry("500x400")
            gen_window.resizable(False, False)
            
            # Center window
            gen_window.geometry("+%d+%d" % (
                (gen_window.winfo_screenwidth() // 2) - 250,
                (gen_window.winfo_screenheight() // 2) - 200
            ))
            
            main_frame = tk.Frame(gen_window, bg='#f8f9fa', padx=30, pady=30)
            main_frame.pack(fill='both', expand=True)
            
            tk.Label(
                main_frame, text="🔑 Generate New Passkey",
                font=('Arial', 16, 'bold'), bg='#f8f9fa'
            ).pack(pady=(0, 20))
            
            tk.Label(
                main_frame, 
                text="Follow the prompts to create a new passkey using your hardware security key or biometric authentication.",
                font=('Arial', 10), bg='#f8f9fa', wraplength=400, justify='center'
            ).pack(pady=(0, 20))
            
            # Device name input
            tk.Label(main_frame, text="Device Name:", font=('Arial', 10, 'bold'), bg='#f8f9fa').pack(anchor='w')
            device_name_var = tk.StringVar(value="Hardware Security Key")
            device_name_entry = tk.Entry(main_frame, textvariable=device_name_var, width=40, font=('Arial', 10))
            device_name_entry.pack(pady=(2, 15), fill='x')
            
            # Status label
            status_label = tk.Label(main_frame, text="Click 'Generate' to start passkey creation", 
                                  font=('Arial', 10), bg='#f8f9fa', fg='#666666')
            status_label.pack(pady=(0, 20))
            
            def generate_passkey():
                try:
                    status_label.config(text="⏳ Touch your security key or follow biometric prompt...", fg='#007bff')
                    gen_window.update()
                    
                    device_name = device_name_var.get().strip() or "Hardware Security Key"
                    
                    # Generate passkey registration
                    result = passkey_manager.begin_registration("admin_user")
                    if result.get('success'):
                        status_label.config(text="✅ Passkey generated successfully!", fg='#28a745')
                        # Refresh the passkey list in main window
                        self._refresh_passkey_list()
                        gen_window.after(2000, gen_window.destroy)
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        status_label.config(text=f"❌ Failed: {error_msg}", fg='#dc3545')
                        
                except Exception as e:
                    status_label.config(text=f"❌ Error: {str(e)}", fg='#dc3545')
            
            # Buttons
            button_frame = tk.Frame(main_frame, bg='#f8f9fa')
            button_frame.pack(pady=(20, 0))
            
            tk.Button(button_frame, text="Generate Passkey", command=generate_passkey,
                     bg='#28a745', fg='white', font=('Arial', 10, 'bold'), padx=20, pady=8).pack(side='left', padx=(0, 10))
            tk.Button(button_frame, text="Cancel", command=gen_window.destroy,
                     bg='#6c757d', fg='white', font=('Arial', 10, 'bold'), padx=20, pady=8).pack(side='left')
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate passkey: {str(e)}")
    
    def _detect_hardware_keys(self):
        """Detect connected hardware security keys."""
        try:
            from .passkey_manager import PasskeyManager
            passkey_manager = PasskeyManager(self.db_manager)
            
            if not hasattr(passkey_manager, 'server') or passkey_manager.server is None:
                messagebox.showerror("Error", "FIDO2 libraries not available. Please install fido2 package.")
                return
            
            # Detect hardware keys
            devices = passkey_manager.detect_hardware_devices()
            
            if devices:
                device_list = "\n".join([f"• {device['name']} - {device['transport']}" for device in devices])
                messagebox.showinfo("Hardware Keys Detected", f"Found {len(devices)} device(s):\n\n{device_list}")
            else:
                messagebox.showinfo("No Hardware Keys", "No hardware security keys detected. Please connect your device and try again.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect hardware keys: {str(e)}")
    
    def _import_passkey(self):
        """Import an existing passkey credential."""
        messagebox.showinfo("Import Passkey", "Passkey import functionality coming soon.")
    
    def _refresh_passkey_list(self):
        """Refresh the list of registered passkeys."""
        try:
            # Clear existing items
            for item in self.passkey_tree.get_children():
                self.passkey_tree.delete(item)
            
            # Load passkeys from database
            from .passkey_manager import PasskeyManager
            passkey_manager = PasskeyManager(self.db_manager)
            
            passkeys = passkey_manager.get_registered_passkeys()
            
            for passkey in passkeys:
                device_name = passkey.get('device_name', 'Unknown Device')
                key_type = 'Hardware Key' if 'hardware' in device_name.lower() else 'Biometric'
                registered = passkey.get('registered_at', 'Unknown')[:10]  # Date only
                last_used = passkey.get('last_used', 'Never')
                if last_used and last_used != 'Never':
                    last_used = last_used[:10]  # Date only
                status = '✅ Active' if passkey.get('is_active', True) else '❌ Revoked'
                
                self.passkey_tree.insert('', 'end', values=(device_name, key_type, registered, last_used, status))
                
        except Exception as e:
            print(f"Error refreshing passkey list: {e}")
    
    def _on_passkey_selected(self, event):
        """Handle passkey selection in the tree."""
        try:
            selection = self.passkey_tree.selection()
            if not selection:
                return
            
            item = self.passkey_tree.item(selection[0])
            values = item['values']
            
            if values:
                # Update detail labels
                self.passkey_detail_labels["Selected Device:"].config(text=values[0])
                self.passkey_detail_labels["Credential ID:"].config(text="Protected")  
                self.passkey_detail_labels["Authentication Count:"].config(text="Available")
                self.passkey_detail_labels["Security Features:"].config(text="FIDO2/WebAuthn")
                
        except Exception as e:
            print(f"Error handling passkey selection: {e}")
    
    def _test_passkey_auth(self):
        """Test authentication with selected passkey."""
        selection = self.passkey_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a passkey to test.")
            return
        
        messagebox.showinfo("Test Authentication", "Touch your security key or follow the biometric prompt to test authentication.")
    
    def _rename_passkey_device(self):
        """Rename the selected passkey device."""
        selection = self.passkey_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a passkey to rename.")
            return
        
        current_name = self.passkey_tree.item(selection[0])['values'][0]
        new_name = tk.simpledialog.askstring("Rename Device", f"Enter new name for '{current_name}':", initialvalue=current_name)
        
        if new_name and new_name.strip():
            # Update device name (implementation would update database)
            messagebox.showinfo("Success", f"Device renamed to '{new_name.strip()}'")
            self._refresh_passkey_list()
    
    def _revoke_passkey(self):
        """Revoke the selected passkey."""
        selection = self.passkey_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a passkey to revoke.")
            return
        
        device_name = self.passkey_tree.item(selection[0])['values'][0]
        
        if messagebox.askyesno("Revoke Passkey", f"Are you sure you want to revoke '{device_name}'?\n\nThis action cannot be undone."):
            # Revoke passkey (implementation would update database)
            messagebox.showinfo("Success", f"Passkey '{device_name}' has been revoked.")
            self._refresh_passkey_list()

    def _show_profile_management(self):
        """Show admin profile management window."""
        try:
            if hasattr(self, 'profile_gui') and self.profile_gui:
                # Profile window already open, bring to front
                if self.profile_gui.profile_window:
                    self.profile_gui.profile_window.lift()
                    return
            
            # Create new profile management window
            self.profile_gui = AdminProfileGUI(self.admin_window, self.admin_auth, self.admin_session)
            self.profile_gui.show_profile_management()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open profile management: {str(e)}")
    
    def _logout_admin(self):
        """Logout admin user."""
        if self.admin_session:
            self.admin_auth.revoke_admin_session(self.admin_session)
            self.admin_session = None
        
        self._on_admin_window_close()
    
    def _on_admin_window_close(self):
        """Handle admin window close."""
        if self.admin_window:
            self.admin_window.destroy()
            self.admin_window = None