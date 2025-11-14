@echo off
echo 🔨 Building SilentLock Professional Installers
echo ===============================================
echo.

cd /d "C:\Users\brigh\OneDrive\Desktop\Projects\SilentLock\installer"

echo 📋 Available installer files:
dir SilentLock-Installer.*
echo.

echo 🔧 Building NSIS Installer...
echo ==============================
echo 💡 Looking for NSIS compiler...

:: Try common NSIS installation paths
set NSIS_PATH=
if exist "C:\Program Files (x86)\NSIS\makensis.exe" (
    set NSIS_PATH="C:\Program Files (x86)\NSIS\makensis.exe"
) else if exist "C:\Program Files\NSIS\makensis.exe" (
    set NSIS_PATH="C:\Program Files\NSIS\makensis.exe"
) else (
    echo ❌ NSIS makensis.exe not found in standard locations
    echo 💡 Please run from NSIS installation directory or add to PATH
    echo 📁 Try: "C:\Program Files (x86)\NSIS\makensis.exe"
)

if defined NSIS_PATH (
    echo ✅ Found NSIS at: %NSIS_PATH%
    echo 🔨 Compiling NSIS installer...
    %NSIS_PATH% SilentLock-Installer.nsi
    
    if exist "SilentLock-Setup.exe" (
        echo 🎉 SUCCESS! NSIS installer created: SilentLock-Setup.exe
        dir SilentLock-Setup.exe
    ) else (
        echo ❌ NSIS build failed - check error messages above
    )
) else (
    echo ⚠️ Skipping NSIS build - makensis not found
)

echo.
echo 🔧 Building Inno Setup Installer...
echo ===================================
echo 💡 Looking for Inno Setup compiler...

:: Try common Inno Setup installation paths
set INNO_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\iscc.exe" (
    set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\iscc.exe"
) else if exist "C:\Program Files\Inno Setup 6\iscc.exe" (
    set INNO_PATH="C:\Program Files\Inno Setup 6\iscc.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 5\iscc.exe" (
    set INNO_PATH="C:\Program Files (x86)\Inno Setup 5\iscc.exe"
) else (
    echo ❌ Inno Setup iscc.exe not found in standard locations
    echo 💡 Please run from Inno Setup installation directory or add to PATH
    echo 📁 Try: "C:\Program Files (x86)\Inno Setup 6\iscc.exe"
)

if defined INNO_PATH (
    echo ✅ Found Inno Setup at: %INNO_PATH%
    echo 🔨 Compiling Inno Setup installer...
    %INNO_PATH% SilentLock-Installer.iss
    
    if exist "Output\SilentLock-Setup.exe" (
        echo 🎉 SUCCESS! Inno Setup installer created: Output\SilentLock-Setup.exe
        dir Output\SilentLock-Setup.exe
        copy "Output\SilentLock-Setup.exe" "SilentLock-InnoSetup.exe"
        echo ✅ Copied to: SilentLock-InnoSetup.exe
    ) else (
        echo ❌ Inno Setup build failed - check error messages above
    )
) else (
    echo ⚠️ Skipping Inno Setup build - iscc not found
)

echo.
echo 📋 BUILD SUMMARY
echo ================
echo ✅ Portable ZIP: SilentLock-Portable-v1.0.0.zip (Ready)
if exist "SilentLock-Setup.exe" (
    echo ✅ NSIS Installer: SilentLock-Setup.exe
)
if exist "SilentLock-InnoSetup.exe" (
    echo ✅ Inno Setup Installer: SilentLock-InnoSetup.exe
)
echo.
echo 🎯 DISTRIBUTION OPTIONS:
echo  📦 Portable: Share SilentLock-Portable-v1.0.0.zip (27.3 MB)
echo  🔧 Traditional: Share installer EXE files
echo  🏢 Enterprise: Use MSI (requires WiX + .NET SDK)
echo.
echo 🎉 SilentLock is ready for professional distribution!
echo.
pause