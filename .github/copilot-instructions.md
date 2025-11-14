# SilentLock Password Manager

## Project Overview
SilentLock is a professional, ethical password manager for personal use that:
- Runs as a background service on Windows
- Detects login forms and prompts to save credentials
- Stores passwords securely with AES encryption
- Uses local storage only (no cloud sync)
- Provides a clean GUI for password management
- Implements master password protection

## Security Features
- AES-256 encryption for stored passwords
- Master password with PBKDF2 key derivation
- Local SQLite database with encryption
- Secure memory handling
- No network transmission of credentials

## Technical Stack
- Python 3.8+
- tkinter for GUI
- cryptography library for encryption
- sqlite3 for local storage
- pynput for keyboard monitoring
- pywin32 for Windows integration

## Ethical Guidelines
- For personal use only
- Requires user consent for credential storage
- Clear opt-in/opt-out mechanisms
- Transparent about data handling
- No unauthorized access to other systems