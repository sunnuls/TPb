@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   POKER ASSISTANT (CV Detector)
echo ========================================
echo.

python poker_gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] Ошибка!
    pause
)
