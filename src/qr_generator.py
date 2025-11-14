"""
QR Code Generator for SilentLock Password Manager.
Generates QR codes for credentials, sharing, and 2FA setup.
"""

import qrcode
try:
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    STYLED_QR_AVAILABLE = True
except ImportError:
    STYLED_QR_AVAILABLE = False
import base64
import json
import io
import time
from typing import Dict, Optional, Union
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter import ttk


class QRCodeGenerator:
    """Enhanced QR code generator for various SilentLock features."""
    
    def __init__(self):
        self.default_size = 10
        self.default_border = 4
        
    def generate_credential_qr(self, website: str, username: str, password: str, 
                             notes: str = "", include_logo: bool = True) -> Dict[str, Union[str, bytes]]:
        """
        Generate QR code for credential sharing.
        
        Args:
            website: Website URL or application name
            username: Username or email
            password: Password (encrypted for sharing)
            notes: Additional notes
            include_logo: Whether to include SilentLock branding
            
        Returns:
            Dict with base64 image data and raw image bytes
        """
        try:
            # Create credential data structure
            credential_data = {
                "type": "silentlock_credential",
                "version": "1.0",
                "website": website,
                "username": username,
                "password": password,  # This should be encrypted when sharing
                "notes": notes,
                "timestamp": str(int(time.time())),
                "source": "SilentLock Password Manager"
            }
            
            # Convert to JSON
            qr_data = json.dumps(credential_data, separators=(',', ':'))
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=self.default_size,
                border=self.default_border,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Generate styled image
            if include_logo and STYLED_QR_AVAILABLE:
                img = qr.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=RoundedModuleDrawer(),
                    fill_color="#2c3e50",
                    back_color="white"
                )
            else:
                img = qr.make_image(fill_color="#2c3e50", back_color="white")
            
            # Add SilentLock branding
            if include_logo:
                img = self._add_branding(img, "SilentLock Credential")
            
            # Convert to base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                'success': True,
                'base64': f"data:image/png;base64,{img_base64}",
                'bytes': img_bytes,
                'format': 'PNG'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate credential QR code: {str(e)}"
            }
    
    def generate_2fa_qr(self, secret: str, account_name: str, issuer: str = "SilentLock") -> Dict[str, Union[str, bytes]]:
        """
        Generate QR code for 2FA/TOTP setup.
        
        Args:
            secret: Base32 encoded secret key
            account_name: Account identifier
            issuer: Service issuer name
            
        Returns:
            Dict with base64 image data and TOTP URI
        """
        try:
            # Create TOTP URI
            totp_uri = f"otpauth://totp/{issuer}:{account_name}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=4,
            )
            qr.add_data(totp_uri)
            qr.make(fit=True)
            
            # Generate image
            if STYLED_QR_AVAILABLE:
                img = qr.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=RoundedModuleDrawer(),
                    fill_color="#1a5490",
                    back_color="white"
                )
            else:
                img = qr.make_image(fill_color="#1a5490", back_color="white")
            
            # Add 2FA branding
            img = self._add_branding(img, "2FA Setup")
            
            # Convert to base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                'success': True,
                'base64': f"data:image/png;base64,{img_base64}",
                'bytes': img_bytes,
                'uri': totp_uri,
                'secret': secret
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate 2FA QR code: {str(e)}"
            }
    
    def generate_wifi_qr(self, ssid: str, password: str, security: str = "WPA") -> Dict[str, Union[str, bytes]]:
        """
        Generate QR code for WiFi credentials.
        
        Args:
            ssid: Network name
            password: Network password
            security: Security type (WPA, WEP, nopass)
            
        Returns:
            Dict with base64 image data
        """
        try:
            # Create WiFi data string
            wifi_data = f"WIFI:T:{security};S:{ssid};P:{password};;"
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(wifi_data)
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            img = self._add_branding(img, f"WiFi: {ssid}")
            
            # Convert to base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                'success': True,
                'base64': f"data:image/png;base64,{img_base64}",
                'bytes': img_bytes,
                'wifi_string': wifi_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate WiFi QR code: {str(e)}"
            }
    
    def generate_url_qr(self, url: str, title: str = "") -> Dict[str, Union[str, bytes]]:
        """
        Generate QR code for URL sharing.
        
        Args:
            url: URL to encode
            title: Optional title for branding
            
        Returns:
            Dict with base64 image data
        """
        try:
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # Generate image
            img = qr.make_image(fill_color="black", back_color="white")
            
            if title:
                img = self._add_branding(img, title)
            
            # Convert to base64
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_bytes = img_buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode()
            
            return {
                'success': True,
                'base64': f"data:image/png;base64,{img_base64}",
                'bytes': img_bytes,
                'url': url
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f"Failed to generate URL QR code: {str(e)}"
            }
    
    def _add_branding(self, qr_img: Image.Image, title: str) -> Image.Image:
        """Add SilentLock branding to QR code image."""
        try:
            # Calculate dimensions
            qr_width, qr_height = qr_img.size
            padding = 40
            title_height = 60
            
            # Create new image with space for title
            branded_width = qr_width + (padding * 2)
            branded_height = qr_height + title_height + (padding * 2)
            
            # Create branded image
            branded_img = Image.new('RGB', (branded_width, branded_height), 'white')
            
            # Paste QR code
            qr_x = (branded_width - qr_width) // 2
            qr_y = title_height + padding
            branded_img.paste(qr_img, (qr_x, qr_y))
            
            # Add title text
            draw = ImageDraw.Draw(branded_img)
            
            try:
                # Try to use a nice font
                font = ImageFont.truetype("arial.ttf", 16)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
            
            # Draw title
            title_bbox = draw.textbbox((0, 0), title, font=font)
            title_width = title_bbox[2] - title_bbox[0]
            title_x = (branded_width - title_width) // 2
            title_y = padding // 2
            
            draw.text((title_x, title_y), title, fill='#2c3e50', font=font)
            
            # Draw SilentLock subtitle
            subtitle = "Generated by SilentLock"
            try:
                small_font = ImageFont.truetype("arial.ttf", 10)
            except:
                small_font = ImageFont.load_default()
            
            subtitle_bbox = draw.textbbox((0, 0), subtitle, font=small_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
            subtitle_x = (branded_width - subtitle_width) // 2
            subtitle_y = qr_y + qr_height + 10
            
            draw.text((subtitle_x, subtitle_y), subtitle, fill='#7f8c8d', font=small_font)
            
            return branded_img
            
        except Exception as e:
            # Return original image if branding fails
            return qr_img
    
    def show_qr_dialog(self, qr_data: Dict, parent_window=None, title: str = "QR Code"):
        """
        Display QR code in a popup dialog.
        
        Args:
            qr_data: QR code data from generation methods
            parent_window: Parent tkinter window
            title: Dialog title
        """
        if not qr_data.get('success'):
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", qr_data.get('error', 'Failed to generate QR code'))
            return
        
        try:
            # Create dialog window
            dialog = tk.Toplevel(parent_window) if parent_window else tk.Tk()
            dialog.title(title)
            dialog.geometry("400x500")
            dialog.configure(bg='white')
            dialog.resizable(False, False)
            
            # Center dialog
            if parent_window:
                dialog.transient(parent_window)
                dialog.grab_set()
            
            # Load QR image
            import tkinter as tk
            from PIL import ImageTk
            
            # Decode base64 image
            img_data = base64.b64decode(qr_data['base64'].split(',')[1])
            img = Image.open(io.BytesIO(img_data))
            
            # Resize if needed
            max_size = 300
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Convert for tkinter
            photo = ImageTk.PhotoImage(img)
            
            # Create UI elements
            main_frame = ttk.Frame(dialog)
            main_frame.pack(fill='both', expand=True, padx=20, pady=20)
            
            # QR code image
            image_label = ttk.Label(main_frame, image=photo)
            image_label.image = photo  # Keep a reference
            image_label.pack(pady=(0, 20))
            
            # Instructions
            instructions = ttk.Label(
                main_frame,
                text="Scan this QR code with your mobile device\nor QR code reader application",
                font=('Arial', 10),
                justify='center'
            )
            instructions.pack(pady=(0, 20))
            
            # Buttons frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill='x')
            
            # Save button
            def save_qr():
                from tkinter import filedialog
                filename = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                    title="Save QR Code"
                )
                if filename:
                    with open(filename, 'wb') as f:
                        f.write(qr_data['bytes'])
                    import tkinter.messagebox as messagebox
                    messagebox.showinfo("Success", f"QR code saved to:\n{filename}")
            
            save_btn = ttk.Button(button_frame, text="Save Image", command=save_qr)
            save_btn.pack(side='left', padx=(0, 10))
            
            # Close button
            close_btn = ttk.Button(button_frame, text="Close", command=dialog.destroy)
            close_btn.pack(side='right')
            
            # Center dialog on screen
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")
            
            # Run dialog
            if not parent_window:
                dialog.mainloop()
                
        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Error", f"Failed to display QR code: {str(e)}")


