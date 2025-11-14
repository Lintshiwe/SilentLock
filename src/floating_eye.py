"""
Enhanced Realistic Floating Eye Monitor Widget for SilentLock.
Displays a realistic, eye-shaped widget in the top-right corner with enhanced monitoring capabilities.
"""

import tkinter as tk
import threading
import time
import math
from datetime import datetime
from typing import Callable, Optional

class FloatingEyeWidget:
    """A realistic eye-shaped floating widget for enhanced monitoring status."""
    
    def __init__(self, on_toggle_callback: Optional[Callable] = None):
        self.window = None
        self.canvas = None
        self.on_toggle_callback = on_toggle_callback
        
        # Eye state
        self.is_monitoring = False
        self.is_visible = False
        self.blink_thread = None
        self.blink_running = False
        self.eye_closed = False
        
        # Enhanced eye properties for realistic shape
        self.eye_width = 90
        self.eye_height = 50
        self.pupil_size = 12
        self.iris_size = 28
        
        # Realistic colors
        self.sclera_color = "#FFFFFF"  # White of eye
        self.iris_color = "#4A90E2"    # Blue iris
        self.pupil_color = "#000000"   # Black pupil
        self.eyelid_color = "#D4AF9A"  # Skin tone for eyelids
        self.border_color = "#8B7355"  # Darker border
        self.lash_color = "#3D3D3D"    # Eyelash color
        
        # Animation timing
        self.blink_interval = 3.0
        self.blink_duration = 0.15
        
        # Eye tracking variables
        self.pupil_x_offset = 0
        self.pupil_y_offset = 0
        
        # Enhanced monitoring flag
        self.enhanced_monitoring = False
        
    def create_widget(self):
        """Create the realistic eye-shaped floating widget."""
        if self.window:
            return
            
        # Create toplevel window
        self.window = tk.Toplevel()
        self.window.title("SilentLock Eye Monitor")
        
        # Window properties for eye shape
        padding = 15
        window_width = self.eye_width + padding
        window_height = self.eye_height + padding
        self.window.geometry(f"{window_width}x{window_height}")
        self.window.resizable(False, False)
        
        # Remove window decorations for custom shape
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        
        # Try to make window background transparent (Windows specific)
        try:
            self.window.wm_attributes('-transparentcolor', 'gray1')
            transparent_bg = 'gray1'
        except:
            transparent_bg = 'SystemButtonFace'
        
        # Position at top-right corner
        screen_width = self.window.winfo_screenwidth()
        x_pos = screen_width - window_width - 25
        y_pos = 25
        self.window.geometry(f"+{x_pos}+{y_pos}")
        
        # Create canvas with transparent background
        self.canvas = tk.Canvas(
            self.window, 
            width=window_width, 
            height=window_height,
            bg=transparent_bg, 
            highlightthickness=0,
            borderwidth=0
        )
        self.canvas.pack()
        
        # Bind enhanced events
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.window.bind("<Button-1>", self._on_click)
        
        # Draw initial realistic eye
        self._draw_realistic_eye()
        
        # Start enhanced animations
        self._start_blinking()
        self._start_eye_tracking()
        
        # Hide initially
        self.window.withdraw()
        
    def show(self):
        """Show the realistic eye widget."""
        if not self.window:
            self.create_widget()
        
        self.is_visible = True
        self.window.deiconify()
        self.window.lift()
        print("👁️ Realistic floating eye monitor activated - Enhanced monitoring enabled!")
        
    def hide(self):
        """Hide the eye widget."""
        if self.window:
            self.is_visible = False
            self.window.withdraw()
            print("👁️ Floating eye monitor hidden")
            
    def destroy(self):
        """Destroy the eye widget."""
        self._stop_blinking()
        if self.window:
            self.window.destroy()
            self.window = None
            
    def set_monitoring(self, monitoring: bool):
        """Set monitoring status and update eye appearance."""
        self.is_monitoring = monitoring
        self.enhanced_monitoring = monitoring  # Enable enhanced tracking when monitoring
        
        if self.canvas:
            self._draw_realistic_eye()
            
        if monitoring:
            print("👁️ Eye monitor: Enhanced tracking ACTIVE - Recording everything accurately!")
        else:
            print("👁️ Eye monitor: Monitoring paused")
            
    def _draw_realistic_eye(self):
        """Draw a highly realistic human eye with advanced details."""
        if not self.canvas:
            return
            
        # Clear canvas
        self.canvas.delete("all")
        
        # Calculate positions
        center_x = self.eye_width // 2 + 7
        center_y = self.eye_height // 2 + 7
        
        if self.eye_closed:
            self._draw_closed_eye(center_x, center_y)
        else:
            self._draw_open_eye(center_x, center_y)
    
    def _draw_open_eye(self, center_x, center_y):
        """Draw an open realistic eye with enhanced details."""
        # Draw realistic almond-shaped sclera (white part)
        eye_points = self._calculate_realistic_eye_shape(center_x, center_y)
        
        # Eye shadow/depth
        shadow_points = self._calculate_realistic_eye_shape(center_x, center_y - 1, 0.95)
        self.canvas.create_polygon(
            shadow_points,
            fill="#F5F5F5",
            outline="",
            smooth=True
        )
        
        # Main sclera
        self.canvas.create_polygon(
            eye_points,
            fill=self.sclera_color,
            outline=self.border_color,
            width=1,
            smooth=True
        )
        
        # Draw iris with enhanced colors based on monitoring status
        iris_x = center_x + self.pupil_x_offset
        iris_y = center_y + self.pupil_y_offset
        
        # Clip iris to realistic eye boundaries
        max_x_offset = self.eye_width // 4
        max_y_offset = self.eye_height // 4
        iris_x = max(center_x - max_x_offset, min(center_x + max_x_offset, iris_x))
        iris_y = max(center_y - max_y_offset, min(center_y + max_y_offset, iris_y))
        
        # Enhanced iris colors with monitoring indication
        if self.is_monitoring and self.enhanced_monitoring:
            iris_color = "#00FF44"  # Bright green for ACTIVE enhanced monitoring
            glow_color = "#88FF88"  # Glow effect for active monitoring
        elif self.is_monitoring:
            iris_color = "#00CC66"  # Standard green for basic monitoring
            glow_color = "#66DD88"
        else:
            iris_color = self.iris_color  # Blue for inactive
            glow_color = "#88BBFF"
            
        # Iris glow effect (outer ring)
        self.canvas.create_oval(
            iris_x - self.iris_size//2 - 3,
            iris_y - self.iris_size//2 - 3,
            iris_x + self.iris_size//2 + 3,
            iris_y + self.iris_size//2 + 3,
            fill=glow_color,
            outline="",
            stipple="gray50"
        )
        
        # Main iris
        self.canvas.create_oval(
            iris_x - self.iris_size//2,
            iris_y - self.iris_size//2,
            iris_x + self.iris_size//2,
            iris_y + self.iris_size//2,
            fill=iris_color,
            outline=self.border_color,
            width=1
        )
        
        # Iris texture lines for realism
        self._draw_iris_texture(iris_x, iris_y, iris_color)
        
        # Draw pupil with enhanced depth
        pupil_x = iris_x
        pupil_y = iris_y
        
        # Pupil shadow for depth
        self.canvas.create_oval(
            pupil_x - self.pupil_size//2 + 1,
            pupil_y - self.pupil_size//2 + 1,
            pupil_x + self.pupil_size//2 + 1,
            pupil_y + self.pupil_size//2 + 1,
            fill="#333333",
            outline=""
        )
        
        # Main pupil
        self.canvas.create_oval(
            pupil_x - self.pupil_size//2,
            pupil_y - self.pupil_size//2,
            pupil_x + self.pupil_size//2,
            pupil_y + self.pupil_size//2,
            fill=self.pupil_color,
            outline=""
        )
        
        # Enhanced highlights for realism
        # Main highlight
        highlight_x = pupil_x - 3
        highlight_y = pupil_y - 3
        self.canvas.create_oval(
            highlight_x - 3, highlight_y - 3,
            highlight_x + 3, highlight_y + 3,
            fill="white", outline=""
        )
        
        # Secondary highlight on iris
        self.canvas.create_oval(
            iris_x + 6, iris_y - 6,
            iris_x + 10, iris_y - 2,
            fill="white", outline=""
        )
        
        # Tiny sparkle for active monitoring
        if self.is_monitoring:
            self.canvas.create_oval(
                pupil_x + 4, pupil_y - 4,
                pupil_x + 6, pupil_y - 2,
                fill="#FFFF88", outline=""
            )
        
        # Draw realistic eyelashes
        self._draw_enhanced_eyelashes(center_x, center_y)
        
        # Add tear duct detail
        self._draw_tear_duct(center_x, center_y)
    
    def _draw_closed_eye(self, center_x, center_y):
        """Draw a closed eye with realistic eyelids and lashes."""
        # Calculate eyelid curves
        upper_points = []
        lower_points = []
        
        # Create realistic eyelid curves
        for i in range(-self.eye_width//2, self.eye_width//2, 1):
            x = center_x + i
            
            # Upper eyelid - more pronounced curve
            angle = math.pi * (i + self.eye_width//2) / self.eye_width
            upper_y = center_y - 3 + int(12 * math.sin(angle))
            
            # Lower eyelid - subtle curve
            lower_y = center_y + 2 - int(6 * math.sin(angle))
            
            upper_points.extend([x, upper_y])
            lower_points.extend([x, lower_y])
        
        # Draw eyelid shadow
        if len(upper_points) >= 6:
            shadow_points = [p + (1 if i % 2 == 1 else 0) for i, p in enumerate(upper_points)]
            self.canvas.create_line(
                shadow_points,
                fill="#C4A484",
                width=4,
                smooth=True
            )
        
        # Draw main eyelids
        if len(upper_points) >= 6 and len(lower_points) >= 6:
            self.canvas.create_line(
                upper_points,
                fill=self.eyelid_color,
                width=3,
                smooth=True
            )
            self.canvas.create_line(
                lower_points, 
                fill=self.eyelid_color,
                width=2,
                smooth=True
            )
        
        # Draw eyelashes on closed eye
        self._draw_closed_eyelashes(center_x, center_y)
    
    def _calculate_realistic_eye_shape(self, center_x, center_y, scale=1.0):
        """Calculate points for highly realistic almond eye shape."""
        points = []
        
        # Create precise almond shape using enhanced mathematical curves
        for angle in range(0, 360, 8):  # Higher resolution
            rad = math.radians(angle)
            
            # Advanced almond shape formula with realistic proportions
            if 0 <= angle <= 180:  # Upper part
                r = (self.eye_width * scale) // 2 * (0.85 + 0.15 * math.sin(rad))
                y_offset = -(self.eye_height * scale) // 2 * math.sin(rad) * 0.75
            else:  # Lower part  
                r = (self.eye_width * scale) // 2 * (0.85 + 0.15 * math.sin(rad))
                y_offset = -(self.eye_height * scale) // 2 * math.sin(rad) * 0.55
                
            # Apply realistic eye corner adjustments
            if 170 <= angle <= 190 or 350 <= angle or angle <= 10:
                r *= 0.9  # Narrow the corners
                
            x = center_x + r * math.cos(rad)
            y = center_y + y_offset
            
            points.extend([x, y])
            
        return points
    
    def _draw_iris_texture(self, iris_x, iris_y, base_color):
        """Draw realistic iris texture lines."""
        try:
            # Convert hex color to RGB for blending
            if base_color.startswith('#'):
                hex_color = base_color[1:]
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16) 
                b = int(hex_color[4:6], 16)
                
                # Create darker shade for texture
                texture_color = f"#{max(0, r-30):02x}{max(0, g-30):02x}{max(0, b-30):02x}"
            else:
                texture_color = "#555555"
            
            # Draw radial texture lines
            for i in range(0, 360, 30):
                angle = math.radians(i)
                start_r = 3
                end_r = self.iris_size // 2 - 2
                
                x1 = iris_x + start_r * math.cos(angle)
                y1 = iris_y + start_r * math.sin(angle)
                x2 = iris_x + end_r * math.cos(angle)
                y2 = iris_y + end_r * math.sin(angle)
                
                self.canvas.create_line(x1, y1, x2, y2, fill=texture_color, width=1)
                
        except Exception as e:
            print(f"Error drawing iris texture: {e}")
    
    def _draw_enhanced_eyelashes(self, center_x, center_y):
        """Draw realistic, varied eyelashes."""
        import random
        
        # Upper eyelashes - more prominent
        for i in range(-4, 5):
            x_base = center_x + i * 7
            y_base = center_y - self.eye_height//2 - 1
            
            # Vary lash length and curve
            length = 5 + random.randint(-1, 2)
            curve = random.randint(-2, 2)
            
            x_tip = x_base + curve
            y_tip = y_base - length
            
            self.canvas.create_line(
                x_base, y_base, x_tip, y_tip,
                fill=self.lash_color,
                width=1
            )
            
        # Lower eyelashes - smaller and sparser
        for i in range(-2, 3):
            x_base = center_x + i * 12
            y_base = center_y + self.eye_height//2 + 1
            
            length = 2 + random.randint(0, 1)
            x_tip = x_base
            y_tip = y_base + length
            
            self.canvas.create_line(
                x_base, y_base, x_tip, y_tip,
                fill=self.lash_color,
                width=1
            )
    
    def _draw_closed_eyelashes(self, center_x, center_y):
        """Draw eyelashes on closed eye."""
        import random
        
        for i in range(-4, 5):
            x_base = center_x + i * 7
            y_base = center_y - 2
            
            length = 6 + random.randint(-1, 2)
            curve = random.randint(-2, 2)
            
            x_tip = x_base + curve
            y_tip = y_base - length
            
            self.canvas.create_line(
                x_base, y_base, x_tip, y_tip,
                fill=self.lash_color,
                width=1
            )
    
    def _draw_tear_duct(self, center_x, center_y):
        """Draw realistic tear duct detail."""
        duct_x = center_x - self.eye_width//2 + 3
        duct_y = center_y
        
        # Small pink tear duct
        self.canvas.create_oval(
            duct_x - 2, duct_y - 2,
            duct_x + 2, duct_y + 2,
            fill="#FFB6C1",
            outline=self.border_color,
            width=1
        )
    
    def _start_eye_tracking(self):
        """Start realistic eye movement and enhanced monitoring."""
        def enhanced_eye_movement():
            while self.blink_running and self.is_visible:
                try:
                    # Enhanced monitoring: more active eye movement when monitoring
                    if self.enhanced_monitoring and not self.eye_closed:
                        import random
                        
                        # More active scanning when enhanced monitoring is on
                        self.pupil_x_offset = random.randint(-5, 5)
                        self.pupil_y_offset = random.randint(-3, 3)
                        
                        if self.canvas:
                            self.canvas.after(0, self._draw_realistic_eye)
                            
                        # Faster scanning for enhanced monitoring
                        time.sleep(1 + random.random() * 2)  # 1-3 seconds
                        
                    elif not self.eye_closed:
                        # Normal subtle movement when not enhanced monitoring
                        import random
                        self.pupil_x_offset = random.randint(-2, 2)
                        self.pupil_y_offset = random.randint(-1, 1)
                        
                        if self.canvas:
                            self.canvas.after(0, self._draw_realistic_eye)
                            
                        time.sleep(3 + random.random() * 4)  # 3-7 seconds
                    else:
                        time.sleep(0.5)  # Short sleep when eye is closed
                        
                except Exception as e:
                    print(f"Error in enhanced eye tracking: {e}")
                    break
        
        if not hasattr(self, 'tracking_thread') or not self.tracking_thread.is_alive():
            self.tracking_thread = threading.Thread(target=enhanced_eye_movement, daemon=True)
            self.tracking_thread.start()
    
    def _start_blinking(self):
        """Start enhanced blinking animation."""
        if self.blink_running:
            return
            
        self.blink_running = True
        self.blink_thread = threading.Thread(target=self._enhanced_blink_loop, daemon=True)
        self.blink_thread.start()
        
    def _stop_blinking(self):
        """Stop all animations."""
        self.blink_running = False
        if self.blink_thread:
            self.blink_thread.join(timeout=1)
            
    def _enhanced_blink_loop(self):
        """Enhanced blinking with natural variation."""
        while self.blink_running:
            try:
                import random
                
                # Natural blink intervals with enhanced monitoring adjustments
                if self.enhanced_monitoring:
                    # More alert blinking when enhanced monitoring
                    base_interval = 2.0
                    variation = 1.0
                else:
                    # Normal blinking
                    base_interval = self.blink_interval
                    variation = 1.5
                
                interval = base_interval + random.uniform(-variation, variation)
                interval = max(0.5, interval)  # Minimum interval
                
                # Wait for blink interval
                for _ in range(int(interval * 10)):
                    if not self.blink_running:
                        break
                    time.sleep(0.1)
                
                if not self.blink_running:
                    break
                    
                # Natural blink duration variation
                blink_duration = self.blink_duration + random.uniform(-0.05, 0.1)
                self._perform_realistic_blink(blink_duration)
                
            except Exception as e:
                print(f"Error in enhanced blink loop: {e}")
                break
                
    def _perform_realistic_blink(self, duration=None):
        """Perform a natural, realistic blink animation."""
        try:
            if not self.canvas or not self.is_visible:
                return
                
            if duration is None:
                duration = self.blink_duration
                
            # Close eye
            self.eye_closed = True
            if self.canvas:
                self.canvas.after(0, self._draw_realistic_eye)
            
            # Natural blink duration
            time.sleep(duration)
            
            # Open eye
            if self.blink_running and self.canvas and self.is_visible:
                self.eye_closed = False
                if self.canvas:
                    self.canvas.after(0, self._draw_realistic_eye)
                
        except Exception as e:
            print(f"Error performing realistic blink: {e}")
            
    def _on_click(self, event):
        """Handle click with enhanced visual feedback."""
        try:
            # Enhanced pupil dilation effect
            original_pupil_size = self.pupil_size
            original_iris_size = self.iris_size
            
            # Dramatic dilation for click feedback
            self.pupil_size = int(self.pupil_size * 1.5)
            self.iris_size = int(self.iris_size * 1.1)
            self._draw_realistic_eye()
            
            # Reset after feedback period
            self.window.after(200, lambda: self._reset_eye_size(original_pupil_size, original_iris_size))
            
            # Enhanced monitoring toggle
            if self.on_toggle_callback:
                self.on_toggle_callback()
                print("👁️ Eye clicked: Enhanced monitoring toggled!")
            else:
                # Default behavior with enhanced feedback
                self.hide()
                print("👁️ Eye monitor hidden - will return in 5 seconds")
                threading.Timer(5.0, self.show).start()
                
        except Exception as e:
            print(f"Error handling enhanced eye click: {e}")
            
    def _reset_eye_size(self, original_pupil_size, original_iris_size):
        """Reset eye size after click effect."""
        self.pupil_size = original_pupil_size
        self.iris_size = original_iris_size
        if self.canvas:
            self._draw_realistic_eye()
            
    def _on_enter(self, event):
        """Handle mouse enter with enhanced glow effect."""
        if self.canvas:
            self.canvas.config(cursor="hand2")
            
            # Enhanced glow colors when hovered
            if self.is_monitoring and self.enhanced_monitoring:
                self.iris_color = "#00FF77"  # Bright enhanced green
            elif self.is_monitoring:
                self.iris_color = "#44DD77"  # Standard monitoring green
            else:
                self.iris_color = "#6AA3F0"  # Brighter blue for inactive
                
            self._draw_realistic_eye()
            
    def _on_leave(self, event):
        """Handle mouse leave and reset to normal colors."""
        if self.canvas:
            self.canvas.config(cursor="")
            
            # Reset to normal colors
            if self.is_monitoring and self.enhanced_monitoring:
                self.iris_color = "#00FF44"  # Enhanced monitoring green
            elif self.is_monitoring:
                self.iris_color = "#00CC66"  # Standard monitoring green
            else:
                self.iris_color = "#4A90E2"  # Normal blue
                
            self._draw_realistic_eye()
            
    def _on_mouse_move(self, event):
        """Make eye follow mouse cursor with enhanced tracking."""
        if self.eye_closed or not self.canvas:
            return
            
        try:
            # Get canvas center
            canvas_center_x = self.eye_width // 2 + 7
            canvas_center_y = self.eye_height // 2 + 7
            
            # Calculate mouse position relative to eye center
            mouse_x = event.x - canvas_center_x
            mouse_y = event.y - canvas_center_y
            
            # Enhanced pupil movement range when enhanced monitoring
            if self.enhanced_monitoring:
                max_offset = 6  # More responsive tracking
            else:
                max_offset = 4  # Standard tracking
                
            distance = math.sqrt(mouse_x**2 + mouse_y**2)
            
            if distance > 0:
                factor = min(distance / 15, max_offset)
                self.pupil_x_offset = (mouse_x / distance) * factor
                self.pupil_y_offset = (mouse_y / distance) * factor
            else:
                self.pupil_x_offset = 0
                self.pupil_y_offset = 0
                
            self._draw_realistic_eye()
            
        except Exception as e:
            print(f"Error in enhanced mouse tracking: {e}")
    
    def update_position(self):
        """Update position to stay in top-right corner."""
        if not self.window:
            return
            
        try:
            screen_width = self.window.winfo_screenwidth()
            window_width = self.eye_width + 15
            x_pos = screen_width - window_width - 25
            y_pos = 25
            self.window.geometry(f"+{x_pos}+{y_pos}")
        except Exception as e:
            print(f"Error updating enhanced eye position: {e}")


class EyeSettings:
    """Enhanced settings manager for the realistic floating eye."""
    
    def __init__(self):
        self.enabled = False
        self.auto_start = False
        self.blink_interval = 3.0
        self.enhanced_tracking = True  # Enable enhanced monitoring when eye is active
        self.realistic_movement = True  # Enable eye movement and tracking
        self.monitor_everything = True  # Monitor and record everything accurately when enabled
        
    def load_settings(self, settings_dict: dict):
        """Load settings from dictionary."""
        eye_settings = settings_dict.get('floating_eye', {})
        self.enabled = eye_settings.get('enabled', False)
        self.auto_start = eye_settings.get('auto_start', False)
        self.blink_interval = eye_settings.get('blink_interval', 3.0)
        self.enhanced_tracking = eye_settings.get('enhanced_tracking', True)
        self.realistic_movement = eye_settings.get('realistic_movement', True)
        self.monitor_everything = eye_settings.get('monitor_everything', True)
        
    def save_settings(self) -> dict:
        """Save settings to dictionary."""
        return {
            'floating_eye': {
                'enabled': self.enabled,
                'auto_start': self.auto_start,
                'blink_interval': self.blink_interval,
                'enhanced_tracking': self.enhanced_tracking,
                'realistic_movement': self.realistic_movement,
                'monitor_everything': self.monitor_everything
            }
        }