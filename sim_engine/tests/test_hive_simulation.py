"""
Unit tests for HIVE simulation module (Roadmap2 Phase 3).

Tests full 3vs1 simulation workflow: lobby scan, table join,
gameplay against dummy, and metrics tracking.
"""

import pytest
from sim_engine.hive_simulation import (
    HandResult,
    HiveSimulation,
    SimulationMetrics,
)


class TestSimulationMetrics:
    """Test simulation metrics tracking."""
    
    def test_metrics_initialization(self):
        """Metrics start at zero."""
        metrics = SimulationMetrics()
        
        assert metrics.total_hands == 0
        assert metrics.hive_wins == 0
        assert metrics.dummy_wins == 0
        assert metrics.total_profit == 0.0
        assert metrics.coordination_bonus == 0.0
    
    def test_winrate_calculation(self):
        """Winrate is wins/total."""
        metrics = SimulationMetrics()
        metrics.total_hands = 100
        metrics.hive_wins = 60
        
        assert metrics.winrate() == 0.60
    
    def test_winrate_zero_hands(self):
        """Winrate is 0 with no hands."""
        metrics = SimulationMetrics()
        
        assert metrics.winrate() == 0.0
    
    def test_roi_calculation(self):
        """ROI is profit per hand * 100."""
        metrics = SimulationMetrics()
        metrics.total_hands = 100
        metrics.total_profit = 250.0
        
        # ROI = (250 / 100) * 100 = 250%
        assert metrics.roi() == 250.0
    
    def test_bb_per_100_calculation(self):
        """bb/100 is profit per 100 hands."""
        metrics = SimulationMetrics()
        metrics.total_hands = 50
        metrics.total_profit = 100.0
        
        # bb/100 = (100 / 50) * 100 = 200
        assert metrics.bb_per_100() == 200.0


class TestHandResult:
    """Test hand result data structure."""
    
    def test_hand_result_creation(self):
        """Can create hand result."""
        result = HandResult(
            hand_number=1,
            hive_cards=["As", "Ah", "Kd", "Kh", "Qc", "Qd"],
            dummy_cards=["Js", "Jh"],
            board=["Ts", "9h", "8d", "7c", "6s"],
            winner="hive",
            pot_size=200.0,
            hive_profit=100.0,
            collective_equity=0.72
        )
        
        assert result.hand_number == 1
        assert len(result.hive_cards) == 6
        assert len(result.dummy_cards) == 2
        assert len(result.board) == 5
        assert result.winner == "hive"
        assert result.pot_size == 200.0
        assert result.hive_profit == 100.0


class TestHiveSimulationSetup:
    """Test simulation setup and initialization."""
    
    def test_simulation_initialization(self):
        """Can initialize simulation."""
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=100,
            lobby_size=50
        )
        
        assert sim.agent_count == 10
        assert sim.hands_per_session == 100
        assert sim.lobby_size == 50
        assert len(sim.agents) == 0  # Not setup yet
    
    def test_setup_creates_agents(self):
        """Setup creates agent pool."""
        sim = HiveSimulation(agent_count=20, lobby_size=30)
        sim.setup()
        
        assert len(sim.agents) == 20
        assert all(a.agent_id.startswith("agent_") for a in sim.agents)
    
    def test_setup_creates_lobby(self):
        """Setup creates virtual lobby."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        sim.setup()
        
        assert sim.lobby is not None
        assert len(sim.lobby.tables) == 50


class TestTableFinding:
    """Test HIVE opportunity finding and joining."""
    
    def test_find_and_join_table_success(self):
        """Successfully find and join HIVE table."""
        sim = HiveSimulation(agent_count=10, lobby_size=100)
        sim.setup()
        
        success = sim.find_and_join_table()
        
        # Should find at least one opportunity in 100 tables
        if success:
            assert sim.current_table is not None
            assert sim.hive_group is not None
            assert len(sim.hive_group.agents) == 3
    
    def test_find_table_without_setup_fails(self):
        """Finding table without setup fails."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        
        success = sim.find_and_join_table()
        
        assert success is False
    
    def test_hive_group_uses_available_agents(self):
        """HIVE group uses first 3 available agents."""
        sim = HiveSimulation(agent_count=10, lobby_size=100)
        sim.setup()
        
        if sim.find_and_join_table():
            # Check agents are marked as in environment
            hive_agents = sim.hive_group.agents
            assert all(a.current_environment is not None for a in hive_agents)


