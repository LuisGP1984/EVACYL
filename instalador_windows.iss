; Script de Inno Setup para "EVACYL".
;
; Qué hace: toma la carpeta que genera PyInstaller en dist\EVACYL y
; construye un instalador .exe normal de Windows: con asistente de
; instalación, icono propio, acceso directo en el menú de inicio y en el
; escritorio (opcional), y un desinstalador que aparece en
; "Aplicaciones y características" de Windows.
;
; Uso: abrir este archivo con Inno Setup (botón derecho -> Compile, o
; Ctrl+F9 dentro del programa). El instalador resultante queda en la
; carpeta "instalador_salida" junto a este script.
;
; IMPORTANTE: este script asume que ya se ha ejecutado antes
;   pyinstaller empaquetado.spec
; y que por tanto existe la carpeta dist\EVACYL con el ejecutable y
; todos sus archivos dentro.

#define MiApp "EVACYL"
#define MiVersion "1.0"
#define MiAutor "Luis González Posada"
#define MiCarpetaDist "dist\EVACYL"

[Setup]
AppId={{8F2C1A4E-3B5D-4A6F-9C7E-1D2E3F4A5B6C}
AppName={#MiApp}
AppVersion={#MiVersion}
AppPublisher={#MiAutor}
DefaultDirName={autopf}\{#MiApp}
DefaultGroupName={#MiApp}
DisableProgramGroupPage=yes
OutputDir=instalador_salida
OutputBaseFilename=Instalador_EVACYL
Compression=lzma
SolidCompression=yes
SetupIconFile=recursos\icono_app.ico
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "{#MiCarpetaDist}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MiApp}"; Filename: "{app}\EVACYL.exe"
Name: "{group}\Desinstalar {#MiApp}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MiApp}"; Filename: "{app}\EVACYL.exe"; Tasks: escritorio

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el Escritorio"; GroupDescription: "Accesos directos adicionales:"

[Run]
Filename: "{app}\EVACYL.exe"; Description: "Abrir {#MiApp} ahora"; Flags: nowait postinstall skipifsilent
