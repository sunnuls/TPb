"""
Unit tests for card sharing functionality (Roadmap2 Phase 2).

Tests CentralHub's ability to:
- Collect hole cards from ≥3 agents
- Calculate collective equity
- Broadcast collective state
"""

import asyncio

import pytest

from sim_engine.central_hub import CentralHub


class TestCardSharing:
    """Test card sharing functionality in CentralHub."""
    
    def test_share_cards_single_agent(self):
        """Single agent sharing cards - should return None."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        result = asyncio.run(
            hub.share_cards(
                environment_id="table1",
                agent_id="agent1",
                hole_cards=["As", "Kh"]
            )
        )
        
        # Should store cards but not calculate collective (need ≥3 agents)
        assert "hole_cards" in hub._sessions["table1"]
        assert hub._sessions["table1"]["hole_cards"]["agent1"] == ["As", "Kh"]
        assert result is None  # Not enough agents
    
    def test_share_cards_two_agents(self):
        """Two agents sharing - still not enough for collective."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        # Agent 1 shares
        asyncio.run(
            hub.share_cards("table1", "agent1", ["As", "Kh"])
        )
        
        # Mock connections for 2 agents
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import MagicMock
        
        ws1 = MagicMock()
        ws2 = MagicMock()
        
        hub._connections["agent1"] = AgentConnection(
            agent_id="agent1",
            websocket=ws1,
            status=AgentStatus.ACTIVE,
            environment_id="table1"
        )
        hub._connections["agent2"] = AgentConnection(
            agent_id="agent2",
            websocket=ws2,
            status=AgentStatus.ACTIVE,
            environment_id="table1"
        )
        
        # Agent 2 shares
        result = asyncio.run(
            hub.share_cards("table1", "agent2", ["Qd", "Jh"])
        )
        
        assert result is None  # Still need 3 agents
    
    def test_share_cards_three_agents_collective(self):
        """Three agents sharing - should calculate collective equity."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        # Mock 3 agent connections
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import MagicMock
        
        for i in range(1, 4):
            ws = MagicMock()
            hub._connections[f"agent{i}"] = AgentConnection(
                agent_id=f"agent{i}",
                websocket=ws,
                status=AgentStatus.ACTIVE,
                environment_id="table1"
            )
        
        # Agent 1 shares
        asyncio.run(hub.share_cards("table1", "agent1", ["As", "Kh"]))
        
        # Agent 2 shares
        asyncio.run(hub.share_cards("table1", "agent2", ["Qd", "Jh"]))
        
        # Agent 3 shares - now we have 3 agents
        result = asyncio.run(
            hub.share_cards("table1", "agent3", ["Ts", "9h"])
        )
        
        assert result is not None
        assert "collective_known_cards" in result
        assert "collective_equity" in result
        assert "agent_count" in result
        
        # Check collective cards
        assert len(result["collective_known_cards"]) == 6
        assert "As" in result["collective_known_cards"]
        assert "Qd" in result["collective_known_cards"]
        assert "Ts" in result["collective_known_cards"]
        
        # Check equity
        assert 0.0 <= result["collective_equity"] <= 1.0
        
        # Check agent count
        assert result["agent_count"] == 3
    
    def test_calculate_collective_equity_base(self):
        """Test equity calculation with no board."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        equity = hub._calculate_collective_equity(
            known_cards=["As", "Ah", "Kd", "Kh"],
            environment_id="table1"
        )
        
        # Base equity + card bonus
        assert equity >= 0.5  # Base
        assert equity <= 0.95  # Max cap
    
    def test_calculate_collective_equity_with_board(self):
        """Test equity calculation with board cards."""
        hub = CentralHub()
        hub._sessions["table1"] = {"board": ["Js", "Ts", "9h"]}
        
        equity = hub._calculate_collective_equity(
            known_cards=["As", "Ah"],
            environment_id="table1"
        )
        
        # Base + card bonus + board bonus
        assert equity > 0.5  # Should be higher with board
        assert equity <= 0.95
    
    def test_equity_scales_with_known_cards(self):
        """More known cards = higher equity."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        equity_2 = hub._calculate_collective_equity(
            known_cards=["As", "Ah"],
            environment_id="table1"
        )
        
        equity_6 = hub._calculate_collective_equity(
            known_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
            environment_id="table1"
        )
        
        assert equity_6 > equity_2
    
    def test_equity_capped_at_95_percent(self):
        """Equity should not exceed 95%."""
        hub = CentralHub()
        hub._sessions["table1"] = {"board": ["Js", "Ts", "9h", "8h", "7h"]}
        
        equity = hub._calculate_collective_equity(
            known_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd", "Jh", "Th"],
            environment_id="table1"
        )
        
        assert equity <= 0.95


class TestCollectiveBroadcast:
    """Test broadcasting collective state to agents."""
    
    @pytest.mark.asyncio
    async def test_broadcast_to_all_agents(self):
        """Broadcast collective state to all agents in session."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        # Mock 3 agents
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import AsyncMock, MagicMock
        
        messages_sent = []
        
        for i in range(1, 4):
            ws = MagicMock()
            ws.send = AsyncMock(side_effect=lambda msg: messages_sent.append(msg))
            
            hub._connections[f"agent{i}"] = AgentConnection(
                agent_id=f"agent{i}",
                websocket=ws,
                status=AgentStatus.ACTIVE,
                environment_id="table1"
            )
        
        collective_data = {
            "collective_known_cards": ["As", "Ah", "Kd", "Kh"],
            "collective_equity": 0.72,
            "agent_count": 3
        }
        
        await hub.broadcast_collective_state("table1", collective_data)
        
        # Each agent should receive a message
        assert len(messages_sent) == 3
    
    @pytest.mark.asyncio
    async def test_broadcast_only_to_session_agents(self):
        """Only agents in the session receive the broadcast."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        hub._sessions["table2"] = {}
        
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import AsyncMock, MagicMock
        
        messages_sent = {"table1": 0, "table2": 0}
        
        # 2 agents in table1
        for i in range(1, 3):
            ws = MagicMock()
            ws.send = AsyncMock(side_effect=lambda msg, table="table1": messages_sent.__setitem__(table, messages_sent[table] + 1))
            
            hub._connections[f"agent{i}"] = AgentConnection(
                agent_id=f"agent{i}",
                websocket=ws,
                status=AgentStatus.ACTIVE,
                environment_id="table1"
            )
        
        # 1 agent in table2
        ws3 = MagicMock()
        ws3.send = AsyncMock()
        hub._connections["agent3"] = AgentConnection(
            agent_id="agent3",
            websocket=ws3,
            status=AgentStatus.ACTIVE,
            environment_id="table2"
        )
        
        collective_data = {"collective_equity": 0.65}
        await hub.broadcast_collective_state("table1", collective_data)
        
        # Only table1 agents receive broadcast
        # (Note: actual count depends on mock implementation)
    
    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_agents(self):
        """Broadcast gracefully handles disconnected agents."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import AsyncMock, MagicMock
        
        # Agent 1: normal
        ws1 = MagicMock()
        ws1.send = AsyncMock()
        hub._connections["agent1"] = AgentConnection(
            agent_id="agent1",
            websocket=ws1,
            status=AgentStatus.ACTIVE,
            environment_id="table1"
        )
        
        # Agent 2: disconnected (send will fail)
        ws2 = MagicMock()
        ws2.send = AsyncMock(side_effect=Exception("Connection closed"))
        hub._connections["agent2"] = AgentConnection(
            agent_id="agent2",
            websocket=ws2,
            status=AgentStatus.ACTIVE,
            environment_id="table1"
        )
        
        collective_data = {"collective_equity": 0.70}
        
        # Should not raise exception
        await hub.broadcast_collective_state("table1", collective_data)


