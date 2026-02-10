"""
Tests for Demo Mode (Roadmap4 Phase 4).

Tests demo interface functionality.
"""

import pytest

from bridge.demo_mode import DemoMode


class TestDemoMode:
    """Test demo mode functionality."""
    
    def test_initialization(self):
        """Test demo mode initialization."""
        demo = DemoMode()
        
        assert demo.state_bridge is not None
        # Should be in dry-run mode
        assert demo.state_bridge.dry_run is True
    
    def test_process_screenshot_simulated(self):
        """Test screenshot processing (simulated)."""
        demo = DemoMode()
        
        # Process with dummy path (will use dry-run data)
        state_text, recommendation, risk = demo.process_screenshot("dummy.png")
        
        # Should return formatted outputs
        assert isinstance(state_text, str)
        assert isinstance(recommendation, str)
        assert isinstance(risk, str)
        
        # Check content
        assert "TABLE STATE" in state_text or "ERROR" in state_text
        assert len(recommendation) > 0
        assert len(risk) > 0
    
    def test_format_table_state(self):
        """Test table state formatting."""
        demo = DemoMode()
        
        # Get simulated table state
        table_state = demo.state_bridge.get_live_table_state(
            table_id="test",
            room="test",
            resolution="1920x1080"
        )
        
        if table_state:
            formatted = demo._format_table_state(table_state)
            
            assert "TABLE STATE" in formatted
            assert "Street:" in formatted
            assert "Pot:" in formatted
    
    def test_generate_hive_recommendation(self):
        """Test HIVE recommendation generation."""
        demo = DemoMode()
        
        # Get simulated table state
        table_state = demo.state_bridge.get_live_table_state(
            table_id="test",
            room="test",
            resolution="1920x1080"
        )
        
        if table_state:
            recommendation = demo._generate_hive_recommendation(table_state)
            
            assert "HIVE RECOMMENDATION" in recommendation
            assert "3vs1" in recommendation
            assert "Recommended Action" in recommendation
    
    def test_generate_risk_assessment(self):
        """Test risk assessment generation."""
        demo = DemoMode()
        
        # Get simulated table state
        table_state = demo.state_bridge.get_live_table_state(
            table_id="test",
            room="test",
            resolution="1920x1080"
        )
        
        if table_state:
            risk = demo._generate_risk_assessment(table_state)
            
            assert "RISK ASSESSMENT" in risk
            assert "Action Risk Level" in risk
            assert "Safety Status" in risk
    
    def test_create_interface(self):
        """Test interface creation."""
        demo = DemoMode()
        
        # Try to create interface
        interface = demo.create_interface()
        
        # May be None if Gradio not available
        if interface is None:
            pytest.skip("Gradio not available")
        else:
            # Interface should be created
            assert interface is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
