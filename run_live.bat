@echo off
chcp 65001 > nul
echo ============================================
echo   LIVE POKER WINDOW CAPTURE
echo ============================================
echo.
echo Поиск окна покер-клиента...
echo.
python poker_live.py
pause
