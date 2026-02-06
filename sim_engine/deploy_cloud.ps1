# Multi-Agent Simulation Research Framework - Cloud Deployment Script (PowerShell)
# Educational Use Only: Deploys research simulation framework to cloud environment
# Пункт 1: Cloud-like deployment with multi-region support (Windows)

param(
    [string]$DeploymentEnv = "production",
    [string]$Region = "us-east-1",
    [int]$AgentCount = 10,
    [int]$ReplicaCount = 2
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Green
Write-Host "Multi-Agent Simulation Deployment" -ForegroundColor Green
Write-Host "Educational Research Framework" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# ============================================================================
# CONFIGURATION
# ============================================================================
Write-Host "Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Environment: $DeploymentEnv"
Write-Host "  Region: $Region"
Write-Host "  Agent Count: $AgentCount"
Write-Host "  Replicas: $ReplicaCount"
Write-Host ""

# ============================================================================
# PREREQUISITES CHECK
# ============================================================================
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

try {
    docker --version | Out-Null
    Write-Host "✓ Docker installed" -ForegroundColor Green
} catch {
    Write-Host "Error: Docker is not installed" -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
    Write-Host "✓ Docker Compose installed" -ForegroundColor Green
} catch {
    Write-Host "Error: Docker Compose is not installed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================================================
# ENVIRONMENT SETUP (Подпункт 1.2: env vars для configs)
# ============================================================================
Write-Host "Setting up environment..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from template..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    
    # Generate secure keys (simplified for Windows)
    $EncryptionKey = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    $JwtSecret = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    
    (Get-Content ".env") -replace '<generate-with-cryptography.fernet.Fernet.generate_key\(\)>', $EncryptionKey | Set-Content ".env"
    (Get-Content ".env") -replace '<generate-secure-random-string>', $JwtSecret | Set-Content ".env"
    
    Write-Host "✓ Environment file created with secure keys" -ForegroundColor Green
} else {
    Write-Host "✓ Using existing .env file" -ForegroundColor Green
}

# Set deployment-specific variables
$env:AGENT_COUNT = $AgentCount
$env:REPLICA_COUNT = $ReplicaCount
$env:REGION = $Region

Write-Host ""

# ============================================================================
# DIRECTORY SETUP
# ============================================================================
Write-Host "Creating directories..." -ForegroundColor Yellow

$directories = @(
    "logs",
    "results",
    "configs",
    "checkpoints",
    "monitoring\grafana\dashboards",
    "monitoring\grafana\datasources"
)

foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "✓ Directories created" -ForegroundColor Green
Write-Host ""

# ============================================================================
# MONITORING CONFIGURATION
# ============================================================================
Write-Host "Configuring monitoring..." -ForegroundColor Yellow

@"
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'simulation-agents'
    static_configs:
      - targets: ['central-hub:8000', 'agent-pool:8001']
    metrics_path: '/metrics'

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
"@ | Set-Content "monitoring\prometheus.yml"

@"
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
"@ | Set-Content "monitoring\grafana\datasources\prometheus.yml"

Write-Host "✓ Monitoring configured" -ForegroundColor Green
Write-Host ""

# ============================================================================
# BUILD DOCKER IMAGES
# ============================================================================
Write-Host "Building Docker images..." -ForegroundColor Yellow

docker-compose build --no-cache

Write-Host "✓ Docker images built" -ForegroundColor Green
Write-Host ""

# ============================================================================
# DEPLOY SERVICES (Подпункт 1.1: Orchestration для 100 agents)
# ============================================================================
Write-Host "Deploying services..." -ForegroundColor Yellow

# Stop existing services
docker-compose down 2>$null

# Start services
docker-compose up -d

Write-Host "✓ Services deployed" -ForegroundColor Green
Write-Host ""

# ============================================================================
# HEALTH CHECK
# ============================================================================
Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow

$maxWait = 60
$elapsed = 0
while ($elapsed -lt $maxWait) {
    $status = docker-compose ps
    if ($status -match "healthy") {
        Write-Host "✓ Services are healthy" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 2
    $elapsed += 2
    Write-Host "." -NoNewline
}
Write-Host ""

if ($elapsed -ge $maxWait) {
    Write-Host "Warning: Services may not be fully healthy" -ForegroundColor Red
}

# ============================================================================
# MULTI-REGION SETUP
# ============================================================================
if ($env:ENABLE_MULTI_REGION -eq "true") {
    Write-Host "Configuring multi-region deployment..." -ForegroundColor Yellow
    
    docker-compose up -d --scale agent-pool=$ReplicaCount
    
    Write-Host "✓ Multi-region configuration complete" -ForegroundColor Green
    Write-Host ""
}

# ============================================================================
# DEPLOYMENT STATUS
# ============================================================================
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:"
docker-compose ps
Write-Host ""
Write-Host "Access Points:"
Write-Host "  Central Hub WebSocket: ws://localhost:8765"
Write-Host "  API Server: http://localhost:8000"
Write-Host "  Prometheus: http://localhost:9090"
Write-Host "  Grafana: http://localhost:3000 (admin/research_sim)"
Write-Host ""
Write-Host "Logs:"
Write-Host "  View logs: docker-compose logs -f"
Write-Host "  Agent logs: docker-compose logs -f agent-pool"
Write-Host "  Hub logs: docker-compose logs -f central-hub"
Write-Host ""
Write-Host "Management:"
Write-Host "  Stop: docker-compose down"
Write-Host "  Restart: docker-compose restart"
Write-Host "  Scale: docker-compose up -d --scale agent-pool=N"
Write-Host ""
Write-Host "Educational Notice:" -ForegroundColor Yellow
Write-Host "This framework is for academic research purposes only."
Write-Host "Studying multi-agent coordination in game theory contexts."
Write-Host ""
