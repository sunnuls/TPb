#!/bin/bash
# Multi-Agent Simulation Research Framework - Cloud Deployment Script
# Educational Use Only: Deploys research simulation framework to cloud environment
# Пункт 1: Cloud-like EC2 deployment with multi-region support

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Multi-Agent Simulation Deployment${NC}"
echo -e "${GREEN}Educational Research Framework${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# ============================================================================
# CONFIGURATION
# ============================================================================
DEPLOYMENT_ENV=${DEPLOYMENT_ENV:-production}
REGION=${REGION:-us-east-1}
AGENT_COUNT=${AGENT_COUNT:-10}
REPLICA_COUNT=${REPLICA_COUNT:-2}

echo -e "${YELLOW}Deployment Configuration:${NC}"
echo "  Environment: $DEPLOYMENT_ENV"
echo "  Region: $REGION"
echo "  Agent Count: $AGENT_COUNT"
echo "  Replicas: $REPLICA_COUNT"
echo ""

# ============================================================================
# PREREQUISITES CHECK
# ============================================================================
echo -e "${YELLOW}Checking prerequisites...${NC}"

command -v docker >/dev/null 2>&1 || {
    echo -e "${RED}Error: docker is not installed${NC}" >&2
    exit 1
}

command -v docker-compose >/dev/null 2>&1 || {
    echo -e "${RED}Error: docker-compose is not installed${NC}" >&2
    exit 1
}

echo -e "${GREEN}✓ Prerequisites satisfied${NC}"
echo ""

# ============================================================================
# ENVIRONMENT SETUP (Подпункт 1.2: env vars для configs)
# ============================================================================
echo -e "${YELLOW}Setting up environment...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    cp .env.example .env
    
    # Generate secure keys
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    sed -i "s|<generate-with-cryptography.fernet.Fernet.generate_key()>|$ENCRYPTION_KEY|g" .env
    sed -i "s|<generate-secure-random-string>|$JWT_SECRET|g" .env
    
    echo -e "${GREEN}✓ Environment file created with secure keys${NC}"
else
    echo -e "${GREEN}✓ Using existing .env file${NC}"
fi

# Set deployment-specific variables
export AGENT_COUNT=$AGENT_COUNT
export REPLICA_COUNT=$REPLICA_COUNT
export REGION=$REGION

echo ""

# ============================================================================
# DIRECTORY SETUP
# ============================================================================
echo -e "${YELLOW}Creating directories...${NC}"

mkdir -p logs results configs checkpoints monitoring/grafana/{dashboards,datasources}

echo -e "${GREEN}✓ Directories created${NC}"
echo ""

# ============================================================================
# MONITORING CONFIGURATION (Preparation for Шаг 4.2)
# ============================================================================
echo -e "${YELLOW}Configuring monitoring...${NC}"

cat > monitoring/prometheus.yml <<EOF
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
EOF

cat > monitoring/grafana/datasources/prometheus.yml <<EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
EOF

echo -e "${GREEN}✓ Monitoring configured${NC}"
echo ""

# ============================================================================
# BUILD DOCKER IMAGES
# ============================================================================
echo -e "${YELLOW}Building Docker images...${NC}"

docker-compose build --no-cache

echo -e "${GREEN}✓ Docker images built${NC}"
echo ""

# ============================================================================
# DEPLOY SERVICES (Подпункт 1.1: Orchestration для 100 agents)
# ============================================================================
echo -e "${YELLOW}Deploying services...${NC}"

# Stop existing services
docker-compose down 2>/dev/null || true

# Start services
docker-compose up -d

echo -e "${GREEN}✓ Services deployed${NC}"
echo ""

# ============================================================================
# HEALTH CHECK
# ============================================================================
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"

MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo -e "${GREEN}✓ Services are healthy${NC}"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${RED}Warning: Services may not be fully healthy${NC}"
fi

# ============================================================================
# MULTI-REGION SETUP (Пункт 1: multi-region для network diversity)
# ============================================================================
if [ "$ENABLE_MULTI_REGION" = "true" ]; then
    echo -e "${YELLOW}Configuring multi-region deployment...${NC}"
    
    # Scale agent pool across regions (simulated via multiple replicas)
    docker-compose up -d --scale agent-pool=$REPLICA_COUNT
    
    echo -e "${GREEN}✓ Multi-region configuration complete${NC}"
    echo ""
fi

# ============================================================================
# DEPLOYMENT STATUS
# ============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Services:"
docker-compose ps
echo ""
echo "Access Points:"
echo "  Central Hub WebSocket: ws://localhost:8765"
echo "  API Server: http://localhost:8000"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana: http://localhost:3000 (admin/research_sim)"
echo ""
echo "Logs:"
echo "  View logs: docker-compose logs -f"
echo "  Agent logs: docker-compose logs -f agent-pool"
echo "  Hub logs: docker-compose logs -f central-hub"
echo ""
echo "Management:"
echo "  Stop: docker-compose down"
echo "  Restart: docker-compose restart"
echo "  Scale: docker-compose up -d --scale agent-pool=N"
echo ""
echo -e "${YELLOW}Educational Notice:${NC}"
echo "This framework is for academic research purposes only."
echo "Studying multi-agent coordination in game theory contexts."
echo ""
