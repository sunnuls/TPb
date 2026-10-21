# Install native scrcpy via winget and print the version.
$ErrorActionPreference = "Continue"

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($machine -or $user) {
        $env:Path = "$machine;$user"
    }
}

function Get-ScrcpyExe {
    Refresh-Path
    $cmd = Get-Command scrcpy -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @(
        "${env:ProgramFiles}\scrcpy\scrcpy.exe",
        "${env:LOCALAPPDATA}\Microsoft\WinGet\Links\scrcpy.exe"
    )
    foreach ($p in $roots) {
        if (Test-Path $p) { return $p }
    }
    $wingetPkgs = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
    if (Test-Path $wingetPkgs) {
        $hit = Get-ChildItem -Path $wingetPkgs -Filter "scrcpy.exe" -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($hit) { return $hit.FullName }
    }
    return $null
}

function Get-ScrcpyVersion([string]$exe) {
    try {
        $out = & $exe --version 2>&1 | Out-String
    } catch {
        return $null
    }
    $m = [regex]::Match($out, "scrcpy\s+([0-9]+\.[0-9]+(?:\.[0-9]+)?)")
    if ($m.Success) { return $m.Groups[1].Value }
    $line = ($out -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -First 1)
    if ($line) { return $line.Trim() }
    return $null
}

Refresh-Path
$exe = Get-ScrcpyExe
if (-not $exe) {
    Write-Host "scrcpy не найден, запускаю winget..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Write-Host "winget не найден. Установите App Installer из Microsoft Store."
        exit 1
    }
    & winget install --id Genymobile.scrcpy --exact --accept-source-agreements --accept-package-agreements
    $code = $LASTEXITCODE
    if ($code -ne 0 -and $code -ne -1978335189) {
        # -1978335189 = already installed
        Write-Host "winget вернул код $code"
    }
    Refresh-Path
    $exe = Get-ScrcpyExe
}

if (-not $exe) {
    Write-Host "scrcpy не установлен: бинарник не найден после winget."
    exit 1
}

$ver = Get-ScrcpyVersion $exe
if (-not $ver) {
    Write-Host "scrcpy найден ($exe), но --version не разобран."
    exit 1
}

Write-Host "scrcpy установлен: версия $ver"
Write-Host "path: $exe"
exit 0
