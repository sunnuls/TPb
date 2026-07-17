@echo off
chcp 65001 > nul
cls
echo ============================================================
echo 🔍 БЫСТРАЯ ПРОВЕРКА ТЕКУЩЕЙ МОДЕЛИ
echo ============================================================
echo.
echo Проверяем weights\best.pt...
echo.

python -c "import os; path='weights/best.pt'; print(f'Размер: {os.path.getsize(path)/1024/1024:.1f} MB') if os.path.exists(path) else print('❌ Файл не найден')"

echo.
echo Тестируем на скриншоте...
python tests/manual/test_current_model.py

pause
