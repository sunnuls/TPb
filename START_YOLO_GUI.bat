@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   ЗАПУСК POKER ASSISTANT (YOLO AI)
echo ========================================
echo.

python poker_gui.py

if errorlevel 1 (
    echo.
    echo [ERROR] Ошибка запуска!
    pause
)
