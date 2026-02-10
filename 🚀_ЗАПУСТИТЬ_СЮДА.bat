@echo off
chcp 65001 >nul
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║         🎴  POKER ASSISTANT - ГЛАВНЫЙ ЗАПУСК  🎴          ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo.
echo  Используется AI модель YOLOv8 для детекции карт
echo  Модель: weights\best.pt (yolov8s_playing_cards.pt)
echo.
echo ════════════════════════════════════════════════════════════
echo.

python poker_gui.py

if errorlevel 1 (
    echo.
    echo ════════════════════════════════════════════════════════════
    echo  ❌ ОШИБКА ЗАПУСКА!
    echo ════════════════════════════════════════════════════════════
    echo.
    pause
)
