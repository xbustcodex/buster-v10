#define AppName "Buster AI OS"
#define AppVersion "11.0.0"
#define AppPublisher "xbustcodex"
#define AppURL "https://github.com/xbustcodex/buster-v10"
#define AppExeName "Buster.exe"

[Setup]
AppId={{7D96E9A5-AC9D-4E76-9B62-6A7B9F7E77B1}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

DefaultDirName={autopf}\Buster AI OS
DefaultGroupName=Buster AI OS

OutputDir=..\..\release
OutputBaseFilename=Buster-{#AppVersion}-Setup

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

PrivilegesRequired=admin

DisableDirPage=no
DisableProgramGroupPage=yes

SetupIconFile=..\..\buster\ui\v9\assets\buster.ico

UninstallDisplayIcon={app}\Buster.exe

#LicenseFile=..\..\LICENSE

VersionInfoVersion={#AppVersion}
VersionInfoCompany=xbustcodex
VersionInfoDescription=Buster AI OS
VersionInfoProductName=Buster AI OS
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: desktopicon; Description: "Create Desktop Shortcut"; Flags: unchecked

[Files]

Source: "..\..\dist\Buster\*"; \
DestDir: "{app}"; \
Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]

Name: "{group}\Buster AI OS"; \
Filename: "{app}\Buster.exe"

Name: "{group}\Uninstall Buster AI OS"; \
Filename: "{uninstallexe}"

Name: "{autodesktop}\Buster AI OS"; \
Filename: "{app}\Buster.exe"; \
Tasks: desktopicon

[Run]

Filename: "{app}\Buster.exe"; \
Description: "Launch Buster AI OS"; \
Flags: nowait postinstall skipifsilent

[UninstallDelete]

Type: filesandordirs; Name: "{app}\logs"

Type: filesandordirs; Name: "{app}\temp"

Type: filesandordirs; Name: "{app}\cache"

[Code]

function InitializeSetup(): Boolean;
begin
  Result := True;
end;