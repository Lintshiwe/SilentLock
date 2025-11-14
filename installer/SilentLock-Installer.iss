[Setup]
AppName=SilentLock Password Manager
AppVersion=1.0.0
AppPublisher=SilentLock Development Team
AppPublisherURL=https://github.com/silentlock/silentlock
AppSupportURL=https://github.com/silentlock/silentlock
AppUpdatesURL=https://github.com/silentlock/silentlock
DefaultDirName={autopf}\SilentLock Password Manager
DefaultGroupName=SilentLock Password Manager
AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=SilentLock-Setup-InnoSetup
SetupIconFile=..\assets\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
Source: "..\dist\SilentLockPasswordManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SilentLock Password Manager"; Filename: "{app}\SilentLockPasswordManager.exe"
Name: "{group}\{cm:UninstallProgram,SilentLock Password Manager}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\SilentLock Password Manager"; Filename: "{app}\SilentLockPasswordManager.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\SilentLock Password Manager"; Filename: "{app}\SilentLockPasswordManager.exe"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\SilentLockPasswordManager.exe"; Description: "{cm:LaunchProgram,SilentLock Password Manager}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
