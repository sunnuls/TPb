"""
Simple Flask Dashboard for HIVE Simulation (Roadmap2 Phase 4).

Real-time visualization of HIVE vs baseline performance:
- Winrate comparison (3vs1 HIVE vs random play)
- ROI and bb/100 charts
- Coordination efficiency metrics
- Edge exploitation graphs

Educational Use Only: For visualizing multi-agent coordination
research results. Not for production use.
"""

from __future__ import annotations

import json
from typing import Dict, List

from flask import Flask, jsonify, render_template_string, request

# Will be populated by simulation runs
SIMULATION_RESULTS: List[Dict] = []


app = Flask(__name__)


# HTML Template with embedded JavaScript for charts
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>HIVE Simulation Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 32px;
            font-weight: bold;
            color: #27ae60;
        }
        .metric-label {
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 5px;
        }
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .refresh-btn {
            background-color: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        .refresh-btn:hover {
            background-color: #2980b9;
        }
        h2 {
            color: #2c3e50;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🐝 HIVE Multi-Agent Simulation Dashboard</h1>
        <p>Real-time visualization of 3vs1 coordination strategy performance</p>
        <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value" id="winrate">--%</div>
            <div class="metric-label">HIVE Winrate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="roi">--</div>
            <div class="metric-label">ROI (%)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="bb100">--</div>
            <div class="metric-label">bb/100 hands</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="coordination">--%</div>
            <div class="metric-label">Coordination Efficiency</div>
        </div>
    </div>

    <div class="chart-container">
        <h2>Winrate Comparison: HIVE vs Random</h2>
        <canvas id="winrateChart"></canvas>
    </div>

    <div class="chart-container">
        <h2>ROI Performance</h2>
        <canvas id="roiChart"></canvas>
    </div>

    <div class="chart-container">
        <h2>Edge Exploitation & Equity Realization</h2>
        <canvas id="edgeChart"></canvas>
    </div>

    <script>
        // Fetch simulation data
        fetch('/api/metrics')
            .then(response => response.json())
            .then(data => {
                updateMetrics(data);
                createCharts(data);
            });

        function updateMetrics(data) {
            if (data.length === 0) {
                return;
            }
            const latest = data[data.length - 1];
            document.getElementById('winrate').textContent = (latest.winrate * 100).toFixed(1) + '%';
            document.getElementById('roi').textContent = latest.roi.toFixed(1) + '%';
            document.getElementById('bb100').textContent = latest.bb_per_100.toFixed(2);
            document.getElementById('coordination').textContent = latest.coordination_efficiency.toFixed(1) + '%';
        }

        function createCharts(data) {
            // Winrate Chart
            const winrateCtx = document.getElementById('winrateChart').getContext('2d');
            new Chart(winrateCtx, {
                type: 'bar',
                data: {
                    labels: ['HIVE (3vs1)', 'Random Baseline'],
                    datasets: [{
                        label: 'Winrate (%)',
                        data: [
                            data.length > 0 ? (data[data.length - 1].winrate * 100) : 0,
                            50  // Random baseline
                        ],
                        backgroundColor: ['#27ae60', '#95a5a6']
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });

            // ROI Chart
            const roiCtx = document.getElementById('roiChart').getContext('2d');
            new Chart(roiCtx, {
                type: 'line',
                data: {
                    labels: data.map((_, i) => `Run ${i + 1}`),
                    datasets: [{
                        label: 'HIVE ROI (%)',
                        data: data.map(d => d.roi),
                        borderColor: '#3498db',
                        fill: false
                    }, {
                        label: 'Baseline (0%)',
                        data: data.map(() => 0),
                        borderColor: '#95a5a6',
                        borderDash: [5, 5],
                        fill: false
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: false
                        }
                    }
                }
            });

            // Edge Exploitation Chart
            const edgeCtx = document.getElementById('edgeChart').getContext('2d');
            new Chart(edgeCtx, {
                type: 'radar',
                data: {
                    labels: ['Edge Exploitation', 'Equity Realization', 'Coordination Eff.'],
                    datasets: [{
                        label: 'HIVE Performance',
                        data: data.length > 0 ? [
                            data[data.length - 1].edge_exploitation * 100,
                            data[data.length - 1].equity_realization,
                            data[data.length - 1].coordination_efficiency
                        ] : [0, 0, 0],
                        backgroundColor: 'rgba(46, 204, 113, 0.2)',
                        borderColor: '#2ecc71',
                        pointBackgroundColor: '#27ae60'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 150
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Render main dashboard."""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/metrics')
def get_metrics():
    """API endpoint for simulation metrics."""
    return jsonify(SIMULATION_RESULTS)


@app.route('/api/submit', methods=['POST'])
def submit_metrics():
    """
    Submit new simulation results.
    
    Expected JSON format:
    {
        "winrate": 0.65,
        "roi": 250.0,
        "bb_per_100": 5.25,
        "edge_exploitation": 1.15,
        "coordination_efficiency": 85.0,
        "equity_realization": 105.0,
        ...
    }
    """
    data = request.get_json()
    SIMULATION_RESULTS.append(data)
    return jsonify({"status": "success", "total_runs": len(SIMULATION_RESULTS)})


@app.route('/api/clear', methods=['POST'])
def clear_metrics():
    """Clear all stored metrics."""
    global SIMULATION_RESULTS
    SIMULATION_RESULTS = []
    return jsonify({"status": "cleared"})


def run_dashboard(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """
    Start Flask dashboard server.
    
    Args:
        host: Host to bind (default: 0.0.0.0 for all interfaces)
        port: Port number (default: 5000)
        debug: Enable Flask debug mode
        
    Educational Note:
        This provides a simple web interface for visualizing
        multi-agent coordination research results in real-time.
    """
    print(f"\n{'=' * 60}")
    print("HIVE SIMULATION DASHBOARD")
    print(f"{'=' * 60}")
    print(f"Starting dashboard server...")
    print(f"Access at: http://localhost:{port}")
    print(f"{'=' * 60}\n")
    
    app.run(host=host, port=port, debug=debug)


# Educational Example: Integration with HiveSimulation
if __name__ == "__main__":
    import threading
    import time
    
    # Start dashboard in background thread
    dashboard_thread = threading.Thread(
        target=run_dashboard,
        kwargs={'host': '127.0.0.1', 'port': 5000, 'debug': False}
    )
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    print("Dashboard started! Visit http://localhost:5000")
    print("Running demo simulations...")
    
    # Run demo simulations and submit results
    from sim_engine.hive_simulation import HiveSimulation
    from sim_engine.metrics import MetricsCalculator
    
    import requests
    
    time.sleep(2)  # Wait for Flask to start
    
    for run in range(3):
        print(f"\nRunning simulation {run + 1}/3...")
        
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=50,
            lobby_size=50,
            log_interval=25
        )
        
        base_metrics = sim.run()
        
        # Calculate advanced metrics
        calculator = MetricsCalculator()
        advanced = calculator.calculate_advanced_metrics(base_metrics, sim.hand_history)
        
        # Submit to dashboard
        try:
            response = requests.post(
                'http://localhost:5000/api/submit',
                json=advanced.summary_dict()
            )
            print(f"Submitted to dashboard: {response.json()}")
        except Exception as e:
            print(f"Failed to submit: {e}")
    
    print("\n" + "=" * 60)
    print("Demo complete! Dashboard at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    # Keep alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
