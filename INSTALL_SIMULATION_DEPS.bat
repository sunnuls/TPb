@echo off
REM Installation script for simulation research dependencies
echo ============================================
echo Installing dependencies for Multi-Agent Simulation Research Framework
echo ============================================

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Warning: No virtual environment found. Using system Python.
)

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install base dependencies
echo.
echo Installing base dependencies from pyproject.toml...
pip install -e .

REM Install extras for simulation research
echo.
echo Installing [live] extras for vision-based input...
pip install -e ".[live]"

echo.
echo Installing [dev] extras for testing and validation...
pip install -e ".[dev]"

echo.
echo Installing [simulation] extras for multi-agent research framework...
pip install -e ".[simulation]"

REM Verify critical packages
echo.
echo ============================================
echo Verifying installation...
echo ============================================
python -c "import fastapi; print(f'✓ FastAPI: {fastapi.__version__}')"
python -c "import cv2; print(f'✓ OpenCV: {cv2.__version__}')"
python -c "import pytest; print(f'✓ Pytest: {pytest.__version__}')"
python -c "import ultralytics; print(f'✓ Ultralytics: {ultralytics.__version__}')"
python -c "import websockets; print(f'✓ Websockets: {websockets.__version__}')" 2>nul || echo "⚠ Websockets not installed"
python -c "import torch; print(f'✓ PyTorch: {torch.__version__}')" 2>nul || echo "⚠ PyTorch not installed"
python -c "import treys; print(f'✓ Treys (poker lib): installed')" 2>nul || echo "⚠ Treys not installed"

echo.
echo ============================================
echo Installation complete!
echo You can now proceed with simulation research setup.
echo ============================================
pause
