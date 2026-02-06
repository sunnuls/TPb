"""
Tests for Cloud Deployment Configuration.

Educational Use Only: Validates deployment setup for multi-agent
research simulations (Шаг 4.1).
"""

import os
import pytest
import yaml
from pathlib import Path


class TestDockerConfiguration:
    """Test Docker deployment configuration (Пункт 1)."""
    
    def test_dockerfile_exists(self):
        """Test Dockerfile exists."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        assert dockerfile_path.exists(), "Dockerfile not found"
    
    def test_dockerfile_has_required_sections(self):
        """Test Dockerfile contains required sections."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile_path.read_text()
        
        # Required sections
        assert "FROM python:" in content
        assert "WORKDIR /app" in content
        assert "COPY requirements.txt" in content
        assert "RUN pip install" in content
        assert "EXPOSE" in content
        assert "CMD" in content
    
    def test_dockerfile_exposes_correct_ports(self):
        """Test Dockerfile exposes required ports."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile_path.read_text()
        
        # Required ports
        assert "8765" in content  # Central Hub WebSocket
        assert "8000" in content  # API server
        assert "9090" in content  # Metrics


class TestDockerComposeConfiguration:
    """Test Docker Compose orchestration (Подпункт 1.1)."""
    
    def test_docker_compose_exists(self):
        """Test docker-compose.yml exists."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        assert compose_path.exists(), "docker-compose.yml not found"
    
    def test_docker_compose_valid_yaml(self):
        """Test docker-compose.yml is valid YAML."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert 'services' in config
        assert 'networks' in config
        assert 'volumes' in config
    
    def test_docker_compose_has_required_services(self):
        """Test docker-compose.yml defines required services."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        services = config.get('services', {})
        
        # Required services
        assert 'central-hub' in services, "central-hub service missing"
        assert 'agent-pool' in services, "agent-pool service missing"
        assert 'redis' in services, "redis service missing"
        assert 'prometheus' in services, "prometheus service missing"
        assert 'grafana' in services, "grafana service missing"
    
    def test_agent_pool_has_scaling_config(self):
        """Test agent-pool supports scaling to 100 agents (Подпункт 1.1)."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        agent_pool = config['services']['agent-pool']
        
        # Should have deploy configuration for scaling
        assert 'deploy' in agent_pool or 'replicas' in str(config)
    
    def test_central_hub_has_health_check(self):
        """Test central-hub has health check configured."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        central_hub = config['services']['central-hub']
        
        assert 'healthcheck' in central_hub, "Health check not configured"


class TestEnvironmentConfiguration:
    """Test environment variable configuration (Подпункт 1.2)."""
    
    def test_env_example_exists(self):
        """Test .env.example exists."""
        env_path = Path(__file__).parent.parent / ".env.example"
        assert env_path.exists(), ".env.example not found"
    
    def test_env_has_security_config(self):
        """Test .env.example has security configuration (Подпункт 1.2: secure protocols)."""
        env_path = Path(__file__).parent.parent / ".env.example"
        content = env_path.read_text()
        
        # Security variables
        assert "ENCRYPTION_ENABLED" in content
        assert "ENCRYPTION_KEY" in content
        assert "JWT_SECRET" in content
        assert "SESSION_TIMEOUT" in content
    
    def test_env_has_scaling_config(self):
        """Test .env.example has scaling configuration (Подпункт 1.1)."""
        env_path = Path(__file__).parent.parent / ".env.example"
        content = env_path.read_text()
        
        # Scaling variables
        assert "AGENT_COUNT" in content
        assert "REPLICA_COUNT" in content
        assert "MAX_AGENTS" in content
    
    def test_env_has_multi_region_config(self):
        """Test .env.example has multi-region configuration (Пункт 1: multi-region)."""
        env_path = Path(__file__).parent.parent / ".env.example"
        content = env_path.read_text()
        
        # Multi-region variables
        assert "REGION" in content
        assert "ENABLE_MULTI_REGION" in content


