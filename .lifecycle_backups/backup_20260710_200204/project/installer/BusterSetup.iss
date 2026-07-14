[Setup]
AppName=Buster Desktop Companion
AppVersion=8.1.0
AppPublisher=PrimeTech
DefaultDirName={autopf}\Buster Desktop Companion
DefaultGroupName=Buster Desktop Companion
OutputDir=..\dist
OutputBaseFilename=BusterSetup-8.1.0
Compression=lzma
SolidCompression=yes
WizardStyle=modern
;SetupIconFile=..\assets\buster.ico
UninstallDisplayIcon={app}\Buster.exe

[Files]
Source: "..\dist\Buster\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Buster Desktop Companion"; Filename: "{app}\Buster.exe"
Name: "{group}\Uninstall Buster Desktop Companion"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Buster Desktop Companion"; Filename: "{app}\Buster.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\Buster.exe"; Description: "Launch Buster Desktop Companion"; Flags: nowait postinstall skipifsilent
