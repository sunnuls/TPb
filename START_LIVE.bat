@echo off
chcp 65001 > nul
echo ============================================
echo   LIVE POKER ASSISTANT
echo ============================================
echo.
echo Поиск окна покер-клиента...
echo.
python test_real_ocr.py --live --config "stol\poker_table_config (1).yaml"
echo.
pause
