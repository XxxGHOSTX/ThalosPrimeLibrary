; Thalos Prime Windows bootstrap installer (Setup.exe)

#define MyAppName "Thalos Prime"
#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "ThalosPrime"
#define MyAppExeName "ThalosPrimeLauncher.exe"

[Setup]
AppId={{C605A2E4-EC50-44DE-8876-072A2F1E93E9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Thalos Prime
DefaultGroupName=Thalos Prime
OutputDir=dist
OutputBaseFilename=Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "dist\ThalosPrime\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs

[Icons]
Name: "{group}\Thalos Prime"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Thalos Prime"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Thalos Prime"; Flags: nowait postinstall skipifsilent
