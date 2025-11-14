#!/usr/bin/env python3
"""
SilentLock Password Manager - Setup Configuration
For building with cx_Freeze, setuptools, and other tools.
"""

import sys
import os
from pathlib import Path
from cx_Freeze import setup, Executable
import setuptools

# Project information
APP_NAME = "SilentLock Password Manager"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Secure, Ethical Password Manager for Personal Use"
APP_AUTHOR = "SilentLock Development Team"
APP_URL = "https://github.com/silentlock/silentlock"

# Get project directory
PROJECT_DIR = Path(__file__).parent
SRC_DIR = PROJECT_DIR / "src"
ASSETS_DIR = PROJECT_DIR / "assets"

# Dependencies that need to be included
PACKAGES = [
    "tkinter",
    "cryptography",
    "pynput", 
    "pywin32",
    "PIL", 
    "pyperclip",
    "psutil",
    "plyer",
    "requests",
    "qrcode",
    "pyotp",
    "zxcvbn",
    "fido2",
    "sqlite3",
    "threading",
    "queue",
    "collections",
    "json",
    "base64",
    "hashlib",
    "hmac",
    "secrets",
    "datetime",
    "time",
    "os",
    "sys",
    "pathlib",
    "configparser",
]

# Files to include in the build
INCLUDE_FILES = [
    (str(ASSETS_DIR), "assets"),
    (str(PROJECT_DIR / "config"), "config"),
    (str(PROJECT_DIR / "requirements.txt"), "requirements.txt"),
    (str(PROJECT_DIR / "README.md"), "README.md"),
    (str(PROJECT_DIR / "USER_MANUAL.md"), "USER_MANUAL.md"),
]

# Build options for cx_Freeze
BUILD_OPTIONS = {
    "packages": PACKAGES,
    "include_files": INCLUDE_FILES,
    "excludes": [
        "matplotlib", "scipy", "numpy", "pandas", 
        "jupyter", "notebook", "IPython", "test"
    ],
    "include_msvcrt": True,
    "optimize": 2,
}

# Executable configuration
EXECUTABLES = [
    Executable(
        script="main.py",
        base="Win32GUI",  # Use Win32GUI for Windows GUI app (no console)
        target_name="SilentLock.exe",
        icon=str(ASSETS_DIR / "logo.ico") if (ASSETS_DIR / "logo.ico").exists() else None,
        shortcut_name=APP_NAME,
        shortcut_dir="DesktopFolder",
    )
]

# Setup configuration
setup(
    name=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    author=APP_AUTHOR,
    url=APP_URL,
    options={"build_exe": BUILD_OPTIONS},
    executables=EXECUTABLES,
    
    # Additional metadata for setuptools
    long_description=open("README.md", "r", encoding="utf-8").read() if Path("README.md").exists() else APP_DESCRIPTION,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Security",
        "Topic :: Security :: Cryptography",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9", 
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",
    install_requires=[
        "cryptography>=41.0.0",
        "pynput>=1.7.6",
        "pywin32>=306",
        "pillow>=10.0.0",
        "pyperclip>=1.8.2",
        "psutil>=5.9.0",
        "plyer>=2.1.0",
        "requests>=2.31.0",
        "qrcode>=7.4.2",
        "pyotp>=2.9.0",
        "zxcvbn>=4.4.28",
        "fido2>=1.1.3",
    ],
    keywords="password manager security encryption windows",
    project_urls={
        "Bug Reports": f"{APP_URL}/issues",
        "Source": APP_URL,
        "Documentation": f"{APP_URL}/wiki",
    },
)

def print_build_instructions():
    """Print build instructions for different methods."""
    print("🔨 SilentLock Build Instructions")
    print("=" * 40)
    print()
    print("🎯 Available Build Methods:")
    print()
    print("1. 📦 cx_Freeze (Recommended):")
    print("   python setup.py build")
    print("   python setup.py bdist_msi  # For MSI installer")
    print()
    print("2. 🔨 PyInstaller:")
    print("   python build_installer.py")
    print("   # OR")
    print("   pyinstaller --onedir --windowed --icon=assets/logo.ico main.py")
    print()
    print("3. 🚀 Auto Build (All methods):")
    print("   python build_installer.py")
    print("   # OR")
    print("   build.bat  # On Windows")
    print()
    print("4. 📋 Manual PyInstaller:")
    print("   pyinstaller SilentLock.spec")
    print()
    print("✅ Output locations:")
    print("   - build/     (cx_Freeze output)")
    print("   - dist/      (PyInstaller output)")
    print("   - installer/ (Installer packages)")
    print()

if __name__ == "__main__":
    # If run directly, show build instructions
    if len(sys.argv) == 1:
        print_build_instructions()
    else:
        # Run normal setup
        pass