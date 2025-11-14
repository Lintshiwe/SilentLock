# SilentLock Complete User Manual

## 🚀 Quick Start with Enhanced Features

### **First Launch Setup**
1. Run `python main.py`
2. Set up your master password
3. **NEW**: Choose if you want Windows auto-start
4. Start monitoring from the Monitor tab

### **Daily Usage Workflow**

#### **Scenario 1: Saving New Credentials**
```
1. Visit a new website (e.g., github.com)
2. Enter your username and password
3. Submit the login form
4. SilentLock prompt: "Save login for username@GitHub?"
5. Click "Yes" → Notification: "New Credential Saved!"
```

#### **Scenario 2: Using Auto-Fill**
```
1. Return to github.com later
2. SilentLock detects the login page
3. Prompt: "Auto-fill login for username@GitHub?"
4. Click "Yes" → Credentials automatically filled
5. Notification: "Auto-fill complete for username@GitHub"
```

#### **Scenario 3: Multiple Accounts**
```
1. Visit a site where you have multiple accounts
2. SilentLock shows account selection:
   ┌─────────────────────────────────┐
   │ Select Account:                 │
   │ ☐ work@company.com             │
   │ ☐ personal@gmail.com           │
   │ ☐ backup@outlook.com           │
   │ [Auto-Fill] [Cancel]           │
   └─────────────────────────────────┘
3. Select desired account → Auto-fill proceeds
```

## 🔧 Configuration Guide

### **Windows Startup Configuration**
1. **Open Settings**: SilentLock → Settings tab
2. **Enable Auto-Start**: Check "Start SilentLock automatically when Windows starts"
3. **Confirmation**: Notification confirms activation
4. **Test**: Restart computer to verify startup

### **Monitoring Preferences**
1. **Auto-Start Monitoring**: Configure monitoring to begin automatically
2. **Notification Settings**: Choose when to show save/auto-fill notifications
3. **Browser Selection**: Customize which browsers to monitor
4. **Sensitivity**: Adjust login form detection sensitivity

### **Security Settings**
1. **Master Password**: Change master password as needed
2. **Auto-Lock**: Configure automatic database locking
3. **Session Timeout**: Set inactivity timeout for security
4. **Activity Logging**: Enable/disable detailed activity logs

## 🎯 Application Monitoring Examples

### **Supported Browsers** (Auto-Detected)
- **Chrome**: `chrome.exe` - Monitors all Google Chrome windows
- **Firefox**: `firefox.exe` - Detects Mozilla Firefox login pages
- **Edge**: `msedge.exe` - Microsoft Edge integration
- **Opera**: `opera.exe` - Opera browser support
- **Brave**: `brave.exe` - Privacy-focused browser support

### **Desktop Applications**
- **Discord**: `discord.exe` - Gaming/community platform
- **Slack**: `slack.exe` - Team communication tool
- **Steam**: `steam.exe` - Gaming platform
- **Outlook**: `outlook.exe` - Microsoft email client
- **Teams**: `teams.exe` - Microsoft collaboration platform

### **Adding Custom Applications**
Edit `config.ini` to add more applications:
```ini
[monitoring]
applications = discord.exe,slack.exe,yourapp.exe
```

## 📊 Monitoring Dashboard Features

### **Real-Time Statistics**
- **Active Monitoring**: Shows current monitoring status
- **Forms Detected**: Count of login forms found today
- **Credentials Saved**: New credentials added
- **Auto-Fills Performed**: Successful auto-fill operations

### **Activity Log Examples**
```
[14:30:25] Monitoring started
[14:32:15] Login detected: user@github.com
[14:32:18] Saved credential for user@github.com
[14:45:02] Auto-fill completed for user@stackoverflow.com
[14:52:33] Declined to save credential for temp@testsite.com
[15:10:45] Monitoring stopped
```

## 🛠️ Advanced Usage

### **Command Line Options**
```powershell
# Standard startup
python main.py

# Silent startup (no GUI)
python main.py --silent

# Start with monitoring enabled
python main.py --monitor

# Debug mode with verbose logging
python main.py --debug
```

### **Configuration File Customization**
Location: `config.ini`
```ini
[monitoring]
browsers = chrome.exe,firefox.exe,msedge.exe
applications = discord.exe,slack.exe,teams.exe
sensitivity = 3
monitor_frequency = 0.5

[autofill]
enabled = true
prompt_timeout = 10
confirm_before_fill = true

[startup]
auto_start_enabled = true
silent_startup = true
auto_begin_monitoring = true

[security]
auto_lock_timeout = 30
clear_clipboard_delay = 30
log_activities = true
```

