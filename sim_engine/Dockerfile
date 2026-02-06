# Multi-Agent Simulation Research Framework - Dockerfile
# Educational Use Only: For controlled research environments studying
# multi-agent coordination patterns in game theory contexts.

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app/
COPY requirements_training.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements_training.txt

# Copy application code
COPY sim_engine/ /app/sim_engine/
COPY shared/ /app/shared/
COPY coach_app/ /app/coach_app/

# Copy configuration templates
COPY sim_engine/configs/ /app/configs/

# Create directories for outputs
RUN mkdir -p /app/logs /app/results /app/checkpoints

# Environment variables (overridable)
ENV PYTHONUNBUFFERED=1
ENV SIM_MODE=research
ENV LOG_LEVEL=INFO
ENV AGENT_COUNT=10
ENV SIMULATION_DURATION=3600
ENV CENTRAL_HUB_HOST=0.0.0.0
ENV CENTRAL_HUB_PORT=8765
ENV ENCRYPTION_ENABLED=true

# Educational Notice
RUN echo "Educational Research Framework - Multi-Agent Simulation" > /app/NOTICE.txt && \
    echo "For academic study of game theory and multi-agent systems only." >> /app/NOTICE.txt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Expose ports
# 8765: Central Hub WebSocket
# 8000: API server
# 9090: Metrics/Monitoring
EXPOSE 8765 8000 9090

# Default command (can be overridden)
CMD ["python", "-m", "sim_engine.orchestrator"]
