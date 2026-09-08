; Inno Setup-script voor de RoboCutter-installer (eerste demo-build).
; Hoofdstuk 8 (design/chapters/08-technische-architectuur.md) legt Inno
; Setup vast als de gekozen installer-tool. Code signing (ook genoemd in
; hoofdstuk 8, voorkomt Windows' "onbekende uitgever"-waarschuwing) is
; hier bewust nog NIET opgezet -- er is nog geen certificaat; voor de
; echte release moet dit alsnog toegevoegd worden (Sign Tool-sectie
; hieronder staat uitgecommentarieerd als startpunt).
;
; Vereist: dist\RoboCutter.exe (gebouwd via scripts\build_exe.ps1) moet
; al bestaan voordat dit script gecompileerd wordt -- zie
; installer\build_installer.ps1, die beide stappen na elkaar uitvoert.

#define MyAppName "RoboCutter"
#define MyAppVersion "0.1.0-demo"
#define MyAppPublisher "RoboCutter"
#define MyAppExeName "RoboCutter.exe"

[Setup]
AppId={{9F6C7B7E-7B0B-4B9E-9F0B-2C6C6E6B9C4A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=Output
OutputBaseFilename=RoboCutter-Setup
SetupIconFile=..\design\assets\logo\robocutter_icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Geen adminrechten nodig zolang er per-user geïnstalleerd wordt
; ({autopf} kiest zelf Program Files met adminrechten, of de per-user
; map zonder -- "lowest" laat de gebruiker kiezen bij de installatie).
PrivilegesRequired=lowest

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"

[Tasks]
Name: "desktopicon"; Description: "Snelkoppeling op het bureaublad plaatsen"; GroupDescription: "Extra snelkoppelingen:"

[Files]
Source: "..\dist\RoboCutter.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Verwijder {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} nu starten"; Flags: nowait postinstall skipifsilent
