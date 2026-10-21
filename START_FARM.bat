@echo off
title HIVE FARM LAUNCHER
color 0A

REM === ДОБАВЬ ЭТУ СТРОКУ ===
cd /d "%~dp0"
REM =========================

echo ==========================================
echo   HIVE CONTROL: Запуск фермы
echo ==========================================
echo.

echo [1/3] Проверка ADB...
adb devices | find "device" >nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Телефон не найден! Проверь USB и отладку.
    pause
    exit
)
echo [OK] Телефон подключен.
echo.

echo [2/3] Запуск дашборда (порт 8000)...
start "HIVE Dashboard" cmd /k "python control/start.py"
timeout /t 3 /nobreak >nul
echo [OK] Дашборд запускается...
echo.

echo [3/3] Запуск сборщика датасета...
start "HIVE Data Collector" cmd /k "python tools/collect_data.py --serial e2d0507 --interval 2 --out dataset/raw"
echo [OK] Сборщик запущен.
echo.

echo ==========================================
echo   ВСЁ ЗАПУЩЕНО!
echo   1. Открой браузер: http://127.0.0.1:8000
echo   2. Кликни на плитку -> кнопка "scrcpy 60fps"
echo   3. Играй. Сборщик пишет кадры в фоне.
echo   4. Чтобы остановить: просто закрой черные окна консоли.
echo ==========================================
echo.
pause