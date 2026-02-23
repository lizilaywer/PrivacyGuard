; PrivacyGuard Windows 安装程序配置
; Inno Setup 脚本
; 版本: v37.4.1

#define MyAppName "PrivacyGuard"
#define MyAppNameFull "PrivacyGuard 脱敏卫士"
#define MyAppVersion "37.4.1"
#define MyAppPublisher "PrivacyGuard Team"
#define MyAppURL "https://github.com/privacyguard/privacyguard"
#define MyAppExeName "PrivacyGuard.exe"

[Setup]
; AppId must be unique for each application
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppNameFull}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\..\releases\windows
OutputBaseFilename=PrivacyGuard-{#MyAppVersion}-Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Code]
// Check if Visual C++ Redistributable is installed (with full DLL check)
function IsVCRedistInstalled(): Boolean;
var
  Version: String;
  HasVCR140, HasVCR140_1, HasMSVCP140: Boolean;
begin
  // Check for VC++ 2015-2022 x64 in registry
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Version) then
  begin
    Result := True;
    Exit;
  end
  else if RegQueryStringValue(HKLM64, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Version', Version) then
  begin
    Result := True;
    Exit;
  end;

  // Also check if required DLLs exist in System32
  HasVCR140 := FileExists('C:\Windows\System32\vcruntime140.dll');
  HasVCR140_1 := FileExists('C:\Windows\System32\vcruntime140_1.dll');
  HasMSVCP140 := FileExists('C:\Windows\System32\msvcp140.dll');

  // All three DLLs are required for onnxruntime
  if HasVCR140 and HasVCR140_1 and HasMSVCP140 then
  begin
    Result := True;
  end
  else
  begin
    Result := False;
  end;
end;

// Get missing DLL info for better error message
function GetMissingDLLInfo(): String;
begin
  Result := '';
  if not FileExists('C:\Windows\System32\vcruntime140.dll') then
    Result := Result + '  - vcruntime140.dll' + #13#10;
  if not FileExists('C:\Windows\System32\vcruntime140_1.dll') then
    Result := Result + '  - vcruntime140_1.dll (CRITICAL for OCR)' + #13#10;
  if not FileExists('C:\Windows\System32\msvcp140.dll') then
    Result := Result + '  - msvcp140.dll' + #13#10;
end;

function InitializeSetup(): Boolean;
var
  MissingDLLs: String;
begin
  if not IsVCRedistInstalled() then
  begin
    MissingDLLs := GetMissingDLLInfo();

    MsgBox('Visual C++ Redistributable is required but not detected.' + #13#10 + #13#10 +
           'Missing files:' + #13#10 + MissingDLLs + #13#10 +
           'Please download and install the latest VC++ Redistributable:' + #13#10 +
           'https://aka.ms/vs/17/release/vc_redist.x64.exe' + #13#10 + #13#10 +
           'Note: vcruntime140_1.dll is REQUIRED for OCR functionality.' + #13#10 +
           'After installation, please run this setup again.', mbInformation, MB_OK);

    // Continue anyway - DLLs might be bundled or user might install later
    Result := True;
  end
  else
  begin
    Result := True;
  end;
end;

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "..\..\..\dist\PrivacyGuard\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\..\dist\PrivacyGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Launcher wrapper for DLL checking
Source: "..\scripts\launcher_wrapper.bat"; DestDir: "{app}"; Flags: ignoreversion
; 注意: 不要在任何共享系统文件上使用 "Flags: ignoreversion"

[Icons]
; Use launcher wrapper to check DLLs before starting
Name: "{autoprograms}\{#MyAppNameFull}"; Filename: "{app}\launcher_wrapper.bat"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppNameFull}"; Filename: "{app}\launcher_wrapper.bat"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppNameFull}"; Filename: "{app}\launcher_wrapper.bat"; Tasks: quicklaunchicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
; Use launcher wrapper to check DLLs before starting
Filename: "{app}\launcher_wrapper.bat"; Description: "{cm:LaunchProgram,{#StringChange(MyAppNameFull, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
