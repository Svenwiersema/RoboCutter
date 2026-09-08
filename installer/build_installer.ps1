# Bouwt eerst dist\RoboCutter.exe (scripts\build_exe.ps1) en compileert
# daarna de Inno Setup-installer (robocutter.iss) eromheen. Vereist een
# lokale Inno Setup 6-installatie (ISCC.exe) -- gratis te downloaden via
# https://jrsoftware.org/isinfo.php.
#
# Gebruik:
#   .\installer\build_installer.ps1
#
# Resultaat: installer\Output\RoboCutter-Setup.exe

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

& .\scripts\build_exe.ps1

$candidatePaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $candidatePaths | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "ISCC.exe (Inno Setup 6) niet gevonden. Installeer Inno Setup 6 via https://jrsoftware.org/isinfo.php."
}

& $iscc "installer\robocutter.iss"

Write-Host ""
Write-Host "Klaar: installer\Output\RoboCutter-Setup.exe"
