@echo off
REM SilentLock Password Manager - Build Script for Windows
REM This script builds SilentLock into an installable executable

echo ================================================
echo SilentLock Password Manager - Build Script
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.8+ and add it to your PATH
    pause
    exit /b 1
)

echo ✅ Python is installed
echo.

REM Check if we're in the right directory
if not exist "main.py" (
    echo ❌ Error: main.py not found
    echo Please run this script from the SilentLock project directory
    pause
    exit /b 1
)

echo ✅ Found main.py - in correct directory
echo.

REM Install/upgrade pip
echo 📦 Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo 📦 Installing dependencies...
python -m pip install -r requirements.txt

REM Install build tools
echo 🔨 Installing build tools...
python -m pip install pyinstaller>=5.13.0
python -m pip install cx_Freeze>=6.15.0
python -m pip install auto-py-to-exe>=2.40.0

echo.
echo ✅ All dependencies installed
echo.

REM Test the application first
echo 🧪 Testing application...
python -c "import sys; sys.path.append('src'); from src.gui import SilentLockGUI; print('✅ Application can be imported successfully')"

if %errorlevel% neq 0 (
    echo ❌ Error: Application failed to import
    echo Please check for missing dependencies
    pause
    exit /b 1
)

echo ✅ Application test passed
echo.

REM Build with the installer builder
echo 🔨 Building installer packages...
python build_installer.py

if %errorlevel% neq 0 (
    echo ❌ Error: Build failed
    pause
    exit /b 1
)

echo.
echo 🎉 BUILD COMPLETE!
echo ================================================
echo ✅ SilentLock has been built successfully!
echo.
echo 📁 Find your files in:
echo   - dist/        (Executable and app files)
echo   - installer/   (Installer packages and scripts)
echo.
echo 📋 Available packages:
echo   1. Portable ZIP - Ready to distribute
echo   2. NSIS Installer Script - Compile with NSIS
echo   3. Inno Setup Script - Compile with Inno Setup
echo   4. WiX MSI Script - Compile with WiX Toolset
echo.
echo 🚀 Your SilentLock Password Manager is ready for distribution!
echo ================================================
echo.
pause