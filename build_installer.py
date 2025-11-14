#!/usr/bin/env python3
"""
SilentLock Password Manager - Installer Builder
Creates installable packages for Windows distribution.
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path

class SilentLockInstaller:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.dist_dir = self.project_dir / "dist"
        self.build_dir = self.project_dir / "build"
        self.installer_dir = self.project_dir / "installer"
        self.app_name = "SilentLock Password Manager"
        self.app_version = "1.0.0"
        self.app_description = "Secure, Ethical Password Manager for Personal Use"
        self.app_author = "SilentLock Development Team"
        self.app_url = "https://github.com/silentlock/silentlock"
        
        # Create directories
        self.installer_dir.mkdir(exist_ok=True)
        
    def check_dependencies(self):
        """Check if required tools are installed."""
        print("🔍 Checking build dependencies...")
        
        required_tools = {
            'pyinstaller': 'PyInstaller for executable creation',
            'cx_Freeze': 'cx_Freeze for alternative executable creation',
            'auto-py-to-exe': 'Auto-py-to-exe for GUI-based building'
        }
        
        available_tools = []
        
        for tool, description in required_tools.items():
            try:
                result = subprocess.run([sys.executable, '-c', f'import {tool}'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    available_tools.append(tool)
                    print(f"✅ {tool}: Available")
                else:
                    print(f"❌ {tool}: Not installed - {description}")
            except Exception as e:
                print(f"❌ {tool}: Error checking - {e}")
        
        if not available_tools:
            print("❌ No build tools available. Installing PyInstaller...")
            self.install_build_tools()
        else:
            print(f"✅ Available build tools: {', '.join(available_tools)}")
            
        return available_tools
    
    def install_build_tools(self):
        """Install required build tools."""
        print("📦 Installing build tools...")
        
        tools = [
            'pyinstaller>=5.13.0',
            'cx_Freeze>=6.15.0',
            'auto-py-to-exe>=2.40.0',
            'nsis>=3.8'  # For NSIS installer
        ]
        
        for tool in tools:
            try:
                print(f"Installing {tool}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', tool], check=True)
                print(f"✅ {tool} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {tool}: {e}")
    
    def create_pyinstaller_spec(self):
        """Create PyInstaller spec file for advanced configuration."""
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Project paths
project_dir = Path(r'{self.project_dir}')
src_dir = project_dir / 'src'
assets_dir = project_dir / 'assets'
config_dir = project_dir / 'config'

# Data files to include
datas = [
    (str(assets_dir), 'assets'),
    (str(config_dir), 'config'),
    ('requirements.txt', '.'),
    ('README.md', '.'),
    ('USER_MANUAL.md', '.'),
]

# Hidden imports (dependencies that PyInstaller might miss)
hiddenimports = [
    'tkinter',
    'tkinter.ttk',
    'tkinter.messagebox',
    'tkinter.filedialog',
    'cryptography',
    'cryptography.fernet',
    'pynput',
    'pynput.keyboard',
    'pynput.mouse',
    'pywin32',
    'win32gui',
    'win32process',
    'win32api',
    'win32con',
    'pillow',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'pyperclip',
    'psutil',
    'plyer',
    'plyer.platforms.win.notification',
    'requests',
    'qrcode',
    'pyotp',
    'zxcvbn',
    'fido2',
    'sqlite3',
    'threading',
    'queue',
    'collections',
    'json',
    'base64',
    'hashlib',
    'hmac',
    'secrets',
    'datetime',
    'time',
    'os',
    'sys',
    'pathlib',
    'configparser',
]

a = Analysis(
    ['main.py'],
    pathex=[str(project_dir), str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'numpy',
        'pandas',
        'jupyter',
        'notebook',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{self.app_name.replace(" ", "")}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to False for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(assets_dir / 'logo.ico'),
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{self.app_name.replace(" ", "")}',
)
'''
        
        spec_file = self.project_dir / "SilentLock.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)
        
        print(f"✅ PyInstaller spec file created: {spec_file}")
        return spec_file
    
    def create_version_info(self):
        """Create version info file for Windows executable."""
        version_info = f'''# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({self.app_version.replace('.', ', ')}, 0),
    prodvers=({self.app_version.replace('.', ', ')}, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{self.app_author}'),
        StringStruct(u'FileDescription', u'{self.app_description}'),
        StringStruct(u'FileVersion', u'{self.app_version}'),
        StringStruct(u'InternalName', u'SilentLock'),
        StringStruct(u'LegalCopyright', u'Copyright © 2025 {self.app_author}'),
        StringStruct(u'OriginalFilename', u'SilentLock.exe'),
        StringStruct(u'ProductName', u'{self.app_name}'),
        StringStruct(u'ProductVersion', u'{self.app_version}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
        
        version_file = self.project_dir / "version_info.txt"
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(version_info)
        
        print(f"✅ Version info file created: {version_file}")
        return version_file
    
    def build_with_pyinstaller(self):
        """Build executable using PyInstaller."""
        print("🔨 Building with PyInstaller...")
        
        # Create spec file
        spec_file = self.create_pyinstaller_spec()
        version_file = self.create_version_info()
        
        try:
            # Clean previous builds
            if self.dist_dir.exists():
                shutil.rmtree(self.dist_dir)
            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
            
            # Build using spec file
            cmd = [
                sys.executable, '-m', 'PyInstaller',
                '--clean',
                '--noconfirm',
                str(spec_file)
            ]
            
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ PyInstaller build completed successfully!")
                
                # Check if executable was created
                exe_path = self.dist_dir / self.app_name.replace(" ", "") / f"{self.app_name.replace(' ', '')}.exe"
                if exe_path.exists():
                    print(f"✅ Executable created: {exe_path}")
                    return exe_path
                else:
                    print(f"❌ Executable not found at expected location: {exe_path}")
                    return None
            else:
                print(f"❌ PyInstaller build failed:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"❌ Error during PyInstaller build: {e}")
            return None
    
    def create_nsis_installer_script(self, exe_path):
        """Create NSIS installer script."""
        nsis_script = f'''!define APPNAME "{self.app_name}"
!define COMPANYNAME "{self.app_author}"
!define DESCRIPTION "{self.app_description}"
!define VERSIONMAJOR 1
!define VERSIONMINOR 0
!define VERSIONBUILD 0
!define HELPURL "{self.app_url}"
!define UPDATEURL "{self.app_url}"
!define ABOUTURL "{self.app_url}"
!define INSTALLSIZE 50000  # Estimated size in KB

RequestExecutionLevel admin
InstallDir "$PROGRAMFILES\\${{APPNAME}}"
Name "${{APPNAME}}"
Icon "assets\\logo.ico"
OutFile "installer\\SilentLock-Setup.exe"

# Create installer pages
Page directory
Page instfiles

# Uninstaller pages
UninstPage uninstConfirm
UninstPage instfiles

Section "Install"
    # Set output path
    SetOutPath $INSTDIR
    
    # Copy files
    File /r "dist\\{self.app_name.replace(" ", "")}\\*.*"
    
    # Create start menu shortcut
    CreateDirectory "$SMPROGRAMS\\${{APPNAME}}"
    CreateShortcut "$SMPROGRAMS\\${{APPNAME}}\\${{APPNAME}}.lnk" "$INSTDIR\\{self.app_name.replace(' ', '')}.exe"
    CreateShortcut "$SMPROGRAMS\\${{APPNAME}}\\Uninstall.lnk" "$INSTDIR\\uninstall.exe"
    
    # Create desktop shortcut
    CreateShortcut "$DESKTOP\\${{APPNAME}}.lnk" "$INSTDIR\\{self.app_name.replace(' ', '')}.exe"
    
    # Create uninstaller
    WriteUninstaller "$INSTDIR\\uninstall.exe"
    
    # Registry entries
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayName" "${{APPNAME}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "UninstallString" "$\\"$INSTDIR\\uninstall.exe$\\""
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "QuietUninstallString" "$\\"$INSTDIR\\uninstall.exe$\\" /S"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "InstallLocation" "$\\"$INSTDIR$\\""
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayIcon" "$\\"$INSTDIR\\{self.app_name.replace(' ', '')}.exe$\\""
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "Publisher" "${{COMPANYNAME}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "HelpLink" "${{HELPURL}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "URLUpdateInfo" "${{UPDATEURL}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "URLInfoAbout" "${{ABOUTURL}}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "DisplayVersion" "${{VERSIONMAJOR}}.${{VERSIONMINOR}}.${{VERSIONBUILD}}"
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "VersionMajor" ${{VERSIONMAJOR}}
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "VersionMinor" ${{VERSIONMINOR}}
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "NoModify" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "NoRepair" 1
    WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}" "EstimatedSize" ${{INSTALLSIZE}}
    
SectionEnd

Section "Uninstall"
    # Remove files
    RMDir /r "$INSTDIR"
    
    # Remove start menu shortcuts
    RMDir /r "$SMPROGRAMS\\${{APPNAME}}"
    
    # Remove desktop shortcut
    Delete "$DESKTOP\\${{APPNAME}}.lnk"
    
    # Remove registry entries
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${{APPNAME}}"
    
SectionEnd
'''
        
        nsis_file = self.installer_dir / "SilentLock-Installer.nsi"
        with open(nsis_file, 'w', encoding='utf-8') as f:
            f.write(nsis_script)
        
        print(f"✅ NSIS installer script created: {nsis_file}")
        return nsis_file
    
    def create_inno_setup_script(self, exe_path):
        """Create Inno Setup installer script."""
        inno_script = f'''[Setup]
AppName={self.app_name}
AppVersion={self.app_version}
AppPublisher={self.app_author}
AppPublisherURL={self.app_url}
AppSupportURL={self.app_url}
AppUpdatesURL={self.app_url}
DefaultDirName={{autopf}}\\{self.app_name}
DefaultGroupName={self.app_name}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=SilentLock-Setup-InnoSetup
SetupIconFile=assets\\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{{cm:CreateQuickLaunchIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
Source: "dist\\{self.app_name.replace(' ', '')}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{self.app_name}"; Filename: "{{app}}\\{self.app_name.replace(' ', '')}.exe"
Name: "{{group}}\\{{cm:UninstallProgram,{self.app_name}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{self.app_name}"; Filename: "{{app}}\\{self.app_name.replace(' ', '')}.exe"; Tasks: desktopicon
Name: "{{userappdata}}\\Microsoft\\Internet Explorer\\Quick Launch\\{self.app_name}"; Filename: "{{app}}\\{self.app_name.replace(' ', '')}.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{{app}}\\{self.app_name.replace(' ', '')}.exe"; Description: "{{cm:LaunchProgram,{self.app_name}}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}"
'''
        
        inno_file = self.installer_dir / "SilentLock-Installer.iss"
        with open(inno_file, 'w', encoding='utf-8') as f:
            f.write(inno_script)
        
        print(f"✅ Inno Setup installer script created: {inno_file}")
        return inno_file
    
    def create_wix_installer(self, exe_path):
        """Create WiX Toolset installer configuration for MSI."""
        # Create WiX configuration
        wix_config = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
  <Product Id="*" 
           Name="{self.app_name}" 
           Language="1033" 
           Version="{self.app_version}.0" 
           Manufacturer="{self.app_author}" 
           UpgradeCode="{{12345678-1234-1234-1234-123456789012}}">
    
    <Package InstallerVersion="200" 
             Compressed="yes" 
             InstallScope="perMachine" 
             Description="{self.app_description}"
             Comments="{self.app_description}"
             Manufacturer="{self.app_author}" />
    
    <MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." />
    <MediaTemplate EmbedCab="yes" />
    
    <Feature Id="ProductFeature" Title="{self.app_name}" Level="1">
      <ComponentGroupRef Id="ProductComponents" />
    </Feature>
    
    <Directory Id="TARGETDIR" Name="SourceDir">
      <Directory Id="ProgramFilesFolder">
        <Directory Id="INSTALLFOLDER" Name="{self.app_name}" />
      </Directory>
      <Directory Id="ProgramMenuFolder">
        <Directory Id="ApplicationProgramsFolder" Name="{self.app_name}"/>
      </Directory>
      <Directory Id="DesktopFolder" Name="Desktop"/>
    </Directory>
    
    <ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER">
      <Component Id="MainExecutable">
        <File Id="MainEXE" 
              Source="dist\\{self.app_name.replace(' ', '')}\\{self.app_name.replace(' ', '')}.exe" 
              KeyPath="yes" 
              Checksum="yes">
          <Shortcut Id="desktopShortcut" 
                    Directory="DesktopFolder" 
                    Name="{self.app_name}" 
                    WorkingDirectory="INSTALLFOLDER" 
                    Icon="MainIcon" />
          <Shortcut Id="startMenuShortcut" 
                    Directory="ApplicationProgramsFolder" 
                    Name="{self.app_name}" 
                    WorkingDirectory="INSTALLFOLDER" 
                    Icon="MainIcon" />
        </File>
      </Component>
    </ComponentGroup>
    
    <Icon Id="MainIcon" SourceFile="assets\\logo.ico" />
    <Property Id="ARPPRODUCTICON" Value="MainIcon" />
    
  </Product>
</Wix>
'''
        
        wix_file = self.installer_dir / "SilentLock.wxs"
        with open(wix_file, 'w', encoding='utf-8') as f:
            f.write(wix_config)
        
        print(f"✅ WiX installer configuration created: {wix_file}")
        return wix_file
    
    def create_portable_package(self, exe_path):
        """Create portable ZIP package."""
        print("📦 Creating portable package...")
        
        try:
            import zipfile
            
            portable_zip = self.installer_dir / f"SilentLock-Portable-v{self.app_version}.zip"
            
            with zipfile.ZipFile(portable_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add executable and all files
                dist_folder = exe_path.parent
                for file_path in dist_folder.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(dist_folder)
                        zf.write(file_path, arcname)
                
                # Add documentation
                docs = ['README.md', 'USER_MANUAL.md', 'QUICKSTART.md']
                for doc in docs:
                    doc_path = self.project_dir / doc
                    if doc_path.exists():
                        zf.write(doc_path, doc)
            
            print(f"✅ Portable package created: {portable_zip}")
            return portable_zip
            
        except Exception as e:
            print(f"❌ Error creating portable package: {e}")
            return None
    
    def build_all(self):
        """Build all installer types."""
        print(f"🚀 Building {self.app_name} v{self.app_version} installers...")
        print("=" * 60)
        
        # Check dependencies
        available_tools = self.check_dependencies()
        
        # Build executable
        exe_path = self.build_with_pyinstaller()
        
        if not exe_path:
            print("❌ Failed to build executable. Cannot create installers.")
            return False
        
        results = []
        
        # Create installer scripts
        print("\n📝 Creating installer scripts...")
        
        # NSIS Installer
        nsis_script = self.create_nsis_installer_script(exe_path)
        results.append(("NSIS Script", nsis_script))
        
        # Inno Setup Installer
        inno_script = self.create_inno_setup_script(exe_path)
        results.append(("Inno Setup Script", inno_script))
        
        # WiX MSI Installer
        wix_script = self.create_wix_installer(exe_path)
        results.append(("WiX MSI Script", wix_script))
        
        # Portable Package
        portable_zip = self.create_portable_package(exe_path)
        if portable_zip:
            results.append(("Portable ZIP", portable_zip))
        
        # Summary
        print(f"\n🎉 BUILD COMPLETE!")
        print("=" * 60)
        print(f"✅ Executable: {exe_path}")
        print(f"📁 Dist Directory: {self.dist_dir}")
        print(f"📦 Installer Directory: {self.installer_dir}")
        print("\n📋 Created Files:")
        
        for name, path in results:
            if path and path.exists():
                print(f"  ✅ {name}: {path}")
            else:
                print(f"  ❌ {name}: Failed to create")
        
        print("\n📝 Next Steps:")
        print("1. Test the executable in the dist folder")
        print("2. Use the installer scripts with appropriate tools:")
        print("   - NSIS: Use NSIS compiler to build the installer")
        print("   - Inno Setup: Use Inno Setup compiler to build the installer")
        print("   - WiX: Use WiX Toolset to build MSI installer")
        print("3. Distribute the portable ZIP for users who prefer portable apps")
        
        return True

def main():
    """Main installer builder function."""
    print("🔨 SilentLock Installer Builder")
    print("=" * 40)
    
    installer = SilentLockInstaller()
    success = installer.build_all()
    
    if success:
        print("\n✅ All installer packages created successfully!")
        print("🎯 Your SilentLock application is ready for distribution!")
    else:
        print("\n❌ Some errors occurred during the build process.")
        print("Please check the output above for details.")

if __name__ == "__main__":
    main()