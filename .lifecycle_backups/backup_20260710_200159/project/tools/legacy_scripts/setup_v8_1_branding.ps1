New-Item -ItemType Directory -Force assets, installer | Out-Null

@'
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(8, 1, 0, 0),
    prodvers=(8, 1, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        "040904b0",
        [
          StringStruct("CompanyName", "PrimeTech"),
          StringStruct("FileDescription", "Buster Desktop Companion"),
          StringStruct("FileVersion", "8.1.0"),
          StringStruct("InternalName", "Buster"),
          StringStruct("OriginalFilename", "Buster.exe"),
          StringStruct("ProductName", "Buster Desktop Companion"),
          StringStruct("ProductVersion", "8.1.0"),
          StringStruct("LegalCopyright", "Copyright 2026 PrimeTech")
        ]
      )
    ]),
    VarFileInfo([VarStruct("Translation", [1033, 1200])])
  ]
)
'@ | Set-Content "version_info.txt"

@'
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
SetupIconFile=..\assets\buster.ico
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
'@ | Set-Content "installer/BusterSetup.iss"

Write-Host "Branding + installer files created."
Write-Host "Next: put your icon at assets\buster.ico"