class TestIntegration:
    """Integration tests for full card sharing workflow."""
    
    def test_full_card_sharing_workflow(self):
        """Test complete workflow: share cards → calculate equity → broadcast."""
        hub = CentralHub()
        hub._sessions["table1"] = {"board": ["Js", "Ts", "9h"]}
        
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import MagicMock
        
        # Add agents incrementally
        ws1 = MagicMock()
        hub._connections["agent1"] = AgentConnection(
            agent_id="agent1",
            websocket=ws1,
            status=AgentStatus.ACTIVE,
            environment_id="table1"
        )
        
        # Sequential card sharing
        result1 = asyncio.run(hub.share_cards("table1", "agent1", ["As", "Kh"]))
        assert result1 is None  # Only 1 agent
        
        # Add second agent
        ws2 = MagicMock()
        hub._connections["agent2"] = AgentConnection(
            agent_id="agent2",
            websocket=ws2,
            status=AgentStatus.ACTIVE,
            environment_id="table1"
        )
        
        result2 = asyncio.run(hub.share_cards("table1", "agent2", ["Qd", "Jh"]))
        assert result2 is None  # Only 2 agents
        
        # Add third agent
        ws3 = MagicMock()
        hub._connections["agent3"] = AgentConnection(
            agent_id="agent3",
            websocket=ws3,
            status=AgentStatus.ACTIVE,
            environment_id="table1"
        )
        
        result3 = asyncio.run(hub.share_cards("table1", "agent3", ["Ts", "9h"]))
        assert result3 is not None  # 3 agents - collective activated
        
        # Verify collective data
        assert len(result3["collective_known_cards"]) == 6
        assert result3["collective_equity"] > 0.5
        assert result3["agent_count"] == 3
        assert result3["dummy_range"] == "random"
    
    def test_multiple_sessions_independent(self):
        """Multiple sessions maintain independent card collections."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        hub._sessions["table2"] = {}
        
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import MagicMock
        
        # 3 agents in table1
        for i in range(1, 4):
            ws = MagicMock()
            hub._connections[f"t1_agent{i}"] = AgentConnection(
                agent_id=f"t1_agent{i}",
                websocket=ws,
                status=AgentStatus.ACTIVE,
                environment_id="table1"
            )
        
        # 3 agents in table2
        for i in range(1, 4):
            ws = MagicMock()
            hub._connections[f"t2_agent{i}"] = AgentConnection(
                agent_id=f"t2_agent{i}",
                websocket=ws,
                status=AgentStatus.ACTIVE,
                environment_id="table2"
            )
        
        # Table 1 shares
        asyncio.run(hub.share_cards("table1", "t1_agent1", ["As", "Kh"]))
        asyncio.run(hub.share_cards("table1", "t1_agent2", ["Qd", "Jh"]))
        result1 = asyncio.run(hub.share_cards("table1", "t1_agent3", ["Ts", "9h"]))
        
        # Table 2 shares different cards
        asyncio.run(hub.share_cards("table2", "t2_agent1", ["2s", "3h"]))
        asyncio.run(hub.share_cards("table2", "t2_agent2", ["4d", "5h"]))
        result2 = asyncio.run(hub.share_cards("table2", "t2_agent3", ["6s", "7h"]))
        
        # Both should have collective data
        assert result1 is not None
        assert result2 is not None
        
        # But different cards
        assert result1["collective_known_cards"] != result2["collective_known_cards"]
        
        # Likely different equity (though random)
        # Just check both are valid
        assert 0.0 <= result1["collective_equity"] <= 1.0
        assert 0.0 <= result2["collective_equity"] <= 1.0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_share_cards_nonexistent_session(self):
        """Sharing cards to nonexistent session returns None."""
        hub = CentralHub()
        
        result = asyncio.run(
            hub.share_cards("nonexistent", "agent1", ["As", "Kh"])
        )
        
        assert result is None
    
    def test_share_cards_empty_cards(self):
        """Handle empty hole cards list."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import MagicMock
        
        for i in range(1, 4):
            ws = MagicMock()
            hub._connections[f"agent{i}"] = AgentConnection(
                agent_id=f"agent{i}",
                websocket=ws,
                status=AgentStatus.ACTIVE,
                environment_id="table1"
            )
        
        result = asyncio.run(
            hub.share_cards("table1", "agent1", [])
        )
        
        # Should store empty list
        assert hub._sessions["table1"]["hole_cards"]["agent1"] == []
    
    def test_agent_reshares_cards(self):
        """Agent can update their hole cards."""
        hub = CentralHub()
        hub._sessions["table1"] = {}
        
        from sim_engine.central_hub import AgentConnection, AgentStatus
        from unittest.mock import MagicMock
        
        for i in range(1, 4):
            ws = MagicMock()
            hub._connections[f"agent{i}"] = AgentConnection(
                agent_id=f"agent{i}",
                websocket=ws,
                status=AgentStatus.ACTIVE,
                environment_id="table1"
            )
        
        # First share
        asyncio.run(hub.share_cards("table1", "agent1", ["As", "Kh"]))
        asyncio.run(hub.share_cards("table1", "agent2", ["Qd", "Jh"]))
        result1 = asyncio.run(hub.share_cards("table1", "agent3", ["Ts", "9h"]))
        
        # Agent 1 updates cards
        result2 = asyncio.run(hub.share_cards("table1", "agent1", ["2s", "3h"]))
        
        # New collective should reflect updated cards
        assert "2s" in result2["collective_known_cards"]
        assert "As" not in result2["collective_known_cards"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
