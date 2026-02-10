@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo   УСТАНОВКА OpenCV
echo ==========================================
echo.

echo [1/2] Установка opencv-python...
pip install opencv-python

if errorlevel 1 (
    echo.
    echo [ERROR] Ошибка установки!
    pause
    exit /b 1
)

echo.
echo [2/2] Проверка установки...
python -c "import cv2; print(f'✓ OpenCV {cv2.__version__} установлен успешно!')"

if errorlevel 1 (
    echo.
    echo [ERROR] OpenCV не импортируется!
    pause
    exit /b 1
)

echo.
echo ==========================================
echo   ✓ УСТАНОВКА ЗАВЕРШЕНА
echo ==========================================
echo.
pause
