@echo off
REM Log Analyzer - Research Optimization Tool
REM Educational Use Only

echo ============================================
echo Simulation Log Analyzer
echo Educational Research Optimization Tool
echo ============================================
echo.

REM Activate virtual environment
if exist ..\.venv\Scripts\activate.bat (
    call ..\.venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found
)

echo Analyzing simulation logs...
echo.

REM Run analyzer
python analysis\log_analyzer.py

echo.
echo Analysis complete!
echo Report saved to: OPTIMIZATION_REPORT.md
echo.

pause
