@echo off
echo 🔨 Building SilentLock MSI with WiX v6.0.2
echo ==========================================

cd /d "C:\Users\brigh\OneDrive\Desktop\Projects\SilentLock\installer"

echo 📋 Checking WiX installation...
wix --version
if errorlevel 1 (
    echo ❌ WiX not found in PATH. Please ensure WiX v6.0.2 is installed and added to PATH.
    echo 💡 Add this to your PATH: C:\Program Files\dotnet\tools\
    pause
    exit /b 1
)

echo ✅ WiX found, building MSI...

echo 🔧 Step 1: Building with WiX v6 (new syntax)
wix build SilentLock-WiX6.wxs -o SilentLock-v6.msi

if errorlevel 1 (
    echo ❌ Build failed. Trying alternative approach...
    echo 🔧 Step 2: Using directory harvesting approach
    
    echo 📁 Harvesting files from dist directory...
    wix extension add WixToolset.Heat.wixext
    heat dir "..\dist\SilentLockPasswordManager" -cg SilentLockFiles -gg -scom -sreg -sfrag -srd -dr INSTALLFOLDER -out SilentLock-Files.wxs
    
    if exist SilentLock-Files.wxs (
        echo ✅ File harvest successful, building complete MSI...
        wix build SilentLock-WiX6.wxs SilentLock-Files.wxs -o SilentLock-Complete-v6.msi
    )
) else (
    echo ✅ Build successful!
)

if exist SilentLock-v6.msi (
    echo 🎉 SUCCESS! MSI created: SilentLock-v6.msi
    dir SilentLock-v6.msi
) else if exist SilentLock-Complete-v6.msi (
    echo 🎉 SUCCESS! MSI created: SilentLock-Complete-v6.msi
    dir SilentLock-Complete-v6.msi
) else (
    echo ❌ No MSI file was created. Check the error messages above.
)

echo.
echo 💡 If build failed, you can also use the portable ZIP:
echo    SilentLock-Portable-v1.0.0.zip is ready for immediate distribution
echo.
echo 📋 For manual WiX installation help:
echo    - Ensure .NET 6+ SDK is installed
echo    - Install WiX: dotnet tool install --global wix
echo    - Add to PATH: C:\Program Files\dotnet\tools\
echo.
pause