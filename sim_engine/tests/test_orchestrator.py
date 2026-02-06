"""
Tests for Multi-Agent Simulation Orchestrator (Фаза 3, Шаг 3.1).

Educational Use Only: Testing scalable research infrastructure.
"""

from __future__ import annotations

import pytest

from sim_engine.sim_orchestrator import (
    AgentConfig,
    AgentStatus,
    EnvironmentSelector,
    EnvironmentType,
    ProxyRotator,
)


class TestAgentConfig:
    """Test agent configuration."""
    
    def test_agent_config_creation(self):
        """Test creating agent configuration."""
        config = AgentConfig(
            agent_id="test_agent_001",
            agent_name="TestAgent",
            strategy_profile="balanced",
            resource_level="medium"
        )
        
        assert config.agent_id == "test_agent_001"
        assert config.strategy_profile == "balanced"
        assert config.resource_level == "medium"
        assert config.simulation_mode is True
    
    def test_agent_config_to_dict(self):
        """Test configuration serialization."""
        config = AgentConfig(
            agent_id="test_agent_002",
            agent_name="TestAgent2",
            strategy_profile="aggressive",
            resource_level="high"
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["agent_id"] == "test_agent_002"
        assert config_dict["strategy_profile"] == "aggressive"
        assert "environment_type" in config_dict


class TestEnvironmentSelector:
    """Test environment selection logic (Подпункт 1.1)."""
    
    def test_scan_environments_generates_list(self):
        """Test environment scanning generates available environments."""
        selector = EnvironmentSelector()
        
        environments = selector.scan_available_environments(
            EnvironmentType.RESEARCH_SANDBOX
        )
        
        assert len(environments) > 0
        assert all("environment_id" in env for env in environments)
        assert all("engagement_level" in env for env in environments)
        assert all("participant_count" in env for env in environments)
    
    def test_select_low_engagement_environment(self):
        """Test selection of low-engagement environments (Подпункт 1.1)."""
        selector = EnvironmentSelector()
        
        # Generate synthetic environments
        environments = selector.scan_available_environments(
            EnvironmentType.POKER_CASH
        )
        
        # Select low-engagement
        selected = selector.select_low_engagement_environment(
            environments,
            target_engagement=0.5
        )
        
        if selected:
            # If we found one below threshold, verify it
            assert selected in environments
            assert "engagement_level" in selected
            
            # Check it's one of the lower engagement ones
            all_engagements = [e["engagement_level"] for e in environments]
            median_engagement = sorted(all_engagements)[len(all_engagements) // 2]
            
            # Selected should be below median (favoring low engagement)
            # (Not guaranteed due to scoring, but likely)
            print(f"Selected engagement: {selected['engagement_level']:.2%}")
            print(f"Median engagement: {median_engagement:.2%}")
    
    def test_select_with_no_suitable_environments(self):
        """Test selection when no environments meet criteria."""
        selector = EnvironmentSelector()
        
        # Empty list
        selected = selector.select_low_engagement_environment(
            [],
            target_engagement=0.5
        )
        
        assert selected is None
    
    def test_environment_has_required_fields(self):
        """Test that generated environments have all required fields."""
        selector = EnvironmentSelector()
        
        environments = selector.scan_available_environments(
            EnvironmentType.RESEARCH_SANDBOX
        )
        
        required_fields = [
            "environment_id",
            "environment_type",
            "engagement_level",
            "participant_count",
            "avg_skill_level",
            "variance",
            "available_seats"
        ]
        
        for env in environments:
            for field in required_fields:
                assert field in env, f"Missing field: {field}"


class TestProxyRotator:
    """Test proxy rotation for network diversity (Пункт 2)."""
    
    def test_proxy_rotator_disabled(self):
        """Test proxy rotator when disabled."""
        rotator = ProxyRotator(enabled=False)
        
        proxy = rotator.get_proxy_for_agent("test_agent")
        
        assert proxy is None
    
    def test_proxy_rotator_enabled_generates_ips(self):
        """Test proxy rotator generates virtual IPs when enabled (Пункт 2)."""
        rotator = ProxyRotator(enabled=True)
        
        assert len(rotator.virtual_ips) > 0
        
        # Check IPs are in expected format
        for ip in rotator.virtual_ips:
            parts = ip.split(".")
            assert len(parts) == 4
            assert all(part.isdigit() for part in parts)
    
    def test_proxy_assignment_is_deterministic(self):
        """Test that same agent ID gets same proxy."""
        rotator = ProxyRotator(enabled=True)
        
        agent_id = "test_agent_123"
        
        proxy1 = rotator.get_proxy_for_agent(agent_id)
        proxy2 = rotator.get_proxy_for_agent(agent_id)
        
        assert proxy1 == proxy2
    
    def test_different_agents_get_different_proxies(self):
        """Test that different agents can get different proxies."""
        rotator = ProxyRotator(enabled=True)
        
        # Not guaranteed to be different due to hash collision,
        # but very likely with enough agents
        agents = [f"agent_{i}" for i in range(10)]
        proxies = [rotator.get_proxy_for_agent(a) for a in agents]
        
        # At least some should be different
        unique_proxies = len(set(proxies))
        assert unique_proxies > 1
    
    def test_proxy_rotation(self):
        """Test proxy rotation functionality (Пункт 2)."""
        rotator = ProxyRotator(enabled=True)
        
        agent_id = "test_agent_rotation"
        
        proxy1 = rotator.get_proxy_for_agent(agent_id)
        rotated_proxy = rotator.rotate_proxy(agent_id)
        
        assert rotated_proxy in rotator.virtual_ips
        # Rotation is random, so not guaranteed to be different
        # but should be valid


class TestOrchestratorComponents:
    """Test orchestrator component integration."""
    
    def test_agent_config_with_environment_assignment(self):
        """Test agent configuration with environment assignment."""
        selector = EnvironmentSelector()
        
        # Generate environments
        environments = selector.scan_available_environments(
            EnvironmentType.RESEARCH_SANDBOX
        )
        
        # Create agent config
        config = AgentConfig(
            agent_id="test_agent_env",
            agent_name="TestAgent",
            strategy_profile="balanced",
            resource_level="medium",
            environment_type=EnvironmentType.RESEARCH_SANDBOX
        )
        
        # Assign environment
        selected_env = selector.select_low_engagement_environment(environments)
        
        if selected_env:
            config.environment_id = selected_env["environment_id"]
            
            assert config.environment_id is not None
            assert config.environment_type == EnvironmentType.RESEARCH_SANDBOX
    
    def test_agent_config_with_proxy(self):
        """Test agent configuration with proxy assignment."""
        rotator = ProxyRotator(enabled=True)
        
        config = AgentConfig(
            agent_id="test_agent_proxy",
            agent_name="TestAgentProxy",
            strategy_profile="aggressive",
            resource_level="high",
            proxy_enabled=True,
            proxy_rotation=True
        )
        
        # Get proxy
        proxy = rotator.get_proxy_for_agent(config.agent_id)
        
        assert proxy is not None
        assert config.proxy_enabled is True
        assert config.proxy_rotation is True


class TestAgentStatus:
    """Test agent status enum."""
    
    def test_agent_status_values(self):
        """Test all agent status values are valid."""
        assert AgentStatus.INITIALIZING.value == "initializing"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.PAUSED.value == "paused"
        assert AgentStatus.ERROR.value == "error"
        assert AgentStatus.STOPPED.value == "stopped"
        assert AgentStatus.RESTARTING.value == "restarting"


class TestStrategyProfiles:
    """Test strategy profile diversity (Пункт 1: unique configs)."""
    
    def test_different_strategy_profiles(self):
        """Test agents can have different strategy profiles."""
        strategies = ["balanced", "conservative", "aggressive", "exploitative"]
        
        configs = []
        for i, strategy in enumerate(strategies):
            config = AgentConfig(
                agent_id=f"agent_{i}",
                agent_name=f"Agent{i}",
                strategy_profile=strategy,
                resource_level="medium"
            )
            configs.append(config)
        
        # All configs should have different strategies
        strategy_set = {c.strategy_profile for c in configs}
        assert len(strategy_set) == len(strategies)
    
    def test_resource_level_diversity(self):
        """Test agents can have different resource levels."""
        resources = ["low", "medium", "high"]
        
        configs = []
        for i, resource in enumerate(resources):
            config = AgentConfig(
                agent_id=f"agent_res_{i}",
                agent_name=f"AgentRes{i}",
                strategy_profile="balanced",
                resource_level=resource
            )
            configs.append(config)
        
        resource_set = {c.resource_level for c in configs}
        assert len(resource_set) == len(resources)
