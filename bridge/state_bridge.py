"""
State Bridge Module (Roadmap3 Phase 2.4).

Main orchestration module that combines all vision extractors
to produce a complete TableState compatible with:
- sim_engine/collective_decision.py
- sim_engine/central_hub.py

This is the primary interface for bridge mode:
    get_live_table_state() -> TableState

EDUCATIONAL USE ONLY: For HCI research prototype.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

import numpy as np

from bridge.screen_capture import ScreenCapture
from bridge.roi_manager import ROIManager
from bridge.vision.card_extractor import CardExtractor
from bridge.vision.numeric_parser import NumericParser
from bridge.vision.metadata import MetadataExtractor
from sim_engine.state.table_state import TableState, PlayerState, Position, Street

logger = logging.getLogger(__name__)


class StateBridge:
    """
    State Bridge - Orchestrates all vision extractors.
    
    Main workflow:
    1. Capture screenshot (from ScreenCapture)
    2. Load ROIs (from ROIManager)
    3. Extract cards (CardExtractor)
    4. Extract numeric data (NumericParser)
    5. Extract metadata (MetadataExtractor)
    6. Assemble complete TableState
    
    In DRY-RUN mode (default):
        All extractors return simulated data -> produces complete test TableState
    
    In UNSAFE mode:
        Real vision extraction -> produces live TableState
    
    EDUCATIONAL NOTE:
        This demonstrates complete state extraction pipeline for
        HCI research studying external poker applications.
    """
    
    def __init__(
        self,
        dry_run: bool = True,
        config: Optional[dict] = None
    ):
        """
        Initialize state bridge.
        
        Args:
            dry_run: If True, use simulated data (safe mode)
            config: Configuration dict (loaded from live_config.yaml)
        """
        self.dry_run = dry_run
        self.config = config or {}
        
        # Initialize all components
        # ScreenCapture doesn't take dry_run - uses SafetyFramework instead
        screen_config = self.config.get('screen_capture', {})
        self.screen_capture = ScreenCapture(
            window_title_pattern=screen_config.get('window_title_pattern'),
            process_name=screen_config.get('process_name'),
            save_screenshots=screen_config.get('save_screenshots', False),
            screenshot_dir=screen_config.get('screenshot_dir', 'bridge/debug_screenshots')
        )
        
        self.roi_manager = ROIManager()
        
        self.card_extractor = CardExtractor(
            dry_run=dry_run,
            fallback_to_simulation=True
        )
        
        self.numeric_parser = NumericParser(
            dry_run=dry_run,
            fallback_to_simulation=True
        )
        
        self.metadata_extractor = MetadataExtractor(
            dry_run=dry_run,
            fallback_to_simulation=True
        )
        
        # Statistics
        self.extractions_count = 0
        self.last_extraction_time = 0.0
        self.last_state: Optional[TableState] = None
        
        logger.info(
            f"StateBridge initialized (dry_run={dry_run})"
        )
    
    def get_live_table_state(
        self,
        table_id: str = "live_table_001",
        room: str = "pokerstars",
        resolution: str = "1920x1080"
    ) -> Optional[TableState]:
        """
        PRIMARY INTERFACE: Extract complete table state.
        
        This is the main entry point for bridge mode integration.
        
        Args:
            table_id: Unique table identifier
            room: Poker room name (for ROI selection)
            resolution: Screen resolution (for ROI selection)
        
        Returns:
            Complete TableState or None on error
        
        EDUCATIONAL NOTE:
            In DRY-RUN mode, returns realistic simulated TableState.
            In UNSAFE mode, performs real vision extraction.
        
        Usage:
            bridge = StateBridge(dry_run=True)
            state = bridge.get_live_table_state()
            
            # Use with collective decision engine
            collective_state = state.to_collective_state()
            decision = decision_engine.decide(collective_state, legal_actions)
        """
        start_time = time.time()
        self.extractions_count += 1
        
        try:
            # Step 1: Capture screenshot
            screenshot, window_info = self._capture_screenshot()
            
            # Step 2: Load ROIs
            roi_dict = self._load_rois(room, resolution)
            
            # Step 3: Extract all data
            cards = self._extract_cards(screenshot, roi_dict)
            numeric = self._extract_numeric(screenshot, roi_dict)
            metadata = self._extract_metadata(
                screenshot, roi_dict, len(cards['board'])
            )
            
            # Step 4: Assemble TableState
            state = self._assemble_table_state(
                table_id=table_id,
                cards=cards,
                numeric=numeric,
                metadata=metadata
            )
            
            # Update statistics
            self.last_extraction_time = time.time() - start_time
            self.last_state = state
            
            logger.info(
                f"TableState extracted: {state.street.value}, "
                f"{len(state.players)} players, pot={state.pot} bb "
                f"(extraction_time={self.last_extraction_time:.3f}s)"
            )
            
            return state
            
        except Exception as e:
            logger.error(f"State extraction failed: {e}", exc_info=True)
            return None
    
    def _capture_screenshot(self) -> Tuple[Optional[np.ndarray], Optional[dict]]:
        """
        Capture screenshot from poker window.
        
        Returns:
            (screenshot array, window info dict)
        """
        if self.dry_run:
            # Simulated screenshot
            return None, {'title': 'PokerStars - Simulated', 'size': (1920, 1080)}
        
        # Real capture
        window_info = self.screen_capture.find_window(
            title_pattern="PokerStars"
        )
        
        if not window_info:
            logger.warning("Poker window not found")
            return None, None
        
        screenshot = self.screen_capture.capture_screenshot(
            window_info=window_info
        )
        
        return screenshot, window_info
    
    def _load_rois(
        self,
        room: str,
        resolution: str
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """
        Load ROIs for specific room and resolution.
        
        Args:
            room: Poker room name
            resolution: Screen resolution
        
        Returns:
            Dictionary of ROIs {name: (x, y, w, h)}
        """
        # Load ROI set (returns bool indicating success)
        success = self.roi_manager.load_roi_set(room, resolution)
        
        if not success:
            logger.warning(
                f"No ROIs found for {room}@{resolution} - using defaults"
            )
            # Return minimal default ROIs
            return {
                'hero_cards': (100, 100, 200, 50),
                'board': (500, 300, 400, 80),
                'pot': (600, 200, 100, 40)
            }
        
        # Get all loaded ROIs (returns dict {name: ROI})
        rois_dict = self.roi_manager.get_all_rois()
        return {name: (roi.x, roi.y, roi.width, roi.height) 
                for name, roi in rois_dict.items()}
    
    def _extract_cards(
        self,
        screenshot: Optional[np.ndarray],
        roi_dict: Dict[str, Tuple[int, int, int, int]]
    ) -> Dict[str, list]:
        """
        Extract all cards (hero + board).
        
        Args:
            screenshot: Screenshot array
            roi_dict: Dictionary of ROIs
        
        Returns:
            Dictionary with 'hero' and 'board' card lists
        """
        # Extract hero cards
        hero_roi = roi_dict.get('hero_cards')
        hero_detection = self.card_extractor.extract_hero_cards(
            screenshot, hero_roi
        )
        
        # Extract board cards
        board_roi = roi_dict.get('board')
        board_detection = self.card_extractor.extract_board_cards(
            screenshot, board_roi
        )
        
        return {
            'hero': hero_detection.cards,
            'board': board_detection.cards
        }
    
    def _extract_numeric(
        self,
        screenshot: Optional[np.ndarray],
        roi_dict: Dict[str, Tuple[int, int, int, int]]
    ) -> dict:
        """
        Extract all numeric data.
        
        Args:
            screenshot: Screenshot array
            roi_dict: Dictionary of ROIs
        
        Returns:
            NumericData result
        """
        numeric_data = self.numeric_parser.extract_all(
            screenshot, roi_dict
        )
        
        return {
            'pot': numeric_data.pot,
            'stacks': numeric_data.stacks,
            'bets': numeric_data.bets,
            'positions': numeric_data.positions
        }
    
    def _extract_metadata(
        self,
        screenshot: Optional[np.ndarray],
        roi_dict: Dict[str, Tuple[int, int, int, int]],
        board_card_count: int
    ) -> dict:
        """
        Extract metadata.
        
        Args:
            screenshot: Screenshot array
            roi_dict: Dictionary of ROIs
            board_card_count: Number of board cards (for street detection)
        
        Returns:
            TableMetadata result
        """
        metadata = self.metadata_extractor.extract_all(
            screenshot,
            board_card_count=board_card_count,
            roi_dict=roi_dict
        )
        
        return {
            'street': metadata.street,
            'table_type': metadata.table_type,
            'max_seats': metadata.max_seats,
            'active_seats': metadata.active_seats,
            'hand_number': metadata.hand_number
        }
    
    def _assemble_table_state(
        self,
        table_id: str,
        cards: dict,
        numeric: dict,
        metadata: dict
    ) -> TableState:
        """
        Assemble complete TableState from extracted data.
        
        Args:
            table_id: Table identifier
            cards: Extracted cards {'hero': [...], 'board': [...]}
            numeric: Extracted numeric data
            metadata: Extracted metadata
        
        Returns:
            Complete TableState
        
        EDUCATIONAL NOTE:
            This is where all vision components are unified into
            a single state representation compatible with decision engines.
        """
        # Build player states
        players = {}
        
        # Hero player
        hero = PlayerState(
            player_id="hero",
            position=self._map_position(numeric['positions'].get('hero', 'BTN')),
            stack=numeric['stacks'].get('hero', 1000.0),
            current_bet=numeric['bets'].get('hero', 0.0),
            is_hero=True,
            is_active=True,
            hole_cards=cards['hero']
        )
        players['hero'] = hero
        
        # Opponent players
        for player_id, stack in numeric['stacks'].items():
            if player_id == 'hero':
                continue
            
            opponent = PlayerState(
                player_id=player_id,
                position=self._map_position(numeric['positions'].get(player_id, 'UNKNOWN')),
                stack=stack,
                current_bet=numeric['bets'].get(player_id, 0.0),
                is_hero=False,
                is_active=True,
                hole_cards=[]  # Opponent cards unknown
            )
            players[player_id] = opponent
        
        # Determine current bet and min raise
        all_bets = list(numeric['bets'].values())
        current_bet = max(all_bets) if all_bets else 0.0
        min_raise = current_bet * 2  # Simplified
        
        # Build TableState
        state = TableState(
            table_id=table_id,
            table_type=metadata['table_type'].value,
            max_seats=metadata['max_seats'],
            street=metadata['street'],
            board=cards['board'],
            pot=numeric['pot'],
            players=players,
            hero_id='hero',
            current_bet=current_bet,
            min_raise=min_raise,
            hand_number=metadata['hand_number'],
            timestamp=time.time(),
            extraction_method="simulated" if self.dry_run else "vision",
            confidence=1.0 if self.dry_run else 0.85
        )
        
        return state
    
    def _map_position(self, position_str: str) -> Position:
        """
        Map position string to Position enum.
        
        Args:
            position_str: Position string (BTN, SB, BB, etc)
        
        Returns:
            Position enum value
        """
        position_map = {
            'BTN': Position.BTN,
            'SB': Position.SB,
            'BB': Position.BB,
            'UTG': Position.UTG,
            'MP': Position.MP,
            'CO': Position.CO
        }
        
        return position_map.get(position_str.upper(), Position.UNKNOWN)
    
    def get_statistics(self) -> dict:
        """Get state bridge statistics."""
        card_stats = self.card_extractor.get_statistics()
        numeric_stats = self.numeric_parser.get_statistics()
        metadata_stats = self.metadata_extractor.get_statistics()
        
        return {
            'total_extractions': self.extractions_count,
            'last_extraction_time': self.last_extraction_time,
            'dry_run': self.dry_run,
            'components': {
                'cards': card_stats,
                'numeric': numeric_stats,
                'metadata': metadata_stats
            }
        }


# Educational example usage
if __name__ == "__main__":
    print("=" * 60)
    print("State Bridge - Educational HCI Research Demo")
    print("=" * 60)
    print()
    
    # Initialize bridge in DRY-RUN mode (safe)
    bridge = StateBridge(dry_run=True)
    
    # Extract complete table state
    print("Extracting table state...")
    state = bridge.get_live_table_state(
        table_id="demo_table",
        room="pokerstars_6max",
        resolution="1920x1080"
    )
    
    if state:
        print()
        print("=" * 60)
        print("Extracted Table State:")
        print("=" * 60)
        print()
        
        print(f"Table ID: {state.table_id}")
        print(f"Street: {state.street.value}")
        print(f"Pot: {state.pot} bb")
        print(f"Board: {state.board}")
        print()
        
        print("Players:")
        for pid, player in state.players.items():
            indicator = "[HERO]" if player.is_hero else "[OPP] "
            print(
                f"  {indicator} {pid} ({player.position.value}): "
                f"{player.stack} bb (bet: {player.current_bet} bb)"
            )
            if player.hole_cards:
                print(f"     Cards: {player.hole_cards}")
        print()
        
        print(f"Active players: {len(state.get_active_players())}")
        print(f"Opponents: {state.get_opponent_count()}")
        print(f"Hero cards: {state.get_hero_cards()}")
        print()
        
        # Test conversion to CollectiveState
        print("Converting to CollectiveState...")
        collective = state.to_collective_state()
        print(f"[OK] Collective cards: {collective.collective_cards}")
        print(f"[OK] Collective equity: {collective.collective_equity:.1%}")
        print(f"[OK] Pot size: {collective.pot_size} bb")
        print()
        
        # Statistics
        stats = bridge.get_statistics()
        print("=" * 60)
        print("Statistics:")
        print("=" * 60)
        print(f"Total extractions: {stats['total_extractions']}")
        print(f"Last extraction time: {stats['last_extraction_time']:.3f}s")
        print(f"DRY-RUN mode: {stats['dry_run']}")
        print()
    else:
        print("❌ State extraction failed")
    
    print("=" * 60)
    print("Educational HCI Research - DRY-RUN mode")
    print("=" * 60)
