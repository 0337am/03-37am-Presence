#define MyAppDisplayName "03:37am Presence"
#define MyInstallName "03-37am Presence"
#define MyAppPublisher "0337am"
#define MyAppExeName "03-37am Presence.exe"

#ifndef MyAppVersion
  #error MyAppVersion must be supplied by the release build script.
#endif

#ifndef MyReleaseName
  #error MyReleaseName must be supplied by the release build script.
#endif

[Setup]
AppId=0337am.Presence.Desktop
AppName={#MyAppDisplayName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppDisplayName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}

SourceDir=..
DefaultDirName={autopf}\{#MyInstallName}
DefaultGroupName={#MyInstallName}
DisableProgramGroupPage=yes

OutputDir=release
OutputBaseFilename=03-37am-Presence-Setup-v{#MyAppVersion}

SetupIconFile=icons\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

CloseApplications=yes
RestartApplications=no

VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDisplayName} - {#MyReleaseName}
VersionInfoProductName={#MyAppDisplayName}
VersionInfoProductVersion={#MyAppVersion}.0

[Files]
Source: "dist\03-37am Presence.exe"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyInstallName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{commondesktop}\{#MyInstallName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{cmd}"; Parameters: "/D /C ""set PYINSTALLER_RESET_ENVIRONMENT=1&&start """" /D ""{app}"" ""{app}\{#MyAppExeName}"""""; Description: "Launch {#MyAppDisplayName}"; Flags: runhidden nowait postinstall skipifsilent