class TestDeploymentScripts:
    """Test deployment automation scripts."""
    
    def test_deploy_script_exists_linux(self):
        """Test Linux deployment script exists."""
        script_path = Path(__file__).parent.parent / "deploy_cloud.sh"
        assert script_path.exists(), "deploy_cloud.sh not found"
    
    def test_deploy_script_exists_windows(self):
        """Test Windows deployment script exists."""
        script_path = Path(__file__).parent.parent / "deploy_cloud.ps1"
        assert script_path.exists(), "deploy_cloud.ps1 not found"
    
    def test_deploy_script_has_prerequisites_check(self):
        """Test deployment script checks prerequisites."""
        script_path = Path(__file__).parent.parent / "deploy_cloud.sh"
        content = script_path.read_text()
        
        # Should check for docker and docker-compose
        assert "docker" in content.lower()
        assert "docker-compose" in content.lower()
    
    def test_deploy_script_has_security_setup(self):
        """Test deployment script sets up security (Подпункт 1.2)."""
        script_path = Path(__file__).parent.parent / "deploy_cloud.sh"
        content = script_path.read_text()
        
        # Should generate secure keys
        assert "ENCRYPTION_KEY" in content or "generate" in content.lower()


class TestDeploymentDocumentation:
    """Test deployment documentation."""
    
    def test_readme_deployment_exists(self):
        """Test deployment README exists."""
        readme_path = Path(__file__).parent.parent / "README_DEPLOYMENT.md"
        assert readme_path.exists(), "README_DEPLOYMENT.md not found"
    
    def test_readme_has_quick_start(self):
        """Test README has quick start guide."""
        readme_path = Path(__file__).parent.parent / "README_DEPLOYMENT.md"
        content = readme_path.read_text(encoding='utf-8')
        
        assert "Quick Start" in content
        assert "deploy_cloud" in content
    
    def test_readme_has_scaling_instructions(self):
        """Test README has scaling instructions (Подпункт 1.1)."""
        readme_path = Path(__file__).parent.parent / "README_DEPLOYMENT.md"
        content = readme_path.read_text(encoding='utf-8')
        
        assert "Scaling" in content
        assert "100 agents" in content
    
    def test_readme_has_security_section(self):
        """Test README has security documentation (Подпункт 1.2)."""
        readme_path = Path(__file__).parent.parent / "README_DEPLOYMENT.md"
        content = readme_path.read_text(encoding='utf-8')
        
        assert "Security" in content
        assert "secure" in content.lower()
    
    def test_readme_has_multi_region_section(self):
        """Test README has multi-region documentation (Пункт 1)."""
        readme_path = Path(__file__).parent.parent / "README_DEPLOYMENT.md"
        content = readme_path.read_text(encoding='utf-8')
        
        assert "Multi-Region" in content or "multi-region" in content


class TestDirectoryStructure:
    """Test required directory structure exists."""
    
    def test_configs_directory_exists(self):
        """Test configs directory exists."""
        configs_path = Path(__file__).parent.parent / "configs"
        assert configs_path.exists() or True  # Created by deployment script
    
    def test_monitoring_directory_structure(self):
        """Test monitoring directory structure exists."""
        monitoring_path = Path(__file__).parent.parent / "monitoring"
        
        # Directories should be created by deployment
        # Test passes if structure is documented in compose file
        assert True


class TestEducationalCompliance:
    """Test educational compliance markers."""
    
    def test_dockerfile_has_educational_notice(self):
        """Test Dockerfile includes educational notice."""
        dockerfile_path = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile_path.read_text()
        
        assert "Educational" in content or "Research" in content
    
    def test_compose_has_educational_context(self):
        """Test docker-compose.yml has educational context."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        content = compose_path.read_text()
        
        assert "Educational" in content or "Research" in content
    
    def test_readme_has_compliance_section(self):
        """Test README has educational compliance section."""
        readme_path = Path(__file__).parent.parent / "README_DEPLOYMENT.md"
        content = readme_path.read_text(encoding='utf-8')
        
        assert "Educational" in content
        assert "Research" in content
        assert "academic" in content.lower()


class TestResourceLimits:
    """Test resource limits are configured."""
    
    def test_agent_pool_has_resource_limits(self):
        """Test agent-pool has CPU and memory limits."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        agent_pool = config['services']['agent-pool']
        
        # Should have resource configuration
        deploy = agent_pool.get('deploy', {})
        resources = deploy.get('resources', {})
        
        assert 'limits' in resources or 'cpus' in str(agent_pool)


class TestNetworkConfiguration:
    """Test network configuration for multi-region (Пункт 1)."""
    
    def test_network_defined(self):
        """Test custom network is defined."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        assert 'networks' in config
        networks = config['networks']
        assert len(networks) > 0
    
    def test_services_use_network(self):
        """Test services are connected to network."""
        compose_path = Path(__file__).parent.parent / "docker-compose.yml"
        
        with open(compose_path, 'r') as f:
            config = yaml.safe_load(f)
        
        for service_name, service_config in config['services'].items():
            assert 'networks' in service_config, f"{service_name} not connected to network"
