# Start tools/collect_data.py in a separate PowerShell window (non-blocking).
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
    Write-Host "Ошибка: adb не найден в PATH."
    exit 1
}

$serial = $null
$out = & adb devices 2>&1 | Out-String
foreach ($line in ($out -split "`r?`n")) {
    $line = $line.Trim()
    if (-not $line -or $line.StartsWith("List of devices")) { continue }
    $parts = $line -split "\s+"
    if ($parts.Count -ge 2 -and $parts[1] -eq "device") {
        $serial = $parts[0]
        break
    }
}

if (-not $serial) {
    Write-Host "Ошибка: нет устройства со статусом device (adb devices)."
    exit 1
}

$outDir = Join-Path $RepoRoot "dataset\raw\$serial"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$cmd = "Set-Location -LiteralPath '$RepoRoot'; python tools/collect_data.py --serial $serial --interval 2 --out dataset/raw"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd | Out-Null

Write-Host "Сборщик запущен в отдельном окне. Играй через scrcpy. Для остановки - Ctrl+C в окне сборщика."
Write-Host "SERIAL=$serial"
exit 0