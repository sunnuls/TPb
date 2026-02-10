@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   HIVE LAUNCHER - Educational Research
echo ========================================
echo.
echo Starting launcher...
echo.

python -m launcher.ui.main_window

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start launcher
    echo.
    pause
)