class TestDummyOpponentSetup:
    """Test dummy opponent creation."""
    
    def test_setup_dummy_creates_opponent(self):
        """Setup creates dummy opponent."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        sim.setup()
        sim.setup_dummy_opponent()
        
        assert sim.dummy is not None
        assert sim.dummy.stack > 0
        assert sim.dummy.variance >= 0


class TestHandPlaying:
    """Test individual hand gameplay."""
    
    def test_play_hand_generates_cards(self):
        """Playing hand generates cards for all players."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        sim.setup()
        sim.setup_dummy_opponent()
        sim.find_and_join_table()
        
        if sim.hive_group and sim.dummy:
            result = sim.play_hand(1)
            
            assert len(result.hive_cards) == 6  # 3 agents * 2 cards
            assert len(result.dummy_cards) == 2
            assert len(result.board) == 5
    
    def test_play_hand_determines_winner(self):
        """Hand has winner (hive or dummy)."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        sim.setup()
        sim.setup_dummy_opponent()
        sim.find_and_join_table()
        
        if sim.hive_group and sim.dummy:
            result = sim.play_hand(1)
            
            assert result.winner in ["hive", "dummy"]
    
    def test_play_hand_calculates_profit(self):
        """Hand result includes profit/loss."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        sim.setup()
        sim.setup_dummy_opponent()
        sim.find_and_join_table()
        
        if sim.hive_group and sim.dummy:
            result = sim.play_hand(1)
            
            assert result.hive_profit != 0.0
            assert result.pot_size > 0
    
    def test_play_hand_tracks_equity(self):
        """Hand result includes collective equity."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        sim.setup()
        sim.setup_dummy_opponent()
        sim.find_and_join_table()
        
        if sim.hive_group and sim.dummy:
            result = sim.play_hand(1)
            
            assert 0.0 <= result.collective_equity <= 1.0


class TestSession:
    """Test full session gameplay."""
    
    def test_play_session_updates_metrics(self):
        """Session updates metrics."""
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=10,  # Small for testing
            lobby_size=50,
            log_interval=5
        )
        sim.setup()
        sim.setup_dummy_opponent()
        
        if sim.find_and_join_table():
            sim.play_session()
            
            assert sim.metrics.total_hands == 10
            assert sim.metrics.hive_wins + sim.metrics.dummy_wins == 10
    
    def test_session_records_hand_history(self):
        """Session records all hands."""
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=5,
            lobby_size=50
        )
        sim.setup()
        sim.setup_dummy_opponent()
        
        if sim.find_and_join_table():
            sim.play_session()
            
            assert len(sim.hand_history) == 5
    
    def test_session_calculates_coordination_bonus(self):
        """Session calculates coordination bonus."""
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=10,
            lobby_size=50
        )
        sim.setup()
        sim.setup_dummy_opponent()
        
        if sim.find_and_join_table():
            sim.play_session()
            
            # Coordination bonus should be calculated
            # (Value depends on win/loss, so just check it's set)
            assert sim.metrics.coordination_bonus != 0.0 or sim.metrics.total_profit == 0.0


class TestFullSimulation:
    """Test complete simulation workflow."""
    
    def test_run_completes_workflow(self):
        """Run executes full workflow."""
        sim = HiveSimulation(
            agent_count=20,
            hands_per_session=50,
            lobby_size=100,
            log_interval=25
        )
        
        metrics = sim.run()
        
        # Should complete and return metrics
        assert metrics is not None
        # If table found, should have played hands
        if sim.current_table:
            assert metrics.total_hands > 0
    
    def test_run_without_table_returns_empty_metrics(self):
        """Run with no HIVE opportunities returns empty metrics."""
        # Very small lobby - might not find opportunities
        sim = HiveSimulation(
            agent_count=5,
            hands_per_session=10,
            lobby_size=5  # Very small
        )
        
        metrics = sim.run()
        
        # Should return metrics even if no table found
        assert metrics is not None


class TestMetricsAccuracy:
    """Test metrics calculation accuracy."""
    
    def test_profit_sums_correctly(self):
        """Total profit is sum of hand profits."""
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=10,
            lobby_size=50
        )
        sim.setup()
        sim.setup_dummy_opponent()
        
        if sim.find_and_join_table():
            sim.play_session()
            
            # Calculate expected profit from hand history
            expected_profit = sum(h.hive_profit for h in sim.hand_history)
            
            assert abs(sim.metrics.total_profit - expected_profit) < 0.01
    
    def test_win_count_matches_results(self):
        """Win counts match hand results."""
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=10,
            lobby_size=50
        )
        sim.setup()
        sim.setup_dummy_opponent()
        
        if sim.find_and_join_table():
            sim.play_session()
            
            hive_wins = sum(1 for h in sim.hand_history if h.winner == "hive")
            dummy_wins = sum(1 for h in sim.hand_history if h.winner == "dummy")
            
            assert sim.metrics.hive_wins == hive_wins
            assert sim.metrics.dummy_wins == dummy_wins


class TestCardGeneration:
    """Test card generation utilities."""
    
    def test_generate_hive_cards_returns_six(self):
        """HIVE card generation returns 6 cards."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        
        cards = sim._generate_hive_cards()
        
        assert len(cards) == 6
        assert all(len(c) == 2 for c in cards)  # Rank + suit
    
    def test_generate_dummy_cards_returns_two(self):
        """Dummy card generation returns 2 cards."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        
        cards = sim._generate_dummy_cards()
        
        assert len(cards) == 2
        assert all(len(c) == 2 for c in cards)
    
    def test_generate_board_returns_five(self):
        """Board generation returns 5 cards."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        
        board = sim._generate_board()
        
        assert len(board) == 5
        assert all(len(c) == 2 for c in board)


