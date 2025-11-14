# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Project paths
project_dir = Path(r'C:\Users\brigh\OneDrive\Desktop\Projects\SilentLock')
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
    hooksconfig={},
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
    name='SilentLockPasswordManager',
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
    name='SilentLockPasswordManager',
)
