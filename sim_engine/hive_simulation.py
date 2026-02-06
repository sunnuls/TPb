"""
HIVE Simulation Loop (Roadmap2 Phase 3).

Full 3vs1 simulation workflow:
- 100 agents scan virtual lobby
- Find profitable tables (HIVE opportunities)
- 3 agents coordinate to join selected table
- Play 1000 hands against 1 dummy opponent
- Log winrate, EV, pots won, coordination bonus

Educational Use Only: For research into emergent multi-agent
coordination strategies. Not for production use.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from sim_engine.agent import HiveAgent, HiveGroup
from sim_engine.collective_decision import (
    CollectiveDecisionEngine,
    CollectiveState,
)
from sim_engine.dummy_opponent import (
    DummyOpponent,
    estimate_hand_strength,
    generate_random_opponent,
)
from sim_engine.table_selection import (
    VirtualLobby,
    VirtualTable,
    find_hive_opportunities,
    select_best_hive_table,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class HandResult:
    """
    Result of a single poker hand.
    
    Attributes:
        hand_number: Sequential hand ID
        hive_cards: All 6 cards known to HIVE (3 agents * 2)
        dummy_cards: Dummy opponent's hole cards
        board: Community cards (5)
        winner: "hive" or "dummy"
        pot_size: Final pot size (in bb)
        hive_profit: HIVE group's profit/loss (in bb)
        collective_equity: HIVE's calculated equity
        action_count: Number of actions taken
    """
    hand_number: int
    hive_cards: List[str]
    dummy_cards: List[str]
    board: List[str]
    winner: str
    pot_size: float
    hive_profit: float
    collective_equity: float
    action_count: int = 0


@dataclass
class SimulationMetrics:
    """
    Aggregated metrics from HIVE simulation.
    
    Tracks performance across all hands to measure
    coordination effectiveness.
    """
    total_hands: int = 0
    hive_wins: int = 0
    dummy_wins: int = 0
    total_profit: float = 0.0
    total_ev: float = 0.0
    pots_won: List[float] = field(default_factory=list)
    coordination_bonus: float = 0.0
    average_equity: float = 0.0
    
    def winrate(self) -> float:
        """Calculate HIVE win rate."""
        if self.total_hands == 0:
            return 0.0
        return self.hive_wins / self.total_hands
    
    def roi(self) -> float:
        """Calculate ROI (Return on Investment)."""
        if self.total_hands == 0:
            return 0.0
        return (self.total_profit / self.total_hands) * 100
    
    def bb_per_100(self) -> float:
        """Calculate bb/100 hands."""
        if self.total_hands == 0:
            return 0.0
        return (self.total_profit / self.total_hands) * 100


class HiveSimulation:
    """
    Full HIVE 3vs1 simulation engine.
    
    Workflow:
    1. Generate agent pool (100 agents)
    2. Scan lobby for HIVE opportunities
    3. Form HIVE groups (3 agents)
    4. Coordinate join to selected table
    5. Play N hands against dummy opponent
    6. Log metrics and results
    
    Educational Note:
        This simulates the complete HIVE strategy lifecycle,
        demonstrating coordination from table selection through
        gameplay against a baseline opponent.
    """
    
    def __init__(
        self,
        agent_count: int = 100,
        hands_per_session: int = 1000,
        lobby_size: int = 200,
        log_interval: int = 100
    ):
        """
        Initialize HIVE simulation.
        
        Args:
            agent_count: Number of agents in pool
            hands_per_session: Hands to play per table
            lobby_size: Number of tables in virtual lobby
            log_interval: Log progress every N hands
        """
        self.agent_count = agent_count
        self.hands_per_session = hands_per_session
        self.lobby_size = lobby_size
        self.log_interval = log_interval
        
        # Initialize components
        self.agents: List[HiveAgent] = []
        self.lobby: Optional[VirtualLobby] = None
        self.metrics = SimulationMetrics()
        self.decision_engine = CollectiveDecisionEngine()
        
        # Simulation state
        self.current_table: Optional[VirtualTable] = None
        self.hive_group: Optional[HiveGroup] = None
        self.dummy: Optional[DummyOpponent] = None
        self.hand_history: List[HandResult] = []
    
    def setup(self) -> None:
        """Setup simulation: create agents and lobby."""
        logger.info(f"Setting up simulation: {self.agent_count} agents, {self.lobby_size} tables")
        
        # Create agent pool
        for i in range(self.agent_count):
            agent = HiveAgent(
                agent_id=f"agent_{i:03d}"
            )
            self.agents.append(agent)
        
        # Generate virtual lobby (tables created in __init__)
        self.lobby = VirtualLobby(num_tables=self.lobby_size)
        
        logger.info(f"Setup complete: {len(self.agents)} agents, {len(self.lobby.tables)} tables")
    
    def find_and_join_table(self) -> bool:
        """
        Scan lobby for HIVE opportunity and coordinate join.
        
        Returns:
            True if successfully joined table, False otherwise
        """
        if not self.lobby:
            return False
        
        # Select best HIVE opportunity table
        best_table = select_best_hive_table(self.lobby)
        
        if not best_table:
            logger.warning("No suitable table selected")
            return False
        
        logger.info(f"Selected table {best_table.table_id}: "
                   f"humans={best_table.human_count}, seats={best_table.seats_available}")
        
        # Form HIVE group from available agents
        available_agents = [a for a in self.agents if a.current_environment is None]
        
        if len(available_agents) < 3:
            logger.warning("Not enough available agents for HIVE")
            return False
        
        # Create HIVE group with first 3 available agents
        hive_agents = available_agents[:3]
        self.hive_group = HiveGroup(agents=hive_agents)
        
        # Coordinate join
        success = self.hive_group.coordinate_join(best_table)
        
        if success:
            self.current_table = best_table
            logger.info(f"HIVE joined table {best_table.table_id}: "
                       f"{[a.agent_id for a in hive_agents]}")
        else:
            logger.warning("HIVE failed to join table")
            self.hive_group = None
        
        return success
    
    def setup_dummy_opponent(self) -> None:
        """Create dummy opponent for the session."""
        self.dummy = generate_random_opponent()
        logger.info(f"Dummy opponent created: style={self.dummy.style.value}, "
                   f"variance={self.dummy.variance:.2f}, aggression={self.dummy.aggression:.2f}")
    
    def play_hand(self, hand_number: int) -> HandResult:
        """
        Simulate a single poker hand (3 HIVE agents vs 1 dummy).
        
        Args:
            hand_number: Sequential hand ID
            
        Returns:
            HandResult with outcome and metrics
            
        Educational Note:
            Simplified gameplay focusing on collective decision-making.
            Real poker involves complex multi-street dynamics.
        """
        # Generate random cards
        hive_cards = self._generate_hive_cards()
        dummy_cards = self._generate_dummy_cards()
        board = self._generate_board()
        
        # Calculate collective equity
        collective_equity = self._calculate_collective_equity(hive_cards, board)
        
        # HIVE collective decision
        collective_state = CollectiveState(
            collective_cards=hive_cards,
            collective_equity=collective_equity,
            agent_count=3,
            pot_size=100.0,  # Simplified pot
            board=board
        )
        
        hive_decision = self.decision_engine.decide(collective_state)
        
        # Dummy opponent decision
        dummy_strength = estimate_hand_strength(dummy_cards, board)
        dummy_action = self.dummy.decide(
            hand_strength=dummy_strength,
            pot_size=100.0,
            bet_to_call=50.0 if hive_decision.bet_size else 0.0
        )
        
        # Determine winner (simplified)
        hive_strength = collective_equity
        winner = "hive" if hive_strength > dummy_strength else "dummy"
        
        # Calculate pot and profit
        pot_size = 150.0  # Simplified
        hive_profit = pot_size if winner == "hive" else -50.0  # Simplified P&L
        
        return HandResult(
            hand_number=hand_number,
            hive_cards=hive_cards,
            dummy_cards=dummy_cards,
            board=board,
            winner=winner,
            pot_size=pot_size,
            hive_profit=hive_profit,
            collective_equity=collective_equity,
            action_count=2  # Simplified
        )
    
    def play_session(self) -> None:
        """
        Play full session (1000 hands) at current table.
        
        Tracks metrics and logs progress.
        """
        if not self.hive_group or not self.dummy:
            logger.error("Cannot play session: HIVE or dummy not initialized")
            return
        
        logger.info(f"Starting session: {self.hands_per_session} hands")
        start_time = time.time()
        
        for hand_num in range(1, self.hands_per_session + 1):
            # Play hand
            result = self.play_hand(hand_num)
            self.hand_history.append(result)
            
            # Update metrics
            self.metrics.total_hands += 1
            if result.winner == "hive":
                self.metrics.hive_wins += 1
            else:
                self.metrics.dummy_wins += 1
            
            self.metrics.total_profit += result.hive_profit
            self.metrics.total_ev += result.collective_equity * result.pot_size
            self.metrics.pots_won.append(result.pot_size if result.winner == "hive" else 0)
            
            # Log progress
            if hand_num % self.log_interval == 0:
                elapsed = time.time() - start_time
                hands_per_sec = hand_num / elapsed if elapsed > 0 else 0
                logger.info(
                    f"Hand {hand_num}/{self.hands_per_session} - "
                    f"Winrate: {self.metrics.winrate():.1%}, "
                    f"Profit: {self.metrics.total_profit:.1f}bb, "
                    f"Speed: {hands_per_sec:.1f} hands/sec"
                )
        
        # Calculate final metrics
        self._calculate_coordination_bonus()
        
        elapsed_total = time.time() - start_time
        logger.info(f"Session complete in {elapsed_total:.1f}s")
        self._log_final_metrics()
    
    def _generate_hive_cards(self) -> List[str]:
        """Generate 6 hole cards for 3 HIVE agents."""
        # Simplified: random cards
        suits = ['s', 'h', 'd', 'c']
        ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        
        cards = []
        for _ in range(6):
            card = random.choice(ranks) + random.choice(suits)
            cards.append(card)
        
        return cards
    
    def _generate_dummy_cards(self) -> List[str]:
        """Generate 2 hole cards for dummy opponent."""
        suits = ['s', 'h', 'd', 'c']
        ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        
        return [
            random.choice(ranks) + random.choice(suits),
            random.choice(ranks) + random.choice(suits)
        ]
    
    def _generate_board(self) -> List[str]:
        """Generate 5 community cards."""
        suits = ['s', 'h', 'd', 'c']
        ranks = ['A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3', '2']
        
        return [
            random.choice(ranks) + random.choice(suits)
            for _ in range(5)
        ]
    
    def _calculate_collective_equity(self, hive_cards: List[str], board: List[str]) -> float:
        """
        Calculate HIVE's collective equity.
        
        Simplified calculation based on known cards.
        """
        # Base equity from number of known cards
        base = 0.5
        card_bonus = len(hive_cards) * 0.03
        board_bonus = len(board) * 0.02
        
        equity = min(0.95, base + card_bonus + board_bonus)
        
        # Add randomness to simulate variance
        equity += random.uniform(-0.05, 0.10)
        
        return max(0.3, min(0.95, equity))
    
    def _calculate_coordination_bonus(self) -> None:
        """
        Calculate coordination bonus: extra profit from HIVE coordination.
        
        Compares actual profit to expected profit if agents played independently.
        """
        if self.metrics.total_hands == 0:
            return
        
        # Estimate independent play profit (50% winrate, no coordination)
        expected_independent_profit = 0.0  # Break-even baseline
        
        # Coordination bonus is excess profit
        self.metrics.coordination_bonus = self.metrics.total_profit - expected_independent_profit
        
        # Average equity
        equity_sum = sum(h.collective_equity for h in self.hand_history)
        self.metrics.average_equity = equity_sum / len(self.hand_history)
    
    def _log_final_metrics(self) -> None:
        """Log final simulation metrics."""
        logger.info("=" * 60)
        logger.info("FINAL SIMULATION METRICS")
        logger.info("=" * 60)
        logger.info(f"Total Hands: {self.metrics.total_hands}")
        logger.info(f"HIVE Wins: {self.metrics.hive_wins} ({self.metrics.winrate():.1%})")
        logger.info(f"Dummy Wins: {self.metrics.dummy_wins} ({1 - self.metrics.winrate():.1%})")
        logger.info(f"Total Profit: {self.metrics.total_profit:.1f}bb")
        logger.info(f"ROI: {self.metrics.roi():.1f}%")
        logger.info(f"bb/100: {self.metrics.bb_per_100():.2f}")
        logger.info(f"Average Equity: {self.metrics.average_equity:.1%}")
        logger.info(f"Coordination Bonus: {self.metrics.coordination_bonus:.1f}bb")
        logger.info(f"Total EV: {self.metrics.total_ev:.1f}bb")
        logger.info("=" * 60)
    
    def run(self) -> SimulationMetrics:
        """
        Run full HIVE simulation workflow.
        
        Returns:
            SimulationMetrics with final results
            
        Workflow:
        1. Setup agents and lobby
        2. Find and join HIVE opportunity table
        3. Setup dummy opponent
        4. Play session (1000 hands)
        5. Return metrics
        """
        logger.info("Starting HIVE Simulation")
        logger.info("=" * 60)
        
        # Phase 1: Setup
        self.setup()
        
        # Phase 2: Find table
        if not self.find_and_join_table():
            logger.error("Failed to find/join table - aborting simulation")
            return self.metrics
        
        # Phase 3: Setup opponent
        self.setup_dummy_opponent()
        
        # Phase 4: Play session
        self.play_session()
        
        logger.info("HIVE Simulation Complete")
        
        return self.metrics


# Educational Example Usage
if __name__ == "__main__":
    # Run small test simulation
    sim = HiveSimulation(
        agent_count=10,  # Smaller pool for testing
        hands_per_session=100,  # Fewer hands for testing
        lobby_size=50,
        log_interval=25
    )
    
    metrics = sim.run()
    
    print("\n" + "=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)
    print(f"Winrate: {metrics.winrate():.1%}")
    print(f"Total Profit: {metrics.total_profit:.1f}bb")
    print(f"bb/100: {metrics.bb_per_100():.2f}")
    print(f"Coordination Bonus: {metrics.coordination_bonus:.1f}bb")
    print("=" * 60)
