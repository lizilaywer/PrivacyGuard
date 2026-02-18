; PrivacyGuard Windows 安装程序配置
; Inno Setup 脚本

#define MyAppName "PrivacyGuard"
#define MyAppNameFull "PrivacyGuard 脱敏卫士"
#define MyAppVersion "37.0"
#define MyAppPublisher "PrivacyGuard Team"
#define MyAppURL "https://github.com/privacyguard/privacyguard"
#define MyAppExeName "PrivacyGuard.exe"

[Setup]
; 注意: AppId 的值为唯一标识此应用程序。
; 不要在其他应用程序的安装程序中使用相同的 AppId 值。
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppNameFull}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; 移除以下行以在安装程序中显示许可协议页面
; LicenseFile=LICENSE.txt
; 移除以下行以在安装程序中显示发布信息页面
; InfoBeforeFile=README.md
; 移除以下行以在安装程序中显示发布信息后页面
; InfoAfterFile=README.md
OutputDir=..\..\..\releases\windows
OutputBaseFilename=PrivacyGuard-{#MyAppVersion}-Setup
SetupIconFile=..\assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "..\..\..\dist\PrivacyGuard\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\..\dist\PrivacyGuard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 注意: 不要在任何共享系统文件上使用 "Flags: ignoreversion"

[Icons]
Name: "{autoprograms}\{#MyAppNameFull}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppNameFull}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppNameFull}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppNameFull, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
