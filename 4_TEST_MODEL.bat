@echo off
chcp 65001 > nul
cls
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║                                                            ║
echo ║          ШАГ 4: ТЕСТИРОВАНИЕ ОБУЧЕННОЙ МОДЕЛИ              ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo  Этот скрипт протестирует вашу обученную модель и покажет
echo  насколько хорошо она распознает карты.
echo.
echo  Будет сравнение:
echo    • Базовая модель VS Обученная модель
echo    • Разные пороги confidence
echo    • Детальная статистика
echo.
echo ════════════════════════════════════════════════════════════
echo.

python 4_test_model.py

echo.
if exist test_trained_model_result.jpg (
    echo Открываю результат...
    start test_trained_model_result.jpg
)

pause
