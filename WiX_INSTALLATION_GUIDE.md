# 🔨 WiX Toolset Installation & MSI Build Guide

## 🎯 **RECOMMENDED VERSION**

### ✅ **WiX Toolset v3.11.2** (Recommended for SilentLock)

**Why this version?**
- ✅ Most stable and battle-tested
- ✅ Extensive documentation and community support
- ✅ Compatible with our generated `SilentLock.wxs` file
- ✅ Works on all Windows versions (7, 8, 10, 11)
- ✅ No compatibility issues

---

## 📥 **DOWNLOAD & INSTALLATION**

### **Step 1: Download WiX v3.11.2**
🔗 **Download Link**: https://github.com/wixtoolset/wix3/releases/tag/wix3112rtm

**File to Download**: `wix311.exe` (approximately 25 MB)

### **Step 2: Install WiX Toolset**
1. ▶️ **Run `wix311.exe` as Administrator**
2. ✅ **Accept the license agreement**
3. ✅ **Use default installation location**: 
   ```
   C:\Program Files (x86)\WiX Toolset v3.11\
   ```
4. ✅ **Complete installation**

### **Step 3: Verify Installation**
Open **Command Prompt** and test:
```cmd
candle --help
light --help
```

**Expected Result**: You should see help text for both commands

---

## 🛠️ **PATH SETUP (If Commands Not Found)**

If `candle` and `light` commands are not recognized:

### **Add WiX to System PATH**
1. 🔍 **Open System Properties** → Advanced → Environment Variables
2. 🎯 **Find "Path" in System Variables** → Edit
3. ➕ **Add new entry**:
   ```
   C:\Program Files (x86)\WiX Toolset v3.11\bin
   ```
4. ✅ **Save and restart Command Prompt**

---

## 🚀 **BUILD SILENTLOCK MSI INSTALLER**

### **Step 1: Navigate to Installer Directory**
```cmd
cd "C:\Users\brigh\OneDrive\Desktop\Projects\SilentLock\installer"
```

### **Step 2: Compile WiX Source**
```cmd
candle SilentLock.wxs
```

**Expected Output**: Creates `SilentLock.wixobj` file

### **Step 3: Link MSI Package**
```cmd
light SilentLock.wixobj -out SilentLock.msi
```

**Expected Output**: Creates `SilentLock.msi` installer package

### **Step 4: Verify MSI Creation**
```cmd
dir SilentLock.msi
```

**Result**: You should see the MSI file (approximately 30-35 MB)

---

## 🎁 **WHAT THE MSI INSTALLER INCLUDES**

### 📦 **Package Contents**
- ✅ **SilentLockPasswordManager.exe** - Main application
- ✅ **All Dependencies** - Python runtime and libraries
- ✅ **Start Menu Shortcuts** - Easy access for users
- ✅ **Uninstaller** - Clean removal capability
- ✅ **Registry Entries** - Windows integration

### 🎯 **Installation Features**
- ✅ **Professional Windows installer experience**
- ✅ **Automated dependency handling**
- ✅ **System integration (Start Menu, Add/Remove Programs)**
- ✅ **Corporate deployment ready**
- ✅ **Silent installation support** (`/quiet` flag)

---

## 🧪 **TESTING YOUR MSI**

### **Step 1: Test Installation**
```cmd
msiexec /i SilentLock.msi
```

### **Step 2: Verify Installation**
1. ✅ Check Start Menu for "SilentLock Password Manager"
2. ✅ Verify installation in "Add/Remove Programs"
3. ✅ Test application launch

### **Step 3: Test Uninstallation**
```cmd
msiexec /x SilentLock.msi
```

---

## 🎯 **DISTRIBUTION OPTIONS**

### **Option 1: Direct MSI Distribution**
- 📧 **Email** the MSI file (30-35 MB)
- ☁️ **Cloud Storage** (Google Drive, OneDrive, etc.)
- 🌐 **Website Download** link

### **Option 2: Enterprise Deployment**
- 📊 **Group Policy** deployment
- 🏢 **SCCM/WSUS** distribution
- 🖥️ **Silent installation**: `msiexec /i SilentLock.msi /quiet`

### **Option 3: Advanced Customization**
- 🎨 **Custom UI**: Modify WiX source for branded installer
- ⚙️ **Configuration**: Pre-configure settings during installation
- 🔐 **Digital Signing**: Code sign the MSI for security

---

## 🆚 **ALTERNATIVE: If WiX v3.11.2 Has Issues**

### **Try WiX v4.0.x (Latest)**
🔗 **Download**: https://github.com/wixtoolset/wix4/releases

**Note**: May require minor adjustments to `SilentLock.wxs` file

### **Fallback Options**
If WiX installation fails:
1. ✅ **Use Portable ZIP** - Already ready for distribution
2. ✅ **NSIS Installer** - Alternative installer format
3. ✅ **Inno Setup** - User-friendly installer creation

---

## 📋 **TROUBLESHOOTING**

### ❌ **"candle is not recognized"**
**Solution**: Add WiX bin directory to PATH (see PATH Setup section)

### ❌ **"Access denied" during installation**
**Solution**: Run Command Prompt as Administrator

### ❌ **MSI build errors**
**Solution**: Check that `SilentLockPasswordManager.exe` exists in `../dist/SilentLockPasswordManager/`

### ❌ **Installation fails on target system**
**Solution**: Ensure target system has .NET Framework 3.5+ installed

---

## 🎉 **FINAL RESULT**

Once completed, you'll have:
- ✅ **`SilentLock.msi`** - Professional Windows installer package
- ✅ **Corporate deployment ready** - Enterprise installation capability
- ✅ **User-friendly installation** - Standard Windows installer experience
- ✅ **Clean uninstallation** - Proper removal process

**Your SilentLock Password Manager will be distributed as a professional MSI package just like commercial software!** 🏆