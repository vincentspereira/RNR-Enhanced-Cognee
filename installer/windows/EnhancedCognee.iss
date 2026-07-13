; RNR Enhanced Cognee - Inno Setup installer script
; Build via installer\build\build_windows.ps1 (which compiles the launcher
; with PyInstaller first), or directly:
;   iscc /DAppVersion=1.0.0 installer\windows\EnhancedCognee.iss

#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{8E2B2F4D-5A1C-4C9D-9B7E-EC0A1EE5C0DE}
AppName=RNR Enhanced Cognee
AppVersion={#AppVersion}
AppPublisher=RNR Enhanced Cognee Team
AppPublisherURL=https://github.com/vincentspereira/enhanced-cognee
DefaultDirName={autopf}\RNR Enhanced Cognee
DefaultGroupName=RNR Enhanced Cognee
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=EnhancedCognee-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName=RNR Enhanced Cognee

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\EnhancedCogneeLauncher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\RNR Enhanced Cognee"; Filename: "{app}\EnhancedCogneeLauncher.exe"
Name: "{group}\{cm:UninstallProgram,RNR Enhanced Cognee}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\RNR Enhanced Cognee"; Filename: "{app}\EnhancedCogneeLauncher.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EnhancedCogneeLauncher.exe"; Description: "{cm:LaunchProgram,RNR Enhanced Cognee}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Keep user data (%LOCALAPPDATA%\EnhancedCognee) - memories survive reinstall
Type: filesandordirs; Name: "{app}"
