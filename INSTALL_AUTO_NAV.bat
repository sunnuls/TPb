@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   Install Auto-Navigation Dependencies
echo ========================================
echo.
echo Installing required packages...
echo.

pip install --upgrade pillow opencv-python pytesseract pyautogui pywin32

echo.
echo ========================================
echo.
echo Installation complete!
echo.
echo IMPORTANT: Tesseract OCR
echo ========================================
echo.
echo To use OCR text detection, you need to:
echo 1. Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
echo 2. Install Tesseract
echo 3. Add to PATH
echo.
echo After installing Tesseract, run:
echo    python -m launcher.vision.auto_ui_detector
echo.
pause
