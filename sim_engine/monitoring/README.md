# Multi-Agent Simulation Research Dashboard

**Educational Use Only**: Monitoring dashboard for tracking performance metrics, efficiency, and anomalies in multi-agent research simulations.

## Overview (Шаг 4.2, Пункт 1)

Flask-based real-time monitoring dashboard that provides:
- **Performance Metrics**: Track decisions, equity, uptime
- **Efficiency Scoring**: Custom metric combining throughput, anomaly rate, equity stability
- **Anomaly Detection**: Real-time alerts for suboptimal modeling
- **Prometheus Integration**: Standard metrics export
- **Agent Monitoring**: Individual agent status and behavior

## Features

### Core Metrics
- Total/Active Agent count
- Total Decisions made
- Anomaly count
- Average Equity across agents
- Session uptime
- **Efficiency Score** (0-100%):
  - Throughput (decisions/sec)
  - Anomaly penalty
  - Equity stability bonus

### Alert System (Подпункт 1.2)
Automated alerts for:
- **Low Efficiency**: <50% efficiency score
- **High Anomaly Rate**: >10% of decisions
- **Inactive Agents**: >50% agents inactive
- **Equity Imbalance**: Average equity outside 0.3-0.7 range

### Prometheus Integration (Подпункт 1.1)
Exports metrics:
- **Counters**: `simulation_runs_total`, `decisions_made_total`, `anomalies_detected_total`
- **Gauges**: `active_agents_current`, `session_duration_seconds`, `average_equity`
- **Histograms**: `decision_latency_seconds`, `equity_distribution`

## Quick Start

### 1. Install Dependencies

```bash
pip install -r monitoring/requirements.txt
```

### 2. Start Dashboard

```bash
# Windows
START_DASHBOARD.bat

# Linux/Mac
chmod +x START_DASHBOARD.sh
./START_DASHBOARD.sh

# Or directly
python monitoring/sim_dashboard.py
```

### 3. Access Dashboard

- **Main Dashboard**: http://localhost:5000
- **Prometheus Metrics**: http://localhost:5000/metrics
- **Health Check**: http://localhost:5000/health

## API Endpoints

### GET /
Main dashboard UI (HTML)

### GET /api/metrics
Get current simulation metrics

**Response:**
```json
{
  "simulation": {
    "total_agents": 10,
    "active_agents": 8,
    "total_decisions": 1523,
    "total_anomalies": 12,
    "average_equity": 0.562,
    "uptime": 3600.5,
    "efficiency_score": 78.3
  },
  "agents": [
    {
      "agent_id": "agent_1",
      "behavior_type": "balanced",
      "decisions_count": 150,
      "average_equity": 0.580,
      "session_duration": 3600.0,
      "anomalies_count": 2,
      "status": "active"
    }
  ]
}
```

### GET /api/alerts
Get active alerts

**Response:**
```json
{
  "alerts": [
    {
      "severity": "warning",
      "type": "low_efficiency",
      "message": "Simulation efficiency below threshold: 45.2%",
      "timestamp": "2026-02-06T10:30:00"
    }
  ],
  "new_alerts": []
}
```

### GET /api/agent/<agent_id>
Get detailed metrics for specific agent

**Response:**
```json
{
  "agent_id": "agent_1",
  "behavior_type": "aggressive",
  "decisions_count": 200,
  "average_equity": 0.675,
  "session_duration": 1800.5,
  "anomalies": ["excessive_activity", "pattern_detected"],
  "last_update": "2026-02-06T10:35:22"
}
```

### POST /api/report
Report metrics from agent

**Request:**
```json
{
  "agent_id": "agent_1",
  "behavior_type": "balanced",
  "decisions": 1,
  "equity": 0.65,
  "duration": 120.5,
  "action_type": "increment",
  "anomalies": []
}
```

**Response:**
```json
{
  "status": "ok",
  "agent_id": "agent_1"
}
```

### GET /metrics
Prometheus metrics endpoint (plain text)

### GET /health
Health check endpoint

## Integration with Agents

Agents can report metrics to the dashboard:

```python
import requests

def report_metrics(agent_id, metrics):
    """Report agent metrics to dashboard."""
    response = requests.post('http://localhost:5000/api/report', json={
        'agent_id': agent_id,
        'behavior_type': metrics['behavior'],
        'decisions': 1,
        'equity': metrics['equity'],
        'duration': metrics['session_duration'],
        'action_type': metrics['action'],
        'anomalies': metrics.get('anomalies', [])
    })
    return response.json()
```

## Configuration

Environment variables:

