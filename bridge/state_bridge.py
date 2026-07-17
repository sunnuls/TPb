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
        config: Optional[dict] = None,
        hwnd: Optional[int] = None,
        roi_zones: Optional[list] = None,
    ):
        """
        Initialize state bridge.

        Args:
            dry_run:   If True, use simulated data (safe mode)
            config:    Configuration dict (loaded from live_config.yaml)
            hwnd:      CoinPoker window handle for direct capture
            roi_zones: Auto-detected ROI zones (list of dicts)
        """
        self.dry_run = dry_run
        self.config = config or {}
        self._hwnd = hwnd
        self._roi_zones = roi_zones or []
        
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
        
        # Live mode: never invent pot/stacks/cards — fail closed instead
        _fb = bool(dry_run)
        self.card_extractor = CardExtractor(
            dry_run=dry_run,
            fallback_to_simulation=_fb,
        )
        self.numeric_parser = NumericParser(
            dry_run=dry_run,
            fallback_to_simulation=_fb,
        )
        self.metadata_extractor = MetadataExtractor(
            dry_run=dry_run,
            fallback_to_simulation=_fb,
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
        resolution: str = "1920x1080",
        hwnd: Optional[int] = None,
    ) -> Optional[TableState]:
        """
        PRIMARY INTERFACE: Extract complete table state.

        Args:
            table_id:   Unique table identifier
            room:       Poker room name ("pokerstars" or "coinpoker")
            resolution: Screen resolution (for ROI selection)
            hwnd:       Window handle override (takes priority over self._hwnd)

        Returns:
            Complete TableState or None on error.
        """
        start_time = time.time()
        self.extractions_count += 1
        _hwnd = hwnd or self._hwnd

        # Always force dry_run from SafetyFramework — the bridge may have been
        # created before the user switched to UNSAFE mode in Settings.
        try:
            from bridge.safety import SafetyFramework, SafetyMode
            _fw = SafetyFramework.get_instance()
            _live = _fw.config.mode == SafetyMode.UNSAFE
            new_dry = not _live
            if self.dry_run != new_dry:
                logger.info(
                    "StateBridge: dry_run %s → %s (SafetyMode=%s)",
                    self.dry_run, new_dry, _fw.config.mode,
                )
                self.dry_run = new_dry
                # Sync child extractors; live = no simulation fallback
                for attr in ("card_extractor", "numeric_parser", "metadata_extractor"):
                    child = getattr(self, attr, None)
                    if child is None:
                        continue
                    if hasattr(child, "set_dry_run"):
                        child.set_dry_run(new_dry)
                    else:
                        child.dry_run = new_dry
                    if hasattr(child, "fallback_to_simulation"):
                        child.fallback_to_simulation = new_dry
        except Exception:
            pass

        try:
            # Step 1: Capture screenshot
            screenshot, window_info = self._capture_screenshot(hwnd=_hwnd, room=room)

            # Step 2: For PokerStars use dedicated extractor path
            print(f"[STATE_BRIDGE] room={room} dry_run={self.dry_run} shot={'OK' if screenshot is not None else 'None'}")
            if room == "pokerstars" and not self.dry_run and screenshot is not None:
                state = self._extract_ps_state(screenshot, table_id, _hwnd)
                if state is not None:
                    self.last_extraction_time = time.time() - start_time
                    self.last_state = state
                    logger.info(
                        "PS TableState: %s, pot=%.0f (%.3fs)",
                        state.street.value, state.pot,
                        self.last_extraction_time,
                    )
                    return state

            # Step 3: Generic path (DRY-RUN and CoinPoker)
            # Live mode: fail closed if capture failed — never invent pot/stacks
            if not self.dry_run and screenshot is None:
                logger.warning(
                    "StateBridge: no screenshot in LIVE mode — returning None"
                )
                return None

            roi_dict = self._load_rois(room, resolution)
            cards = self._extract_cards(screenshot, roi_dict)
            numeric = self._extract_numeric(screenshot, roi_dict)
            metadata = self._extract_metadata(
                screenshot, roi_dict, len(cards["board"])
            )
            state = self._assemble_table_state(
                table_id=table_id,
                cards=cards,
                numeric=numeric,
                metadata=metadata,
            )

            self.last_extraction_time = time.time() - start_time
            self.last_state = state

            logger.info(
                "TableState extracted: %s, %d players, pot=%.0f (%.3fs)",
                state.street.value, len(state.players), state.pot,
                self.last_extraction_time,
            )
            return state

        except Exception as e:
            logger.error("State extraction failed: %s", e, exc_info=True)
            return None

    def _extract_ps_state(
        self,
        screenshot: np.ndarray,
        table_id: str,
        hwnd: Optional[int],
    ) -> Optional["TableState"]:
        """Extract TableState from a PokerStars table screenshot using pokerstars_extractor."""
        try:
            from bridge.vision.pokerstars_extractor import (
                extract_cards_from_screenshot,
                extract_pot,
                extract_stack,
                is_bots_turn,
                parse_ps_number,
                detect_action_buttons,
                update_button_cache,
            )
            from sim_engine.state.table_state import TableState, PlayerState, Position, Street

            # Load ROI definitions from pokerstars.yaml
            roi_dict = self._load_rois_from_yaml("pokerstars")

            # Cards
            hero_cards = extract_cards_from_screenshot(
                screenshot, roi_dict,
                ["hero_card_1", "hero_card_2"],
            )
            board_cards = extract_cards_from_screenshot(
                screenshot, roi_dict,
                ["board_card_1", "board_card_2", "board_card_3",
                 "board_card_4", "board_card_5"],
            )

            # Numeric
            pot   = extract_pot(screenshot, roi_dict)
            stack = extract_stack(screenshot, roi_dict, "hero_stack")

            # Villain stacks
            villain_stacks = {}
            for i in range(1, 6):
                key = f"villain_{i}_stack"
                v = extract_stack(screenshot, roi_dict, key)
                if v > 0:
                    villain_stacks[f"v{i}"] = v

            # Detect action buttons dynamically (no fixed ROI needed)
            # and update cache so action executor can click them
            buttons = detect_action_buttons(screenshot)
            update_button_cache(buttons)

            # Turn detection: buttons visible = it's our turn
            bot_turn = bool(buttons) or is_bots_turn(screenshot, roi_dict)
            logger.info(
                "PS extract: hero=%s board=%s pot=%.0f turn=%s buttons=%s",
                hero_cards, board_cards, pot, bot_turn, list(buttons.keys()),
            )

            # Determine street from board length
            nb = len(board_cards)
            if nb == 0:
                street = Street.PREFLOP
            elif nb == 3:
                street = Street.FLOP
            elif nb == 4:
                street = Street.TURN
            else:
                street = Street.RIVER

            # Build players
            players = []
            hero = PlayerState(
                player_id="hero",
                position=Position.BTN,
                stack=stack,
                hole_cards=hero_cards,
                is_active=True,
                is_hero=True,
            )
            players.append(hero)
            for pid, stk in villain_stacks.items():
                players.append(PlayerState(
                    player_id=pid,
                    position=Position.BB,
                    stack=stk,
                    is_active=True,
                    is_hero=False,
                ))

            state = TableState(
                table_id=table_id,
                street=street,
                pot=pot,
                board=board_cards,
                players=players,
                is_bots_turn=bot_turn,
            )
            logger.debug(
                "PS state: street=%s hero=%s board=%s pot=%.0f turn=%s",
                street.value, hero_cards, board_cards, pot, bot_turn,
            )
            return state

        except Exception as exc:
            logger.warning("_extract_ps_state failed: %s", exc, exc_info=True)
            # Also print so it's visible in terminal even if HIVE filters bridge.* logs
            import traceback
            print(f"[STATE_BRIDGE] _extract_ps_state EXCEPTION: {exc}")
            traceback.print_exc()
            return None

    def _load_rois_from_yaml(self, room: str) -> Dict[str, Tuple[int, int, int, int]]:
        """Load ROI definitions from config/rooms/<room>.yaml."""
        try:
            import yaml, os
            yaml_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config", "rooms", f"{room}.yaml"
            )
            if not os.path.exists(yaml_path):
                return {}
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            rois_raw = data.get("rois", {})
            result: Dict[str, Tuple[int, int, int, int]] = {}
            for name, vals in rois_raw.items():
                result[name] = (
                    vals.get("x", 0), vals.get("y", 0),
                    vals.get("width", 50), vals.get("height", 30),
                )
            return result
        except Exception as exc:
            logger.debug("_load_rois_from_yaml(%s) error: %s", room, exc)
            return {}

    def _capture_screenshot(
        self,
        hwnd: Optional[int] = None,
        room: str = "pokerstars",
    ) -> Tuple[Optional[np.ndarray], Optional[dict]]:
        """Capture screenshot from poker window.

        For GLFW30/OpenGL windows (modern PokerStars) PrintWindow returns a
        black frame, so we fall back to pyautogui screen capture of the
        window's on-screen region.
        """
        if self.dry_run:
            return None, {'title': f'{room} - Simulated', 'size': (1920, 1080)}

        # Try PrintWindow first (works for non-OpenGL windows).
        # For GLFW30/OpenGL (modern PokerStars) it returns a near-black frame
        # (mean < ~15), so we discard those and fall through to pyautogui.
        if hwnd:
            try:
                import cv2 as _cv2
                img = self.screen_capture.capture_full_window(hwnd=hwnd)
                if img is not None:
                    if hasattr(img, "convert"):
                        img = _cv2.cvtColor(
                            np.array(img.convert("RGB")), _cv2.COLOR_RGB2BGR
                        )
                    h, w = img.shape[:2]
                    mean_val = float(np.mean(img))
                    logger.info(
                        "Table capture (PrintWindow): %dx%d mean=%.1f",
                        w, h, mean_val,
                    )
                    if mean_val > 15.0:  # actual content; not OpenGL black frame
                        return img, {"hwnd": hwnd, "title": "captured_via_hwnd",
                                     "size": (w, h)}
                    logger.info(
                        "PrintWindow image too dark (mean=%.1f) — "
                        "OpenGL window detected, switching to pyautogui", mean_val
                    )
            except Exception as exc:
                logger.info("PrintWindow capture failed: %s — trying pyautogui", exc)

        # Fallback: pyautogui screenshot of the window's on-screen region.
        # This is required for GLFW30/OpenGL windows where PrintWindow returns
        # a solid-black frame.
        if hwnd:
            try:
                import win32gui
                import pyautogui
                import cv2 as _cv2

                rect = win32gui.GetWindowRect(hwnd)
                wx, wy, wx2, wy2 = rect
                ww, wh = wx2 - wx, wy2 - wy
                if ww > 100 and wh > 100:
                    # Bring window to front so pyautogui captures real pixels
                    try:
                        import win32con
                        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                        win32gui.SetForegroundWindow(hwnd)
                    except Exception:
                        pass

                    pil_img = pyautogui.screenshot(region=(wx, wy, ww, wh))
                    img = _cv2.cvtColor(np.array(pil_img), _cv2.COLOR_RGB2BGR)
                    mean_val = float(np.mean(img))
                    logger.info(
                        "Table capture (pyautogui): %dx%d at (%d,%d) mean=%.1f",
                        ww, wh, wx, wy, mean_val,
                    )
                    if mean_val > 5.0:  # non-blank
                        return img, {"hwnd": hwnd,
                                     "title": "captured_via_pyautogui",
                                     "size": (ww, wh)}
                    logger.warning(
                        "Table capture: pyautogui image blank (mean=%.1f) "
                        "— window may be hidden", mean_val
                    )
            except Exception as exc:
                logger.warning("pyautogui capture failed: %s", exc)

        # Last resort: window title search (ScreenCapture uses its own pattern from init)
        try:
            window_info = self.screen_capture.find_window()
        except Exception:
            window_info = None
        if not window_info:
            logger.debug("Poker window not found via screen_capture.find_window()")
            return None, None

        screenshot = self.screen_capture.capture_screenshot(window_info=window_info)
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
    
    def _roi_zones_to_dict(
        self, roi_zones: list, img_shape: tuple
    ) -> Dict[str, Tuple[int, int, int, int]]:
        """Convert auto-ROI zone list to the {name: (x,y,w,h)} dict expected by extractors."""
        result: Dict[str, Tuple[int, int, int, int]] = {}
        for z in roi_zones:
            if isinstance(z, dict):
                name = z.get("name", "")
                x, y = z.get("x", 0), z.get("y", 0)
                w, h = z.get("w", 50), z.get("h", 25)
            else:
                name = getattr(z, "name", "")
                x, y = getattr(z, "x", 0), getattr(z, "y", 0)
                w, h = getattr(z, "w", 50), getattr(z, "h", 25)
            if name:
                result[name] = (x, y, w, h)
        # Provide minimal defaults if missing
        h_img = img_shape[0] if len(img_shape) > 0 else 1080
        w_img = img_shape[1] if len(img_shape) > 1 else 1920
        result.setdefault("hero_cards", (int(w_img * 0.38), int(h_img * 0.80), 200, 60))
        result.setdefault("board",      (int(w_img * 0.28), int(h_img * 0.45), 440, 80))
        result.setdefault("pot",        (int(w_img * 0.42), int(h_img * 0.40), 140, 35))
        result.setdefault("fold_button",  (int(w_img * 0.25), int(h_img * 0.88), 130, 42))
        result.setdefault("call_button",  (int(w_img * 0.43), int(h_img * 0.88), 130, 42))
        result.setdefault("raise_button", (int(w_img * 0.61), int(h_img * 0.88), 130, 42))
        return result

    def _is_bots_turn(
        self, img: "np.ndarray", roi_dict: Dict[str, Tuple[int, int, int, int]]
    ) -> bool:
        """Detect whether fold/call/raise buttons are visible (HSV green check).

        Returns True when at least the "fold" button region contains a
        significant green-hued area (indicating active action buttons).
        """
        try:
            import cv2
            import numpy as np

            fold_roi = roi_dict.get("fold_button")
            if fold_roi is None:
                return False
            x, y, w, h = fold_roi
            region = img[y: y + h, x: x + w]
            if region.size == 0:
                return False

            hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
            # Green hue range (CoinPoker action buttons are typically green)
            lo = np.array([35,  60,  60])
            hi = np.array([85, 255, 255])
            mask = cv2.inRange(hsv, lo, hi)
            green_ratio = np.count_nonzero(mask) / mask.size
            return green_ratio > 0.10  # > 10 % green pixels in the fold zone
        except Exception:
            return False

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
