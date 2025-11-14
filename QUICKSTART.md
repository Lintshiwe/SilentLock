# Quick Start Guide - SilentLock Password Manager

## 🚀 Quick Setup (5 minutes)

### 1. Start the Application
```powershell
# From the project directory:
python main.py

# Or run the VS Code task:
# Ctrl+Shift+P > "Tasks: Run Task" > "Run SilentLock Password Manager"
```

### 2. Initial Setup
1. **Set Master Password**: Enter a strong password when prompted
2. **Main Interface**: The password manager GUI will open

### 3. Basic Usage

#### Add Your First Credential
1. Click **"Add Credential"** button
2. Fill in the form:
   - Site Name: `GitHub`
   - Site URL: `https://github.com`
   - Username: `your_username`
   - Password: `your_password`
3. Click **"Save"**

#### Start Background Monitoring
1. Go to **"Monitor"** tab
2. Click **"Start Monitoring"**
3. Now when you log into websites, SilentLock will detect login forms

### 4. Key Features

| Feature | How to Use |
|---------|------------|
| **View Passwords** | Double-click any credential to copy password |
| **Search** | Type in the search box to filter credentials |
| **Edit** | Select credential → Click "Edit" |
| **Delete** | Select credential → Click "Delete" |
| **Auto-Save** | Start monitoring → Login to any site → Accept save prompt |

## 🔒 Security Tips

- **Master Password**: Choose a strong, memorable password
- **Backup**: Keep the database file safe (`%APPDATA%\SilentLock\credentials.db`)
- **Privacy**: Only use on your own devices
- **Updates**: Keep the application updated for security patches

## ⚡ Keyboard Shortcuts

- `Ctrl+N` - Add new credential
- `Delete` - Delete selected credential  
- `F5` - Refresh credential list
- `Double-click` - Copy password to clipboard

## 🛡️ Privacy Notice

✅ **What SilentLock DOES:**
- Stores passwords locally on your device only
- Encrypts all data with AES-256
- Monitors keyboard input to detect login forms (when enabled)
- Requires your explicit consent to save credentials

❌ **What SilentLock NEVER DOES:**
- Send data over the internet
- Access other users' data
- Store passwords in plain text
- Work without your permission

## 🆘 Need Help?

**Application won't start?**
- Run: `python test_basic.py` to verify installation
- Check: Python 3.8+ is installed
- Ensure: All requirements installed (`pip install -r requirements.txt`)

**Can't remember master password?**
- Unfortunately, you'll need to reset the database
- Delete: `%APPDATA%\SilentLock\credentials.db`
- Restart SilentLock to set a new master password

**Monitoring not working?**
- Run as Administrator for monitoring features
- Check antivirus isn't blocking the application
- Try restarting the monitoring from the Monitor tab

---

🎉 **You're all set!** SilentLock will help keep your passwords secure and accessible.