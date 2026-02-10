@echo off
chcp 65001 > nul
echo ============================================
echo   POKER ASSISTANT GUI
echo ============================================
echo.
python poker_gui.py
if errorlevel 1 (
    echo.
    echo Произошла ошибка!
    pause
)