## 🔍 Troubleshooting Guide

### **Auto-Fill Not Working**
**Problem**: Credentials not auto-filling on familiar sites
**Solutions**:
1. Check if master password is entered correctly
2. Verify the site URL matches saved credential
3. Ensure monitoring is active (Monitor tab)
4. Try running as Administrator for full access
5. Check if site uses non-standard login forms

### **Windows Startup Issues**
**Problem**: SilentLock not starting with Windows
**Solutions**:
1. Check Windows Registry entry: `Win+R` → `regedit` → `HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Run`
2. Verify Python path is correct in registry
3. Try disabling and re-enabling startup in Settings
4. Run SilentLock as Administrator when changing startup settings
5. Check antivirus software isn't blocking startup

### **Monitoring Problems**
**Problem**: Login forms not being detected
**Solutions**:
1. Ensure monitoring is started (green status indicator)
2. Check if browser/app is in the monitored list
3. Try restarting monitoring from Monitor tab
4. Add custom applications to config.ini
5. Adjust sensitivity settings if too conservative

### **Notification Issues**
**Problem**: Not seeing save/auto-fill notifications
**Solutions**:
1. Check Windows notification settings (Windows 10+)
2. Verify notification preferences in Settings tab
3. Look for notifications in Windows Action Center
4. Ensure "Show save notifications" is enabled
5. Test with custom notification fallback

### **Performance Issues**
**Problem**: SilentLock using too much CPU/memory
**Solutions**:
1. Increase monitoring frequency (slower checking)
2. Reduce monitored application list
3. Disable debug logging if enabled
4. Check for conflicting software
5. Use browser-only monitoring instead of universal

## 🎮 Keyboard Shortcuts Reference

### **Global Shortcuts** (when monitoring)
- `Ctrl+Shift+L` - Open SilentLock main window
- `Ctrl+Shift+M` - Toggle monitoring on/off
- `Ctrl+Shift+P` - Pause monitoring temporarily

### **Main Window Shortcuts**
- `Ctrl+N` - Add new credential
- `Ctrl+F` - Focus search box
- `Delete` - Delete selected credential
- `F5` - Refresh credentials list
- `Ctrl+S` - Save changes
- `Escape` - Close dialog/cancel operation

### **During Prompts**
- `Enter` - Accept save/auto-fill prompt
- `Escape` - Cancel/decline prompt
- `Tab` - Navigate between options

## 📱 Integration Examples

### **Browser Integration**
SilentLock works seamlessly with:
- **Multi-tab browsing**: Monitors all open tabs
- **Private/Incognito mode**: Detects but respects privacy
- **Extension compatibility**: Works alongside password managers
- **Cross-domain**: Handles subdomains and redirects

### **Application Integration**
- **Native apps**: Desktop applications with built-in login
- **Electron apps**: Modern web-based desktop applications
- **Legacy software**: Older applications with standard Windows forms
- **Web views**: Applications using embedded web browsers

## 🛡️ Security Best Practices

### **Master Password Security**
1. **Strong Password**: Use unique, complex master password
2. **Regular Updates**: Change master password periodically
3. **Safe Storage**: Don't write down or share master password
4. **Backup Strategy**: Keep encrypted database backups

### **Auto-Fill Security**
1. **Verify Prompts**: Always read auto-fill prompts carefully
2. **Site Verification**: Ensure you're on the correct website
3. **Public Computers**: Disable auto-fill on shared/public devices
4. **Suspicious Activity**: Report unexpected auto-fill attempts

### **System Security**
1. **Administrator Rights**: Only use when necessary
2. **Antivirus Integration**: Ensure SilentLock is whitelisted
3. **System Updates**: Keep Windows and Python updated
4. **Network Security**: SilentLock never transmits credentials

---

**🎉 You're now ready to use SilentLock's complete feature set for secure, intelligent password management!**

For additional help, see:
- `AUTOFILL_GUIDE.md` - Detailed auto-fill documentation
- `MONITORING_GUIDE.md` - Browser and application monitoring
- `SECURITY.md` - Security architecture and privacy details
- `QUICKSTART.md` - 5-minute setup guide