class TestEquityCalculation:
    """Test collective equity calculation."""
    
    def test_equity_in_valid_range(self):
        """Equity is between 0 and 1."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        
        hive_cards = ["As", "Ah", "Kd", "Kh", "Qc", "Qd"]
        board = ["Js", "Ts", "9h", "8d", "7c"]
        
        equity = sim._calculate_collective_equity(hive_cards, board)
        
        assert 0.0 <= equity <= 1.0
    
    def test_more_cards_higher_equity(self):
        """More known cards tends toward higher equity."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        
        few_cards = ["As", "Ah"]
        many_cards = ["As", "Ah", "Kd", "Kh", "Qc", "Qd"]
        board = ["Js", "Ts", "9h"]
        
        equity_few = sim._calculate_collective_equity(few_cards, board)
        equity_many = sim._calculate_collective_equity(many_cards, board)
        
        # Many cards should have higher base equity (before randomness)
        # Run multiple times and check average
        avg_few = sum(sim._calculate_collective_equity(few_cards, board) for _ in range(20)) / 20
        avg_many = sum(sim._calculate_collective_equity(many_cards, board) for _ in range(20)) / 20
        
        assert avg_many > avg_few


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_simulation_with_zero_agents(self):
        """Handle zero agents gracefully."""
        sim = HiveSimulation(agent_count=0, lobby_size=50)
        sim.setup()
        
        assert len(sim.agents) == 0
        success = sim.find_and_join_table()
        assert success is False
    
    def test_simulation_with_few_agents(self):
        """Handle too few agents for HIVE."""
        sim = HiveSimulation(agent_count=2, lobby_size=50)
        sim.setup()
        
        success = sim.find_and_join_table()
        # Might fail to form HIVE group
        if not success:
            assert sim.hive_group is None
    
    def test_session_without_hive_or_dummy(self):
        """Session without HIVE or dummy logs error."""
        sim = HiveSimulation(agent_count=10, lobby_size=50)
        
        # Don't setup or find table
        sim.play_session()
        
        # Should not crash, but metrics stay at zero
        assert sim.metrics.total_hands == 0


class TestLogging:
    """Test simulation logging."""
    
    def test_simulation_logs_progress(self):
        """Simulation logs progress at intervals."""
        # This test primarily checks that logging doesn't crash
        sim = HiveSimulation(
            agent_count=10,
            hands_per_session=10,
            lobby_size=50,
            log_interval=5
        )
        
        metrics = sim.run()
        
        # Should complete without errors
        assert metrics is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
