#!/bin/bash
# Multi-Agent Simulation Dashboard Launcher
# Educational Use Only

echo "============================================"
echo "Multi-Agent Simulation Research Dashboard"
echo "Educational Use Only"
echo "============================================"
echo ""

# Activate virtual environment
if [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
else
    echo "Warning: Virtual environment not found"
fi

# Install dashboard requirements
echo "Installing dashboard requirements..."
pip install -q -r monitoring/requirements.txt

# Set Flask environment
export FLASK_APP=monitoring/sim_dashboard.py
export FLASK_DEBUG=false
export DASHBOARD_PORT=5000

echo ""
echo "Starting dashboard on http://localhost:5000"
echo "Prometheus metrics: http://localhost:5000/metrics"
echo "Press Ctrl+C to stop"
echo ""

# Start dashboard
python monitoring/sim_dashboard.py
