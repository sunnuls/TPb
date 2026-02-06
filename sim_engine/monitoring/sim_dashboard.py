"""
Multi-Agent Simulation Research Dashboard.

Educational Use Only: Flask-based monitoring dashboard for tracking
performance metrics, efficiency, and anomalies in research simulations.

Шаг 4.2, Пункт 1: Track performance metrics, efficiency, anomalies.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request
from prometheus_client import Counter, Gauge, Histogram, generate_latest

# Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'research_sim_dashboard_2026')


# ============================================================================
# PROMETHEUS METRICS (Подпункт 1.1: Integrate Prometheus)
# ============================================================================

# Counters
simulation_runs = Counter(
    'simulation_runs_total',
    'Total number of simulation runs',
    ['agent_id', 'behavior_type']
)

decisions_made = Counter(
    'decisions_made_total',
    'Total number of decisions made',
    ['agent_id', 'action_type']
)

anomalies_detected = Counter(
    'anomalies_detected_total',
    'Total number of anomalies detected',
    ['anomaly_type']
)

# Gauges
active_agents = Gauge(
    'active_agents_current',
    'Current number of active agents'
)

session_duration = Gauge(
    'session_duration_seconds',
    'Current session duration',
    ['agent_id']
)

average_equity = Gauge(
    'average_equity',
    'Average equity across all agents'
)

# Histograms
decision_latency = Histogram(
    'decision_latency_seconds',
    'Decision generation latency',
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

equity_distribution = Histogram(
    'equity_distribution',
    'Distribution of equity values',
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class AgentMetrics:
    """Metrics for a single agent."""
    agent_id: str
    behavior_type: str
    decisions_count: int = 0
    average_equity: float = 0.0
    session_duration: float = 0.0
    anomalies: List[str] = field(default_factory=list)
    last_update: float = field(default_factory=time.time)


@dataclass
class SimulationMetrics:
    """Aggregated simulation metrics."""
    total_agents: int = 0
    active_agents: int = 0
    total_decisions: int = 0
    total_anomalies: int = 0
    average_equity: float = 0.0
    uptime: float = 0.0
    efficiency_score: float = 0.0  # Custom metric
    
    def calculate_efficiency(self) -> float:
        """
        Calculate simulation efficiency score.
        
        Educational Note:
            Efficiency combines decision throughput, anomaly rate,
            and equity stability for research evaluation.
        """
        if self.total_decisions == 0:
            return 0.0
        
        # Base score: decisions per second
        throughput = self.total_decisions / max(1, self.uptime)
        
        # Penalty for anomalies
        anomaly_rate = self.total_anomalies / max(1, self.total_decisions)
        anomaly_penalty = max(0, 1 - (anomaly_rate * 10))
        
        # Bonus for stable equity
        equity_stability = 1 - abs(0.5 - self.average_equity)
        
        # Combined score (0-100)
        efficiency = (throughput * 10 + anomaly_penalty * 50 + equity_stability * 40)
        
        return min(100.0, efficiency)


# ============================================================================
# IN-MEMORY STORAGE (для демо; в продакшене использовать Redis/DB)
# ============================================================================

class MetricsStore:
    """Simple in-memory metrics storage."""
    
    def __init__(self):
        self.agents: Dict[str, AgentMetrics] = {}
        self.simulation: SimulationMetrics = SimulationMetrics()
        self.alerts: List[Dict[str, Any]] = []
        self.start_time = time.time()
    
    def update_agent_metrics(self, agent_id: str, data: Dict[str, Any]):
        """Update metrics for specific agent."""
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentMetrics(
                agent_id=agent_id,
                behavior_type=data.get('behavior_type', 'balanced')
            )
        
        agent = self.agents[agent_id]
        agent.decisions_count += data.get('decisions', 0)
        agent.average_equity = data.get('equity', agent.average_equity)
        agent.session_duration = data.get('duration', agent.session_duration)
        
        if 'anomalies' in data:
            agent.anomalies.extend(data['anomalies'])
        
        agent.last_update = time.time()
        
        # Update Prometheus metrics
        decisions_made.labels(
            agent_id=agent_id,
            action_type=data.get('action_type', 'unknown')
        ).inc(data.get('decisions', 0))
        
        session_duration.labels(agent_id=agent_id).set(agent.session_duration)
    
    def update_simulation_metrics(self):
        """Recalculate aggregated simulation metrics."""
        self.simulation.total_agents = len(self.agents)
        self.simulation.active_agents = sum(
            1 for agent in self.agents.values()
            if time.time() - agent.last_update < 60
        )
        self.simulation.total_decisions = sum(
            agent.decisions_count for agent in self.agents.values()
        )
        self.simulation.total_anomalies = sum(
            len(agent.anomalies) for agent in self.agents.values()
        )
        
        if self.agents:
            self.simulation.average_equity = sum(
                agent.average_equity for agent in self.agents.values()
            ) / len(self.agents)
        
        self.simulation.uptime = time.time() - self.start_time
        self.simulation.efficiency_score = self.simulation.calculate_efficiency()
        
        # Update Prometheus gauges
        active_agents.set(self.simulation.active_agents)
        average_equity.set(self.simulation.average_equity)
    
    def check_alerts(self):
        """Check for alert conditions (Подпункт 1.2: Alerts)."""
        alerts = []
        
        # Alert: Low efficiency
        if self.simulation.efficiency_score < 50:
            alerts.append({
                'severity': 'warning',
                'type': 'low_efficiency',
                'message': f'Simulation efficiency below threshold: {self.simulation.efficiency_score:.1f}%',
                'timestamp': datetime.now().isoformat()
            })
        
        # Alert: High anomaly rate
        if self.simulation.total_decisions > 0:
            anomaly_rate = self.simulation.total_anomalies / self.simulation.total_decisions
            if anomaly_rate > 0.1:
                alerts.append({
                    'severity': 'critical',
                    'type': 'high_anomaly_rate',
                    'message': f'Anomaly rate exceeds 10%: {anomaly_rate*100:.1f}%',
                    'timestamp': datetime.now().isoformat()
                })
        
        # Alert: Inactive agents
        inactive_count = self.simulation.total_agents - self.simulation.active_agents
        if inactive_count > self.simulation.total_agents * 0.5:
            alerts.append({
                'severity': 'warning',
                'type': 'inactive_agents',
                'message': f'{inactive_count} agents inactive (>50%)',
                'timestamp': datetime.now().isoformat()
            })
        
        # Alert: Suboptimal equity distribution
        if self.simulation.average_equity < 0.3 or self.simulation.average_equity > 0.7:
            alerts.append({
                'severity': 'info',
                'type': 'equity_imbalance',
                'message': f'Average equity outside optimal range: {self.simulation.average_equity:.2f}',
                'timestamp': datetime.now().isoformat()
            })
        
        # Store new alerts
        for alert in alerts:
            if not any(a['type'] == alert['type'] and 
                      (datetime.now() - datetime.fromisoformat(a['timestamp'])) < timedelta(minutes=5)
                      for a in self.alerts):
                self.alerts.append(alert)
                
                # Increment Prometheus counter
                anomalies_detected.labels(anomaly_type=alert['type']).inc()
        
        # Keep only recent alerts (last hour)
        cutoff = datetime.now() - timedelta(hours=1)
        self.alerts = [
            a for a in self.alerts
            if datetime.fromisoformat(a['timestamp']) > cutoff
        ]
        
        return alerts


# Global metrics store
metrics_store = MetricsStore()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/metrics')
def get_metrics():
    """Get current simulation metrics."""
    metrics_store.update_simulation_metrics()
    
    return jsonify({
        'simulation': {
            'total_agents': metrics_store.simulation.total_agents,
            'active_agents': metrics_store.simulation.active_agents,
            'total_decisions': metrics_store.simulation.total_decisions,
            'total_anomalies': metrics_store.simulation.total_anomalies,
            'average_equity': round(metrics_store.simulation.average_equity, 3),
            'uptime': round(metrics_store.simulation.uptime, 1),
            'efficiency_score': round(metrics_store.simulation.efficiency_score, 1)
        },
        'agents': [
            {
                'agent_id': agent.agent_id,
                'behavior_type': agent.behavior_type,
                'decisions_count': agent.decisions_count,
                'average_equity': round(agent.average_equity, 3),
                'session_duration': round(agent.session_duration, 1),
                'anomalies_count': len(agent.anomalies),
                'status': 'active' if time.time() - agent.last_update < 60 else 'inactive'
            }
            for agent in metrics_store.agents.values()
        ]
    })


@app.route('/api/alerts')
def get_alerts():
    """Get current alerts (Подпункт 1.2)."""
    alerts = metrics_store.check_alerts()
    
    return jsonify({
        'alerts': metrics_store.alerts,
        'new_alerts': alerts
    })


@app.route('/api/agent/<agent_id>')
def get_agent_details(agent_id: str):
    """Get detailed metrics for specific agent."""
    if agent_id not in metrics_store.agents:
        return jsonify({'error': 'Agent not found'}), 404
    
    agent = metrics_store.agents[agent_id]
    
    return jsonify({
        'agent_id': agent.agent_id,
        'behavior_type': agent.behavior_type,
        'decisions_count': agent.decisions_count,
        'average_equity': round(agent.average_equity, 3),
        'session_duration': round(agent.session_duration, 1),
        'anomalies': agent.anomalies,
        'last_update': datetime.fromtimestamp(agent.last_update).isoformat()
    })


@app.route('/api/report', methods=['POST'])
def report_metrics():
    """
    Endpoint for agents to report metrics.
    
    Expected JSON:
    {
        "agent_id": "agent_1",
        "behavior_type": "balanced",
        "decisions": 1,
        "equity": 0.65,
        "duration": 120.5,
        "action_type": "increment",
        "anomalies": []
    }
    """
    data = request.get_json()
    
    if not data or 'agent_id' not in data:
        return jsonify({'error': 'agent_id required'}), 400
    
    agent_id = data['agent_id']
    metrics_store.update_agent_metrics(agent_id, data)
    
    return jsonify({'status': 'ok', 'agent_id': agent_id})


@app.route('/metrics')
def prometheus_metrics():
    """Prometheus metrics endpoint (Подпункт 1.1)."""
    return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'uptime': round(time.time() - metrics_store.start_time, 1),
        'timestamp': datetime.now().isoformat()
    })


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.route('/api/reset', methods=['POST'])
def reset_metrics():
    """Reset all metrics (for testing)."""
    global metrics_store
    metrics_store = MetricsStore()
    return jsonify({'status': 'reset'})


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    
    print("=" * 60)
    print("Multi-Agent Simulation Research Dashboard")
    print("Educational Use Only")
    print("=" * 60)
    print(f"Starting dashboard on http://0.0.0.0:{port}")
    print(f"Prometheus metrics: http://0.0.0.0:{port}/metrics")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
