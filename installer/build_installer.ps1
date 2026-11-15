# Bouwt eerst dist\RoboCutter.exe (scripts\build_exe.ps1) en compileert
# daarna de Inno Setup-installer (robocutter.iss) eromheen. Vereist een
# lokale Inno Setup-installatie (ISCC.exe, versie 6 of hoger) -- gratis
# te downloaden via https://jrsoftware.org/isinfo.php.
#
# Gebruik:
#   .\installer\build_installer.ps1
#
# Resultaat: installer\Output\RoboCutter-Setup-<versie>.exe

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& .\scripts\build_exe.ps1

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $iscc) {
    $iscc = Get-ChildItem -Path "${env:ProgramFiles(x86)}", "$env:ProgramFiles" -Filter "ISCC.exe" -Recurse -Depth 1 -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $iscc) {
    throw "ISCC.exe (Inno Setup) niet gevonden. Installeer Inno Setup via https://jrsoftware.org/isinfo.php."
}

$versie = (python -c "import sys; sys.path.insert(0, 'src'); import robocutter; print(robocutter.__version__)").Trim()
& $iscc "/DMyAppVersion=$versie" "installer\robocutter.iss"

Write-Host ""
Write-Host "Klaar: installer\Output\RoboCutter-Setup-$versie.exe"
