# Inno Setup script for Tradutor em tempo real
# Place this file in the project root and compile with Inno Setup Compiler (ISCC.exe)

#define MyAppName "Tradutor em tempo real"
#define MyAppVersion "1.0"
#define MyPublisher "SeuNome"
#define MyExeNameLauncher "TradutorLauncher.exe"
#define MyExeNameClipboard "TradutorReal.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
OutputBaseFilename=TradutorSetup
Compression=lzma2
SolidCompression=yes

[Files]
; Instala os executáveis gerados na pasta `dist` do projeto
Source: "{#GetCurrentScriptDir()}\\dist\\{#MyExeNameLauncher}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#GetCurrentScriptDir()}\\dist\\{#MyExeNameClipboard}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName} (Launcher)"; Filename: "{app}\\{#MyExeNameLauncher}"
Name: "{group}\{#MyAppName} (Clipboard)"; Filename: "{app}\\{#MyExeNameClipboard}"
Name: "{userdesktop}\{#MyAppName} (Launcher)"; Filename: "{app}\\{#MyExeNameLauncher}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Run]
Filename: "{app}\\{#MyExeNameLauncher}"; Description: "Executar {#MyAppName} na saída"; Flags: nowait postinstall skipifsilent

[Code]
function GetCurrentScriptDir(Param: String): String;
begin
  Result := ExtractFileDir(ExpandConstant('{srcexe}'));
end;
