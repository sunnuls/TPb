"""
Table State Module for Bridge & Simulation (Roadmap3 Phase 2).

Unified state representation compatible with:
- bridge/state_bridge.py (Phase 2)
- sim_engine/collective_decision.py (Phase 2 integration)
- sim_engine/central_hub.py (coordination)

EDUCATIONAL USE ONLY: For HCI research and multi-agent simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Street(str, Enum):
    """Poker street/stage."""
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class Position(str, Enum):
    """Player positions at poker table."""
    BTN = "button"
    SB = "small_blind"
    BB = "big_blind"
    UTG = "utg"
    MP = "middle_position"
    CO = "cutoff"
    UNKNOWN = "unknown"


@dataclass
class PlayerState:
    """
    State of a single player at the table.
    
    Attributes:
        player_id: Unique identifier
        position: Table position
        stack: Current stack size (in bb)
        current_bet: Current bet in this round
        is_hero: Whether this is the hero player
        is_active: Whether player is in the hand
        hole_cards: Known hole cards (if hero or shared)
    """
    player_id: str
    position: Position = Position.UNKNOWN
    stack: float = 0.0
    current_bet: float = 0.0
    is_hero: bool = False
    is_active: bool = True
    hole_cards: List[str] = field(default_factory=list)


@dataclass
class TableState:
    """
    Complete table state for poker simulation and bridge.
    
    This unified state format is compatible with:
    - Bridge state extraction (Phase 2)
    - Collective decision engine
    - Central hub coordination
    
    EDUCATIONAL NOTE:
        This state representation enables seamless integration between
        live bridge and simulation components for HCI research.
    """
    # Basic table info
    table_id: str
    table_type: str = "cash"  # cash | tournament
    max_seats: int = 6
    
    # Current hand state
    street: Street = Street.PREFLOP
    board: List[str] = field(default_factory=list)
    pot: float = 0.0
    
    # Players
    players: Dict[str, PlayerState] = field(default_factory=dict)
    hero_id: Optional[str] = None
    
    # Action info
    current_bet: float = 0.0
    min_raise: float = 0.0
    
    # Metadata
    hand_number: int = 0
    timestamp: float = 0.0
    
    # Bridge-specific (Phase 2)
    extraction_method: str = "simulated"  # simulated | ocr | vision
    confidence: float = 1.0  # Extraction confidence (0.0-1.0)
    
    def get_hero(self) -> Optional[PlayerState]:
        """Get hero player state."""
        if self.hero_id and self.hero_id in self.players:
            return self.players[self.hero_id]
        return None
    
    def get_hero_cards(self) -> List[str]:
        """Get hero's hole cards."""
        hero = self.get_hero()
        return hero.hole_cards if hero else []
    
    def get_active_players(self) -> List[PlayerState]:
        """Get all active players in the hand."""
        return [p for p in self.players.values() if p.is_active]
    
    def get_opponent_count(self) -> int:
        """Get number of active opponents."""
        active = self.get_active_players()
        hero = self.get_hero()
        
        if hero and hero.is_active:
            return len(active) - 1
        return len(active)
    
    def to_collective_state(self) -> 'CollectiveState':
        """
        Convert to CollectiveState for decision engine.
        
        Returns:
            CollectiveState compatible with collective_decision module
            
        EDUCATIONAL NOTE:
            Enables bridge to use existing collective decision logic.
        """
        from sim_engine.collective_decision import CollectiveState
        
        # Collect all known cards (hero + any shared cards)
        collective_cards = self.get_hero_cards()
        
        # Build stack sizes dict
        stack_sizes = {
            pid: player.stack
            for pid, player in self.players.items()
        }
        
        # Calculate collective equity (placeholder - will be refined)
        # For now, use simplified heuristic
        collective_equity = 0.5  # Default 50%
        
        return CollectiveState(
            collective_cards=collective_cards,
            collective_equity=collective_equity,
            agent_count=1,  # Single agent by default (HIVE mode sets this higher)
            pot_size=self.pot,
            stack_sizes=stack_sizes,
            board=self.board,
            dummy_range="unknown"
        )
    
    def as_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'table_id': self.table_id,
            'table_type': self.table_type,
            'max_seats': self.max_seats,
            'street': self.street.value,
            'board': self.board,
            'pot': self.pot,
            'players': {
                pid: {
                    'player_id': p.player_id,
                    'position': p.position.value,
                    'stack': p.stack,
                    'current_bet': p.current_bet,
                    'is_hero': p.is_hero,
                    'is_active': p.is_active,
                    'hole_cards': p.hole_cards
                }
                for pid, p in self.players.items()
            },
            'hero_id': self.hero_id,
            'current_bet': self.current_bet,
            'min_raise': self.min_raise,
            'hand_number': self.hand_number,
            'timestamp': self.timestamp,
            'extraction_method': self.extraction_method,
            'confidence': self.confidence
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("Table State - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Create sample table state
    hero = PlayerState(
        player_id="hero",
        position=Position.BTN,
        stack=1000.0,
        is_hero=True,
        hole_cards=["As", "Kh"]
    )
    
    villain = PlayerState(
        player_id="villain1",
        position=Position.BB,
        stack=950.0,
        current_bet=10.0
    )
    
    state = TableState(
        table_id="table_001",
        table_type="cash",
        max_seats=6,
        street=Street.PREFLOP,
        pot=15.0,
        players={"hero": hero, "villain1": villain},
        hero_id="hero",
        current_bet=10.0,
        extraction_method="simulated"
    )
    
    # Display state
    print(f"Table: {state.table_id}")
    print(f"Street: {state.street.value}")
    print(f"Pot: {state.pot} bb")
    print(f"Board: {state.board}")
    print()
    
    print(f"Hero cards: {state.get_hero_cards()}")
    print(f"Active players: {len(state.get_active_players())}")
    print(f"Opponents: {state.get_opponent_count()}")
    print()
    
    # Convert to CollectiveState
    collective = state.to_collective_state()
    print(f"Collective cards: {collective.collective_cards}")
    print(f"Collective equity: {collective.collective_equity:.1%}")
    print()
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
