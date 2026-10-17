param(
    [string]$GamePath = "C:\Program Files (x86)\Steam\steamapps\common\Mortal Kombat Arcade Kollection",
    [string]$DllPath = "",
    [switch]$NoBackup
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
if (-not $DllPath) {
    $DllPath = Join-Path $root "build\Release\xlive.dll"
    if (-not (Test-Path -LiteralPath $DllPath)) {
        $bundledDll = Join-Path $PSScriptRoot "xlive.dll"
        if (Test-Path -LiteralPath $bundledDll) {
            $DllPath = $bundledDll
        }
    }
}

$win32Path = Join-Path $GamePath "BINARIES\WIN32"
$target = Join-Path $win32Path "xlive.dll"

if (-not (Test-Path -LiteralPath $DllPath)) {
    throw "Source DLL was not found: $DllPath. Build first with .\scripts\build-vs2022.ps1."
}

if (-not (Test-Path -LiteralPath $win32Path)) {
    throw "MKAK WIN32 folder was not found: $win32Path"
}

$process = Get-Process MKHDGame -ErrorAction SilentlyContinue
if ($process) {
    throw "MKHDGame.exe is running. Close the game before installing."
}

if ((Test-Path -LiteralPath $target) -and -not $NoBackup) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = Join-Path $win32Path "xlive.dll.backup-$stamp"
    Copy-Item -LiteralPath $target -Destination $backup -Force
    Write-Host "Backed up existing xlive.dll to: $backup"
}

Copy-Item -LiteralPath $DllPath -Destination $target -Force

Write-Host "Installed: $target"
Write-Host ""
Write-Host "Installed DLL hash:"
Get-FileHash -Algorithm SHA256 $target | Format-List