# Convenience functions for quick QR generation
def generate_credential_qr(website: str, username: str, password: str, notes: str = "") -> Dict:
    """Quick credential QR generation."""
    generator = QRCodeGenerator()
    return generator.generate_credential_qr(website, username, password, notes)

def generate_2fa_qr(secret: str, account_name: str, issuer: str = "SilentLock") -> Dict:
    """Quick 2FA QR generation."""
    generator = QRCodeGenerator()
    return generator.generate_2fa_qr(secret, account_name, issuer)

def show_credential_qr(website: str, username: str, password: str, parent=None):
    """Quick credential QR display."""
    generator = QRCodeGenerator()
    qr_data = generator.generate_credential_qr(website, username, password)
    generator.show_qr_dialog(qr_data, parent, f"Credential QR - {website}")


if __name__ == "__main__":
    # Test QR code generation
    import time
    
    generator = QRCodeGenerator()
    
    # Test credential QR
    test_qr = generator.generate_credential_qr(
        "example.com",
        "testuser@example.com", 
        "securepassword123",
        "Test credential for development"
    )
    
    if test_qr['success']:
        print("✅ Credential QR code generated successfully")
        generator.show_qr_dialog(test_qr, title="Test Credential QR")
    else:
        print("❌ Failed to generate credential QR:", test_qr['error'])