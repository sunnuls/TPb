@echo off
REM Multi-Agent Simulation Dashboard Launcher
REM Educational Use Only

echo ============================================
echo Multi-Agent Simulation Research Dashboard
echo Educational Use Only
echo ============================================
echo.

REM Activate virtual environment
if exist ..\. venv\Scripts\activate.bat (
    call ..\.venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found
)

REM Install dashboard requirements
echo Installing dashboard requirements...
pip install -q -r monitoring\requirements.txt

REM Set Flask environment
set FLASK_APP=monitoring\sim_dashboard.py
set FLASK_DEBUG=false
set DASHBOARD_PORT=5000

echo.
echo Starting dashboard on http://localhost:5000
echo Prometheus metrics: http://localhost:5000/metrics
echo Press Ctrl+C to stop
echo.

REM Start dashboard
python monitoring\sim_dashboard.py

pause
