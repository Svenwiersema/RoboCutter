# Bouwt een standalone RoboCutter.exe met PyInstaller, voor de eerste
# demo. Hoofdstuk 8 (design/chapters/08-technische-architectuur.md)
# legt Nuitka vast als definitieve keuze voor de echte commerciële
# release (compileert naar machine-code, lastiger te decompileren) --
# PyInstaller is bewust gekozen voor déze eerste demo-build omdat het,
# anders dan Nuitka, geen aparte C-compiler nodig heeft. Vóór de
# commerciële release moet dit script (of een vervanger ervan) naar
# Nuitka overgezet worden.
#
# Gebruik:
#   pip install -e ".[build]"
#   .\scripts\build_exe.ps1
#
# Resultaat: dist\RoboCutter.exe (één bestand, geen installatie nodig
# om 'm te proberen) -- installer\build_installer.ps1 bouwt hier de
# Inno Setup-installer overheen.

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

python -m PyInstaller `
    --name RoboCutter `
    --onefile `
    --windowed `
    --icon "design/assets/logo/robocutter_icon.ico" `
    --add-data "design/assets;design/assets" `
    --paths src `
    --noconfirm `
    --distpath dist `
    --workpath build `
    src/robocutter/ui/app.py

Write-Host ""
Write-Host "Klaar: dist\RoboCutter.exe"
