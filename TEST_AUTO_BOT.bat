@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   Test Automatic Bot System
echo ========================================
echo.
echo This will test the automatic bot controller.
echo.
pause
echo.

python -m launcher.auto_bot_controller

echo.
echo ========================================
echo.
pause
