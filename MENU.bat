@echo off
chcp 65001 >nul
cd /d "%~dp0"

:MENU
cls
echo.
echo ========================================
echo   HIVE LAUNCHER v0.4.0
echo   Educational Research Only
echo ========================================
echo.
echo Выберите действие:
echo.
echo   1. 🚀 Запустить Launcher
echo   2. 📦 Установить зависимости
echo   3. 🤖 Тест Auto-Navigation
echo   4. 📖 Открыть документацию
echo   5. ❌ Выход
echo.
echo ========================================
echo.

set /p choice="Ваш выбор (1-5): "

if "%choice%"=="1" goto START_LAUNCHER
if "%choice%"=="2" goto INSTALL
if "%choice%"=="3" goto TEST
if "%choice%"=="4" goto DOCS
if "%choice%"=="5" goto EXIT

echo.
echo Неверный выбор!
timeout /t 2 >nul
goto MENU

:START_LAUNCHER
echo.
echo Запуск HIVE Launcher...
echo.
python -m launcher.ui.main_window
if errorlevel 1 (
    echo.
    echo Ошибка запуска!
    echo.
    pause
)
goto MENU

:INSTALL
echo.
echo Установка зависимостей...
echo.
pip install --upgrade pyqt6 pillow opencv-python pytesseract pyautogui pywin32
echo.
echo ========================================
echo Установка завершена!
echo.
echo ВАЖНО: Установите Tesseract OCR
echo https://github.com/UB-Mannheim/tesseract/wiki
echo ========================================
echo.
pause
goto MENU

:TEST
echo.
echo Тест Auto-Navigation...
echo.
python -m launcher.vision.auto_ui_detector
echo.
pause
goto MENU

:DOCS
echo.
echo Документация:
echo.
echo   README_LAUNCHER.md        - Обзор
echo   QUICK_START_AUTO_NAV.md   - Быстрый старт
echo   COMPLETE_GUIDE.md         - Полное руководство
echo   FINAL_SUMMARY.md          - Итоговая сводка
echo.
echo Открыть README_LAUNCHER.md? (Y/N)
set /p open_docs="Ваш выбор: "

if /i "%open_docs%"=="Y" (
    start README_LAUNCHER.md
)
echo.
pause
goto MENU

:EXIT
echo.
echo До свидания!
echo.
timeout /t 2 >nul
exit
