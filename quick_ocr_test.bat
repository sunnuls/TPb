@echo off
chcp 65001 > nul
echo ============================================
echo 🎴 БЫСТРЫЙ ТЕСТ OCR РАСПОЗНАВАНИЯ
echo ============================================
echo.

REM Проверка виртуального окружения
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ Виртуальное окружение не найдено!
    echo.
    echo Создайте окружение командой:
    echo    python -m venv .venv
    echo.
    pause
    exit /b 1
)

REM Активация окружения
echo 🔧 Активация виртуального окружения...
call .venv\Scripts\activate.bat

REM Проверка зависимостей
echo.
echo 🔧 Проверка зависимостей...
python -c "import PIL" 2>nul
if errorlevel 1 (
    echo ⚠️ Устанавливаю зависимости...
    pip install pillow pytesseract pyyaml
)

REM Проверка Tesseract
echo.
echo 🔧 Проверка Tesseract OCR...
tesseract --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ❌ Tesseract OCR не найден!
    echo.
    echo 📥 Скачайте и установите Tesseract:
    echo    https://github.com/UB-Mannheim/tesseract/wiki
    echo.
    echo После установки добавьте в PATH:
    echo    C:\Program Files\Tesseract-OCR
    echo.
    pause
    exit /b 1
)

echo ✅ Tesseract найден!

REM Проверка файлов
echo.
echo 🔧 Проверка файлов...

set SCREENSHOT=screenshot_test.png
set CONFIG=poker_table_config.yaml

REM Ищем скриншот
if exist "photo_2026-01-16_19-35-24.jpg" set SCREENSHOT=photo_2026-01-16_19-35-24.jpg
if exist "screenshot.png" set SCREENSHOT=screenshot.png

REM Ищем конфиг
if exist "poker_table_config (1).yaml" set CONFIG=poker_table_config (1).yaml

echo 📄 Скриншот: %SCREENSHOT%
echo 📄 Конфиг: %CONFIG%

if not exist "%SCREENSHOT%" (
    echo.
    echo ❌ Скриншот не найден!
    echo.
    echo 💡 Положите скриншот покерного стола в папку:
    echo    %CD%
    echo.
    echo Поддерживаемые форматы: .png, .jpg, .jpeg
    echo.
    pause
    exit /b 1
)

if not exist "%CONFIG%" (
    echo.
    echo ❌ Конфиг не найден!
    echo.
    echo 💡 Скопируйте скачанный файл из браузера:
    echo    poker_table_config (1).yaml
    echo.
    echo В папку проекта:
    echo    %CD%
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================
echo ▶️ ЗАПУСК ТЕСТА OCR
echo ============================================
echo.

REM Запуск теста
python tests/manual/test_real_ocr.py "%SCREENSHOT%" "%CONFIG%"

echo.
echo ============================================
echo ✅ ТЕСТ ЗАВЕРШЕН
echo ============================================
echo.
echo 📁 Проверьте файл: zones_visualization.png
echo    Убедитесь, что зоны правильно расположены!
echo.
echo 💡 Подробная инструкция: docs/guides/OCR_TESTING_GUIDE.md
echo.
pause