```bash
# Dashboard port
export DASHBOARD_PORT=5000

# Flask debug mode
export FLASK_DEBUG=false

# Flask secret key
export FLASK_SECRET_KEY=your_secret_key
```

## Prometheus Setup

### prometheus.yml

```yaml
scrape_configs:
  - job_name: 'simulation-dashboard'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboard

Import metrics:
- `simulation_runs_total` - Total simulations
- `active_agents_current` - Current active agents
- `average_equity` - Average equity gauge
- `decision_latency_seconds` - Decision generation time

Example PromQL queries:

```promql
# Decision rate (per second)
rate(decisions_made_total[5m])

# Anomaly rate
rate(anomalies_detected_total[5m]) / rate(decisions_made_total[5m])

# Active agents trend
active_agents_current
```

## Alert Rules (Подпункт 1.2)

### Built-in Alerts

1. **Low Efficiency Alert**
   - Trigger: Efficiency < 50%
   - Severity: Warning
   - Action: Review agent behavior distribution

2. **High Anomaly Rate**
   - Trigger: Anomaly rate > 10%
   - Severity: Critical
   - Action: Check session timeouts, patterns

3. **Inactive Agents**
   - Trigger: >50% agents inactive
   - Severity: Warning
   - Action: Verify agent connectivity

4. **Equity Imbalance**
   - Trigger: Average equity < 0.3 or > 0.7
   - Severity: Info
   - Action: Review variance parameters

### Custom Prometheus Alerts

Create `alert_rules.yml`:

```yaml
groups:
  - name: simulation_alerts
    interval: 30s
    rules:
      - alert: SimulationLowEfficiency
        expr: efficiency_score < 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Simulation efficiency is low"
          description: "Efficiency score has been below 50% for 5 minutes"

      - alert: HighAnomalyRate
        expr: rate(anomalies_detected_total[5m]) / rate(decisions_made_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High anomaly detection rate"
          description: "More than 10% of decisions have anomalies"
```

## Monitoring Best Practices

1. **Dashboard Checks**
   - Monitor efficiency score (target: >70%)
   - Watch anomaly count trend
   - Verify all agents active

2. **Performance Tuning**
   - If efficiency low: adjust agent count or behavior distribution
   - If anomalies high: review session limits, variance parameters
   - If equity imbalanced: check opponent profiler training

3. **Alert Response**
   - **Low Efficiency**: Scale down agents or optimize decision logic
   - **High Anomalies**: Increase session timeout, review patterns
   - **Inactive Agents**: Check network, verify central hub connection

## Testing

Run dashboard tests:

```bash
pytest sim_engine/tests/test_dashboard.py -v
```

Test coverage:
- Metrics calculation
- Alert generation
- API endpoints
- Prometheus integration

## Architecture

```
┌─────────────────────────────────────┐
│        Simulation Agents            │
│   (report metrics via POST)         │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│     Flask Dashboard (Port 5000)     │
│  ┌─────────────────────────────┐   │
│  │   MetricsStore (In-Memory)  │   │
│  │  - Agents metrics           │   │
│  │  - Simulation metrics       │   │
│  │  - Alerts                   │   │
│  └─────────────────────────────┘   │
│                                      │
│  ┌─────────────────────────────┐   │
│  │   Prometheus Metrics        │   │
│  │   /metrics endpoint         │   │
│  └─────────────────────────────┘   │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      Prometheus + Grafana           │
│   (scrape /metrics every 15s)       │
└─────────────────────────────────────┘
```

## Educational Compliance

This dashboard is designed for:
- ✅ Academic research monitoring
- ✅ Multi-agent system analysis
- ✅ Performance optimization studies
- ✅ Algorithm validation

**Not intended for**:
- ❌ Real-money gaming monitoring
- ❌ Production gambling systems
- ❌ Commercial operations

All data collected is for research purposes and should be anonymized.

## Troubleshooting

### Dashboard won't start
```bash
# Check port availability
netstat -an | findstr 5000  # Windows
lsof -i :5000  # Linux/Mac

# Use different port
export DASHBOARD_PORT=5001
python monitoring/sim_dashboard.py
```

### No metrics appearing
- Verify agents are reporting via `/api/report`
- Check dashboard logs for errors
- Test endpoint: `curl -X POST http://localhost:5000/api/report -H "Content-Type: application/json" -d '{"agent_id":"test","decisions":1}'`

### Prometheus not scraping
- Verify `/metrics` endpoint accessible
- Check Prometheus `targets` page
- Verify `prometheus.yml` configuration

---

**Version**: 1.0.0  
**Last Updated**: 2026-02-06  
**License**: Educational Research Use Only
