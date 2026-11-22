# Builds a Blip release:  .\build_release.ps1 -Version 1.0.1
#   1. puts the version into config.py
#   2. builds dist\Blip\Blip.exe  (build_exe.ps1)
#   3. builds the installer  release\BlipSetup-<version>.exe  (Inno Setup)
#   4. writes release\BlipSetup-<version>.exe.sha256
# Then upload both files to a GitHub release tagged v<version>.
# Developed by Tunes
param([string]$Version = "")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if ($Version) {
    (Get-Content config.py -Raw) -replace 'VERSION = "[^"]*"', "VERSION = `"$Version`"" |
        Set-Content config.py -NoNewline -Encoding utf8
}
$Version = ([regex]::Match((Get-Content config.py -Raw), 'VERSION = "([^"]*)"')).Groups[1].Value
Write-Host "Building Blip $Version"

& .\build_exe.ps1

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 not found. Install it:  winget install JRSoftware.InnoSetup" }
& $iscc /Qp "/DMyAppVersion=$Version" installer.iss
if ($LASTEXITCODE -ne 0) { throw "Installer build failed" }

$setup = "release\BlipSetup-$Version.exe"
$hash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
"$hash  BlipSetup-$Version.exe" | Set-Content "$setup.sha256" -NoNewline -Encoding ascii

Write-Host ""
Write-Host "Upload these to a GitHub release tagged v$($Version):"
Get-Item $setup, "$setup.sha256" | ForEach-Object { Write-Host ("  {0}  ({1:N1} MB)" -f $_.FullName, ($_.Length / 1MB)) }
