; Blip installer (Inno Setup 6).  Build with:  .\build_release.ps1
; Installs per user (no admin needed) to %LOCALAPPDATA%\Programs\Blip.
; Your Blip data in %APPDATA%\Blip (settings, memory, progress) is never touched by
; installing or updating.
; Developed by Tunes

#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppName "Blip"
#define MyAppPublisher "Tunes"
#define MyAppExe "Blip.exe"

[Setup]
AppId={{6B1E4C2A-8F3D-4B7E-9A51-3C2D7E8F1B90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/TunesDev/Blip
AppSupportURL=https://github.com/TunesDev/Blip/issues
AppUpdatesURL=https://github.com/TunesDev/Blip/releases
DefaultDirName={localappdata}\Programs\Blip
DefaultGroupName=Blip
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=BlipSetup-{#MyAppVersion}
SetupIconFile=assets\blip.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=force
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start Blip with Windows"; GroupDescription: "Start-up:"

[Files]
Source: "dist\Blip\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Blip"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\Blip"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Blip"; ValueData: """{app}\{#MyAppExe}"""; Tasks: startup

[Run]
; normal install: offer to start Blip at the end
Filename: "{app}\{#MyAppExe}"; Description: "Start Blip now"; Flags: nowait postinstall skipifsilent
; silent update (started by Blip itself with /UPDATE): start Blip again afterwards
Filename: "{app}\{#MyAppExe}"; Flags: nowait; Check: IsUpdate

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExe}"; Flags: runhidden; RunOnceId: "StopBlip"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function IsUpdate: Boolean;
begin
  Result := Pos('/UPDATE', UpperCase(GetCmdTail)) > 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Value: String;
begin
  { remove Blip's "start with Windows" entry, but only if it points at this install }
  if CurUninstallStep = usPostUninstall then
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'Blip', Value) then
      if Pos(Lowercase(ExpandConstant('{app}')), Lowercase(Value)) > 0 then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'Blip');
end;
