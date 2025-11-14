"""
SilentLock Splash Screen
Shows the application logo and loading progress during startup.
"""

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import threading
import time


class SplashScreen:
    """Professional splash screen with logo and loading animation."""
    
    def __init__(self):
        self.splash = tk.Tk()
        self.splash.title("SilentLock")
        self.splash.overrideredirect(True)  # Remove window frame
        
        # Set window size and center it
        width = 400
        height = 300
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.splash.geometry(f"{width}x{height}+{x}+{y}")
        
        # Make it stay on top
        self.splash.attributes('-topmost', True)
        
        # Set background
        self.splash.configure(bg='#2c3e50')
        
        # Initialize progress variables first
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Initializing SilentLock...")
        
        # Load and set window icon
        self._set_window_icon()
        
        # Create splash content
        self._create_splash_content()
        
    def _set_window_icon(self):
        """Set the window icon for better taskbar visibility."""
        try:
            # Try ICO file first (best for Windows)
            ico_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'logo.ico')
            if os.path.exists(ico_path):
                self.splash.iconbitmap(ico_path)
                # Also set proper window class for Windows taskbar integration (if supported)
                try:
                    self.splash.wm_class("SilentLock", "SilentLock Password Manager")
                except AttributeError:
                    # wm_class not available on all tkinter versions
                    pass
                print("✅ Splash screen icon set from ICO")
            else:
                # Fallback to PNG
                logo_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'logo.png')
                if os.path.exists(logo_path):
                    # Load and create multiple sizes for better Windows integration
                    icon_image = Image.open(logo_path)
                    
                    # Create 32x32 and 16x16 icons
                    icon_32 = icon_image.resize((32, 32), Image.Resampling.LANCZOS)
                    icon_photo_32 = ImageTk.PhotoImage(icon_32)
                    
                    icon_16 = icon_image.resize((16, 16), Image.Resampling.LANCZOS)
                    icon_photo_16 = ImageTk.PhotoImage(icon_16)
                    
                    # Set both sizes
                    self.splash.iconphoto(True, icon_photo_32, icon_photo_16)
                    
                    # Keep references
                    self.icon_photo_32 = icon_photo_32
                    self.icon_photo_16 = icon_photo_16
                    print("✅ Splash screen icon set from PNG")
                else:
                    print("⚠️ No logo files found for splash screen")
        except Exception as e:
            print(f"❌ Could not set splash screen icon: {e}")
    
    def _create_splash_content(self):
        """Create the splash screen content."""
        main_frame = tk.Frame(self.splash, bg='#2c3e50')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Logo
        try:
            logo_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'logo.png')
            if os.path.exists(logo_path):
                # Load and resize logo
                logo_image = Image.open(logo_path)
                # Resize to fit splash screen nicely
                logo_image = logo_image.resize((120, 120), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image)
                
                logo_label = tk.Label(main_frame, image=self.logo_photo, bg='#2c3e50')
                logo_label.pack(pady=(10, 20))
            else:
                # Fallback if logo not found
                logo_label = tk.Label(main_frame, text="🔒", font=('Arial', 48), 
                                    bg='#2c3e50', fg='#3498db')
                logo_label.pack(pady=(10, 20))
        except Exception as e:
            print(f"Could not load logo: {e}")
            # Fallback
            logo_label = tk.Label(main_frame, text="🔒", font=('Arial', 48), 
                                bg='#2c3e50', fg='#3498db')
            logo_label.pack(pady=(10, 20))
        
        # Application name
        title_label = tk.Label(main_frame, text="SilentLock", 
                              font=('Arial', 24, 'bold'), 
                              bg='#2c3e50', fg='white')
        title_label.pack(pady=(0, 5))
        
        # Subtitle
        subtitle_label = tk.Label(main_frame, text="Password Manager", 
                                 font=('Arial', 12), 
                                 bg='#2c3e50', fg='#bdc3c7')
        subtitle_label.pack(pady=(0, 20))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate', 
                                          length=300, variable=self.progress_var)
        self.progress_bar.pack(pady=(10, 10))
        
        # Status label
        self.status_label = tk.Label(main_frame, textvariable=self.status_var,
                                    font=('Arial', 10), bg='#2c3e50', fg='#ecf0f1')
        self.status_label.pack(pady=(5, 10))
        
        # Version info
        version_label = tk.Label(main_frame, text="Version 1.0 • Secure • Ethical", 
                               font=('Arial', 8), bg='#2c3e50', fg='#7f8c8d')
        version_label.pack(side='bottom', pady=(20, 0))
    
    def update_progress(self, value, status_text):
        """Update the progress bar and status text."""
        self.progress_var.set(value)
        self.status_var.set(status_text)
        self.splash.update()
    
    def show(self):
        """Show the splash screen."""
        self.splash.deiconify()
        self.splash.update()
        return self.splash
    
    def close(self):
        """Close the splash screen."""
        try:
            self.splash.destroy()
        except:
            pass


class LoadingAnimation:
    """Handles the loading animation sequence."""
    
    def __init__(self, splash_screen):
        self.splash = splash_screen
        self.loading_steps = [
            (10, "Loading security modules..."),
            (25, "Initializing encryption..."),
            (40, "Setting up database..."),
            (55, "Loading audit system..."),
            (70, "Configuring monitoring..."),
            (85, "Preparing interface..."),
            (100, "Ready!")
        ]
    
    def animate_loading(self, callback=None):
        """Animate the loading process."""
        def run_animation():
            for progress, status in self.loading_steps:
                self.splash.update_progress(progress, status)
                time.sleep(0.8)  # Pause between steps
            
            # Brief pause on "Ready!"
            time.sleep(1)
            
            if callback:
                callback()
        
        # Run animation in separate thread
        animation_thread = threading.Thread(target=run_animation, daemon=True)
        animation_thread.start()
        return animation_thread


def show_splash_screen(on_complete_callback=None):
    """Show splash screen with loading animation."""
    splash = SplashScreen()
    splash.show()
    
    # Start loading animation
    animator = LoadingAnimation(splash)
    
    def on_animation_complete():
        if on_complete_callback:
            on_complete_callback()
        # Small delay then close splash
        splash.splash.after(500, splash.close)
    
    animator.animate_loading(on_animation_complete)
    
    return splash


if __name__ == "__main__":
    # Test the splash screen
    def test_complete():
        print("Splash screen test completed!")
    
    splash = show_splash_screen(test_complete)
    splash.splash.mainloop()