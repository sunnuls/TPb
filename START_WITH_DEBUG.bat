@echo off
chcp 65001 >nul
title HIVE Launcher - Debug Mode

echo.
echo ====================================
echo 🔍 HIVE Launcher - DEBUG MODE
echo ====================================
echo.
echo Starting launcher with debug viewer...
echo.
echo DEBUG FEATURES:
echo - Visual feedback for bot vision
echo - See detected UI elements
echo - Real-time screen capture
echo - Bounding boxes for buttons
echo - Detection logs
echo.
echo ====================================
echo.

python -m launcher.ui.main_window

if %errorlevel% neq 0 (
    echo.
    echo ❌ Launch failed!
    echo.
    echo Possible reasons:
    echo 1. Python not in PATH
    echo 2. Missing dependencies
    echo 3. Module import errors
    echo.
    echo Run INSTALL_AUTO_NAV.bat to install dependencies.
    echo.
    pause
)
