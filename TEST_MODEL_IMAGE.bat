@echo off
chcp 65001 > nul
echo ======================================================================
echo ТЕСТ МОДЕЛИ НА РЕАЛЬНОМ ИЗОБРАЖЕНИИ КАРТ
echo ======================================================================
echo.
python test_model_with_image.py
echo.
if exist test_model_result.jpg (
    echo Открываю результат...
    start test_model_result.jpg
)
pause
