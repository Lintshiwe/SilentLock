"""
Admin Profile Management GUI for SilentLock.
Provides interface for managing admin profile and 2FA settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import base64
import io
import os
from typing import Dict, Optional


class AdminProfileGUI:
    """GUI for admin profile management and 2FA configuration."""
    
    def __init__(self, parent, admin_auth, session_token):
        self.parent = parent
        self.admin_auth = admin_auth
        self.session_token = session_token
        self.profile_window = None
        self.profile_data = {}
        
    def show_profile_management(self):
        """Show the admin profile management window."""
        if self.profile_window:
            self.profile_window.lift()
            return
            
        self.profile_window = tk.Toplevel(self.parent)
        self.profile_window.title("Admin Profile Management")
        self.profile_window.geometry("800x700")
        self.profile_window.resizable(True, True)
        self.profile_window.transient(self.parent)
        
        # Center window
        self.profile_window.update_idletasks()
        x = (self.profile_window.winfo_screenwidth() // 2) - (self.profile_window.winfo_width() // 2)
        y = (self.profile_window.winfo_screenheight() // 2) - (self.profile_window.winfo_height() // 2)
        self.profile_window.geometry(f"+{x}+{y}")
        
        # Load profile data
        self._load_profile_data()
        
        # Create interface
        self._create_profile_interface()
        
        # Handle window close
        self.profile_window.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _load_profile_data(self):
        """Load current profile data."""
        try:
            result = self.admin_auth.get_admin_profile(self.session_token)
            if result['success']:
                self.profile_data = result['profile']
            else:
                messagebox.showerror("Error", f"Failed to load profile: {result['error']}")
                self.profile_data = {}
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load profile: {str(e)}")
            self.profile_data = {}
    
    def _create_profile_interface(self):
        """Create the profile management interface."""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.profile_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Profile tab
        profile_frame = ttk.Frame(notebook, padding="20")
        notebook.add(profile_frame, text="Profile")
        self._create_profile_tab(profile_frame)
        
        # 2FA Settings tab
        security_frame = ttk.Frame(notebook, padding="20")
        notebook.add(security_frame, text="Security & 2FA")
        self._create_security_tab(security_frame)
        
        # Email Configuration tab
        email_frame = ttk.Frame(notebook, padding="20")
        notebook.add(email_frame, text="Email Settings")
        self._create_email_tab(email_frame)
        
        # Activity tab
        activity_frame = ttk.Frame(notebook, padding="20")
        notebook.add(activity_frame, text="Activity Log")
        self._create_activity_tab(activity_frame)
    
    def _create_profile_tab(self, parent):
        """Create the profile information tab."""
        # Header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text="👤 Admin Profile", 
                 font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        
        # Profile picture section
        pic_frame = ttk.LabelFrame(parent, text="Profile Picture", padding="10")
        pic_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.profile_pic_label = ttk.Label(pic_frame, text="📷", font=('Arial', 48))
        self.profile_pic_label.pack(side=tk.LEFT, padx=(0, 15))
        
        pic_buttons_frame = ttk.Frame(pic_frame)
        pic_buttons_frame.pack(side=tk.LEFT, fill=tk.BOTH)
        
        ttk.Button(pic_buttons_frame, text="Upload Picture", 
                  command=self._upload_profile_picture).pack(anchor=tk.W, pady=2)
        ttk.Button(pic_buttons_frame, text="Remove Picture", 
                  command=self._remove_profile_picture).pack(anchor=tk.W, pady=2)
        
        # Basic information
        info_frame = ttk.LabelFrame(parent, text="Basic Information", padding="15")
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Create two columns
        left_col = ttk.Frame(info_frame)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        right_col = ttk.Frame(info_frame)
        right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # Left column fields
        ttk.Label(left_col, text="Display Name:").pack(anchor=tk.W, pady=2)
        self.display_name_var = tk.StringVar(value=self.profile_data.get('display_name', ''))
        ttk.Entry(left_col, textvariable=self.display_name_var, width=30).pack(fill=tk.X, pady=(2, 10))
        
        ttk.Label(left_col, text="Email Address:").pack(anchor=tk.W, pady=2)
        self.email_var = tk.StringVar(value=self.profile_data.get('email', ''))
        ttk.Entry(left_col, textvariable=self.email_var, width=30).pack(fill=tk.X, pady=(2, 10))
        
        ttk.Label(left_col, text="Admin ID:").pack(anchor=tk.W, pady=2)
        admin_id_entry = ttk.Entry(left_col, width=30)
        admin_id_entry.pack(fill=tk.X, pady=(2, 10))
        admin_id_entry.insert(0, self.profile_data.get('admin_id', ''))
        admin_id_entry.config(state='readonly')
        
        # Right column fields
        ttk.Label(right_col, text="Phone Number:").pack(anchor=tk.W, pady=2)
        self.phone_var = tk.StringVar(value=self.profile_data.get('phone_number', ''))
        ttk.Entry(right_col, textvariable=self.phone_var, width=30).pack(fill=tk.X, pady=(2, 10))
        
        ttk.Label(right_col, text="Created:").pack(anchor=tk.W, pady=2)
        created_entry = ttk.Entry(right_col, width=30)
        created_entry.pack(fill=tk.X, pady=(2, 10))
        created_entry.insert(0, self.profile_data.get('created_at', ''))
        created_entry.config(state='readonly')
        
        ttk.Label(right_col, text="Last Login:").pack(anchor=tk.W, pady=2)
        login_entry = ttk.Entry(right_col, width=30)
        login_entry.pack(fill=tk.X, pady=(2, 10))
        login_entry.insert(0, self.profile_data.get('last_login', ''))
        login_entry.config(state='readonly')
        
        # Security question
        security_frame = ttk.LabelFrame(parent, text="Security Question", padding="15")
        security_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(security_frame, text="Security Question:").pack(anchor=tk.W, pady=2)
        self.security_question_var = tk.StringVar(value=self.profile_data.get('security_question', ''))
        ttk.Entry(security_frame, textvariable=self.security_question_var).pack(fill=tk.X, pady=(2, 10))
        
        ttk.Label(security_frame, text="Security Answer:").pack(anchor=tk.W, pady=2)
        self.security_answer_var = tk.StringVar()
        ttk.Entry(security_frame, textvariable=self.security_answer_var, show='*').pack(fill=tk.X, pady=(2, 10))
        
        # Save button
        ttk.Button(parent, text="💾 Save Profile Changes", 
                  command=self._save_profile_changes).pack(pady=20)
    
    def _create_security_tab(self, parent):
        """Create the security and 2FA settings tab."""
        # Header
        ttk.Label(parent, text="🔐 Security & Two-Factor Authentication", 
                 font=('Arial', 16, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
        # Current 2FA status
        status_frame = ttk.LabelFrame(parent, text="Current 2FA Status", padding="15")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        twofa_enabled = self.profile_data.get('2fa_enabled', False)
        email_2fa_enabled = self.profile_data.get('email_2fa_enabled', False)
        twofa_method = self.profile_data.get('2fa_method', 'none')
        
        status_text = ""
        if twofa_enabled:
            if twofa_method == 'totp':
                status_text = "✅ TOTP Authentication Enabled"
            elif twofa_method == 'email':
                status_text = "✅ Email OTP Authentication Enabled"
            elif twofa_method == 'both':
                status_text = "✅ Both TOTP and Email OTP Enabled"
        else:
            status_text = "❌ Two-Factor Authentication Disabled"
        
        ttk.Label(status_frame, text=status_text, font=('Arial', 12)).pack(anchor=tk.W)
        
        # Email 2FA configuration
        email2fa_frame = ttk.LabelFrame(parent, text="Email-Based 2FA", padding="15")
        email2fa_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.email_2fa_var = tk.BooleanVar(value=email_2fa_enabled)
        ttk.Checkbutton(email2fa_frame, text="Enable Email-Based 2FA", 
                       variable=self.email_2fa_var).pack(anchor=tk.W, pady=5)
        
        ttk.Label(email2fa_frame, text="📧 Email OTP codes will be sent to your registered email address", 
                 font=('Arial', 9), foreground='gray').pack(anchor=tk.W, pady=5)
        
        # Test email button
        email_test_frame = ttk.Frame(email2fa_frame)
        email_test_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(email_test_frame, text="📨 Send Test Email", 
                  command=self._send_test_email).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(email_test_frame, text="⚙️ Configure Email Settings", 
                  command=self._show_email_config).pack(side=tk.LEFT)
        
        # TOTP configuration
        totp_frame = ttk.LabelFrame(parent, text="TOTP Authentication", padding="15")
        totp_frame.pack(fill=tk.X, pady=(0, 15))
        
        has_totp = bool(self.profile_data.get('totp_secret'))
        ttk.Label(totp_frame, text=f"TOTP Status: {'Configured' if has_totp else 'Not Configured'}", 
                 font=('Arial', 10, 'bold')).pack(anchor=tk.W, pady=5)
        
        totp_buttons_frame = ttk.Frame(totp_frame)
        totp_buttons_frame.pack(fill=tk.X, pady=10)
        
        if has_totp:
            ttk.Button(totp_buttons_frame, text="📱 Show QR Code", 
                      command=self._show_totp_qr).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(totp_buttons_frame, text="🔄 Regenerate TOTP", 
                      command=self._regenerate_totp).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(totp_buttons_frame, text="❌ Disable TOTP", 
                      command=self._disable_totp).pack(side=tk.LEFT)
        else:
            ttk.Button(totp_buttons_frame, text="✅ Setup TOTP", 
                      command=self._setup_totp).pack(side=tk.LEFT)
        
        # Save security settings button
        ttk.Button(parent, text="🔒 Save Security Settings", 
                  command=self._save_security_settings).pack(pady=20)
    
    def _create_email_tab(self, parent):
        """Create the email configuration tab."""
        # Header
        ttk.Label(parent, text="📧 Email Configuration", 
                 font=('Arial', 16, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
        # Email service status
        status_frame = ttk.LabelFrame(parent, text="Email Service Status", padding="15")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        email_configured = self.profile_data.get('email_service_configured', False)
        smtp_status = self.profile_data.get('smtp_config_status', {})
        
        status_text = "✅ Email Service Configured" if email_configured else "❌ Email Service Not Configured"
        ttk.Label(status_frame, text=status_text, font=('Arial', 12)).pack(anchor=tk.W, pady=5)
        
        if smtp_status:
            ttk.Label(status_frame, text=f"SMTP Server: {smtp_status.get('smtp_server', 'Not set')}", 
                     font=('Arial', 10)).pack(anchor=tk.W, pady=2)
            ttk.Label(status_frame, text=f"From Email: {smtp_status.get('from_email', 'Not set')}", 
                     font=('Arial', 10)).pack(anchor=tk.W, pady=2)
        
        # SMTP Configuration
        smtp_frame = ttk.LabelFrame(parent, text="SMTP Configuration", padding="15")
        smtp_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Create form fields
        form_frame = ttk.Frame(smtp_frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # SMTP Server
        ttk.Label(form_frame, text="SMTP Server:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.smtp_server_var = tk.StringVar(value=smtp_status.get('smtp_server', ''))
        ttk.Entry(form_frame, textvariable=self.smtp_server_var, width=40).grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        # SMTP Port
        ttk.Label(form_frame, text="SMTP Port:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.smtp_port_var = tk.StringVar(value=str(smtp_status.get('smtp_port', 587)))
        ttk.Entry(form_frame, textvariable=self.smtp_port_var, width=40).grid(row=1, column=1, sticky=tk.W+tk.E, pady=5)
        
        # From Email
        ttk.Label(form_frame, text="From Email:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.from_email_var = tk.StringVar(value=smtp_status.get('from_email', ''))
        ttk.Entry(form_frame, textvariable=self.from_email_var, width=40).grid(row=2, column=1, sticky=tk.W+tk.E, pady=5)
        
        # From Password/App Password
        ttk.Label(form_frame, text="App Password:").grid(row=3, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.from_password_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.from_password_var, show='*', width=40).grid(row=3, column=1, sticky=tk.W+tk.E, pady=5)
        
        # Use TLS
        self.use_tls_var = tk.BooleanVar(value=smtp_status.get('use_tls', True))
        ttk.Checkbutton(form_frame, text="Use TLS/STARTTLS", variable=self.use_tls_var).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(smtp_frame)
        button_frame.pack(fill=tk.X, pady=15)
        
        ttk.Button(button_frame, text="🧪 Test Configuration", 
                  command=self._test_email_config).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="💾 Save Email Settings", 
                  command=self._save_email_config).pack(side=tk.LEFT)
    
    def _create_activity_tab(self, parent):
        """Create the activity log tab."""
        # Header
        ttk.Label(parent, text="📊 Recent Activity", 
                 font=('Arial', 16, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
        # Activity log
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create treeview for activity log
        columns = ('time', 'activity', 'description')
        self.activity_tree = ttk.Treeview(log_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.activity_tree.heading('time', text='Time')
        self.activity_tree.heading('activity', text='Activity')
        self.activity_tree.heading('description', text='Description')
        
        self.activity_tree.column('time', width=150, anchor=tk.W)
        self.activity_tree.column('activity', width=150, anchor=tk.W)
        self.activity_tree.column('description', width=300, anchor=tk.W)
        
        # Scrollbar for treeview
        activity_scroll = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=activity_scroll.set)
        
        # Pack treeview and scrollbar
        self.activity_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        activity_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate activity log
        self._populate_activity_log()
        
        # Statistics
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding="15")
        stats_frame.pack(fill=tk.X, pady=(10, 0))
        
        login_count = self.profile_data.get('login_count', 0)
        ttk.Label(stats_frame, text=f"Total Logins: {login_count}", font=('Arial', 10)).pack(anchor=tk.W, pady=2)
        
        session_count = len(self.profile_data.get('active_sessions', []))
        ttk.Label(stats_frame, text=f"Active Sessions: {session_count}", font=('Arial', 10)).pack(anchor=tk.W, pady=2)
    
    def _populate_activity_log(self):
        """Populate the activity log treeview."""
        # Clear existing items
        for item in self.activity_tree.get_children():
            self.activity_tree.delete(item)
        
        # Add activity entries
        activities = self.profile_data.get('recent_activity', [])
        for activity in activities:
            self.activity_tree.insert('', 'end', values=(
                activity.get('timestamp', ''),
                activity.get('activity_type', ''),
                activity.get('description', '')
            ))
    
    def _upload_profile_picture(self):
        """Upload a new profile picture."""
        file_path = filedialog.askopenfilename(
            title="Select Profile Picture",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )
        
        if file_path:
            try:
                # TODO: Implement profile picture upload
                messagebox.showinfo("Info", "Profile picture upload will be implemented in a future version.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload picture: {str(e)}")
    
    def _remove_profile_picture(self):
        """Remove the current profile picture."""
        try:
            # TODO: Implement profile picture removal
            messagebox.showinfo("Info", "Profile picture removal will be implemented in a future version.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove picture: {str(e)}")
    
    def _save_profile_changes(self):
        """Save profile changes."""
        try:
            updates = {
                'display_name': self.display_name_var.get(),
                'email': self.email_var.get(),
                'phone_number': self.phone_var.get()
            }
            
            if self.security_question_var.get():
                updates['security_question'] = self.security_question_var.get()
            
            if self.security_answer_var.get():
                updates['security_answer'] = self.security_answer_var.get()
            
            result = self.admin_auth.update_admin_profile(self.session_token, updates)
            if result['success']:
                messagebox.showinfo("Success", "Profile updated successfully!")
                self._load_profile_data()  # Refresh data
            else:
                messagebox.showerror("Error", result['error'])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save profile: {str(e)}")
    
    def _save_security_settings(self):
        """Save security settings."""
        try:
            # Configure email 2FA
            result = self.admin_auth.configure_email_2fa(
                self.session_token,
                self.email_2fa_var.get(),
                self.email_var.get()
            )
            
            if result['success']:
                messagebox.showinfo("Success", "Security settings updated successfully!")
                self._load_profile_data()  # Refresh data
            else:
                messagebox.showerror("Error", result['error'])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save security settings: {str(e)}")
    
    def _send_test_email(self):
        """Send a test email OTP."""
        try:
            result = self.admin_auth.send_email_otp(purpose='test')
            if result['success']:
                messagebox.showinfo("Success", result['message'])
            else:
                messagebox.showerror("Error", result['error'])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send test email: {str(e)}")
    
    def _show_email_config(self):
        """Show email configuration dialog."""
        # Switch to email tab
        pass  # Tab is already created
    
    def _test_email_config(self):
        """Test email configuration."""
        try:
            smtp_config = {
                'smtp_server': self.smtp_server_var.get(),
                'smtp_port': int(self.smtp_port_var.get()),
                'from_email': self.from_email_var.get(),
                'from_password': self.from_password_var.get(),
                'use_tls': self.use_tls_var.get(),
                'from_name': 'SilentLock Security'
            }
            
            # Test configuration
            result = self.admin_auth.email_otp_service.configure_email_settings(
                smtp_config['smtp_server'],
                smtp_config['smtp_port'],
                smtp_config['from_email'],
                smtp_config['from_password'],
                smtp_config['use_tls'],
                smtp_config['from_name']
            )
            
            if result['success']:
                messagebox.showinfo("Success", "Email configuration test successful!")
            else:
                messagebox.showerror("Error", f"Email test failed: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Configuration test failed: {str(e)}")
    
    def _save_email_config(self):
        """Save email configuration."""
        try:
            smtp_config = {
                'smtp_server': self.smtp_server_var.get(),
                'smtp_port': int(self.smtp_port_var.get()),
                'from_email': self.from_email_var.get(),
                'from_password': self.from_password_var.get(),
                'use_tls': self.use_tls_var.get(),
                'from_name': 'SilentLock Security'
            }
            
            result = self.admin_auth.configure_email_2fa(
                self.session_token,
                True,  # Enable email 2FA
                self.email_var.get(),
                smtp_config
            )
            
            if result['success']:
                messagebox.showinfo("Success", "Email configuration saved successfully!")
                self._load_profile_data()  # Refresh data
            else:
                messagebox.showerror("Error", result['error'])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save email configuration: {str(e)}")
    
    def _show_totp_qr(self):
        """Show TOTP QR code."""
        messagebox.showinfo("Info", "TOTP QR code display will be implemented.")
    
    def _regenerate_totp(self):
        """Regenerate TOTP secret."""
        messagebox.showinfo("Info", "TOTP regeneration will be implemented.")
    
    def _disable_totp(self):
        """Disable TOTP authentication."""
        messagebox.showinfo("Info", "TOTP disable will be implemented.")
    
    def _setup_totp(self):
        """Setup TOTP authentication."""
        messagebox.showinfo("Info", "TOTP setup will be implemented.")
    
    def _on_close(self):
        """Handle window close."""
        self.profile_window.destroy()
        self.profile_window = None