from __future__ import annotations

import argparse
import json
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

import numpy as np
import yaml
from PIL import Image

from coach_app.adapters.vision.live_adapter import LiveVisionAdapter
from coach_app.coach.explain import explain_from_key_facts
from coach_app.engine.poker.analyze import analyze_poker_state
from coach_app.ingest.vision.fusion import merge_partial_state
from coach_app.product.mode import ProductMode
from coach_app.schemas.ingest import ParseReport
from coach_app.schemas.meta import Meta
from coach_app.schemas.poker import PokerGameState
from coach_app.state.validate import StateValidationError, validate_poker_state

OutputMode = Literal["console", "overlay", "telegram"]


@dataclass
class LiveRTAConfig:
    region: dict[str, int] | None
    fps: float
    ui_change: dict[str, Any]
    post_action_change: dict[str, Any]
    meta: dict[str, Any]
    telegram: dict[str, Any]
    tables: dict[str, Any]


def _stable_json_hash(obj: Any) -> str:
    b = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    import hashlib

    return hashlib.sha256(b).hexdigest()


def _roi_change_score(prev: np.ndarray, curr: np.ndarray) -> float:
    if prev.shape != curr.shape:
        return float("inf")
    # absdiff on grayscale
    try:
        import cv2

        d = cv2.absdiff(prev, curr)
        return float(np.mean(d))
    except Exception:
        a = prev.astype(np.int16)
        b = curr.astype(np.int16)
        return float(np.mean(np.abs(a - b)))


class _OverlaySink:
    def __init__(self) -> None:
        self._app = None
        self._QtCore = None
        self._QtWidgets = None
        self._windows: dict[str, Any] = {}
        self._window_cls: Any = None

    def ensure_started(self) -> None:
        if self._app is not None:
            return
        try:
            from PyQt5 import QtCore, QtWidgets
        except Exception as e:  # pragma: no cover
            raise RuntimeError("PyQt5 не установлен. Установите extra [live].") from e

        class OverlayWindow(QtWidgets.QWidget):
            def __init__(self):
                super().__init__()
                self.setWindowFlags(
                    QtCore.Qt.WindowStaysOnTopHint
                    | QtCore.Qt.FramelessWindowHint
                    | QtCore.Qt.Tool
                    | QtCore.Qt.WindowTransparentForInput
                )
                self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
                self.setGeometry(50, 50, 520, 260)

                self.label = QtWidgets.QLabel(self)
                self.label.setGeometry(10, 10, 500, 240)
                self.label.setStyleSheet(
                    "color: white; background-color: rgba(0,0,0,160); padding: 10px; font-size: 13px;"
                )
                self.label.setWordWrap(True)

            def set_text(self, text: str) -> None:
                self.label.setText(text)

        self._QtCore = QtCore
        self._QtWidgets = QtWidgets
        self._window_cls = OverlayWindow
        self._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        w = OverlayWindow()
        w.show()
        self._windows["default"] = w

    def show(self, text: str, *, table_id: str = "default", anchor_rect: tuple[int, int, int, int] | None = None) -> None:
        self.ensure_started()
        assert self._app is not None
        if table_id not in self._windows:
            assert self._window_cls is not None
            w = self._window_cls()
            w.show()
            self._windows[table_id] = w

        w = self._windows[table_id]
        if anchor_rect is not None:
            x, y, w0, h0 = anchor_rect
            ow, oh = 520, 260
            nx = int(x + 10)
            ny = int(max(0, y - oh - 10))
            if ny < 10:
                ny = int(y + 10)
            w.setGeometry(nx, ny, ow, oh)
        w.set_text(text)
        # process events to repaint
        self._app.processEvents()  # pragma: no cover


class _TelegramSink:
    def __init__(self, *, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._bot = None

    def ensure_started(self) -> None:
        if self._bot is not None:
            return
        try:
            from telegram import Bot
        except Exception as e:  # pragma: no cover
            raise RuntimeError("python-telegram-bot не установлен. Установите extra [telegram].") from e
        self._bot = Bot(token=self.bot_token)

    def send(self, text: str) -> None:
        self.ensure_started()
        assert self._bot is not None
        # fire-and-forget
        self._bot.send_message(chat_id=self.chat_id, text=text)


class LiveRTA:
    def __init__(
        self,
        config_path: str | Path,
        *,
        output_mode: OutputMode = "console",
        ethical_mode: bool = True,
    ) -> None:
        self.config_path = Path(config_path)
        self.output_mode: OutputMode = output_mode
        self.ethical_mode = bool(ethical_mode)

        data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}

        # Support two formats:
        # 1) Adapter YAML (has 'rois') -> treat as vision adapter config
        # 2) RTA YAML -> points to adapter config and adds runtime settings
        is_adapter_cfg = isinstance(data, dict) and ("rois" in data or "anchors" in data)

        if is_adapter_cfg:
            rta_cfg_obj: dict[str, Any] = {}
            adapter_cfg = str(self.config_path)
        else:
            rta_cfg_obj = dict(data)
            adapter_cfg = (
                rta_cfg_obj.get("vision_adapter_config")
                or rta_cfg_obj.get("adapter_config")
                or rta_cfg_obj.get("vision_config")
                or "coach_app/configs/adapters/pokerstars_live.yaml"
            )

        self.cfg = LiveRTAConfig(
            region=rta_cfg_obj.get("region"),
            fps=float(rta_cfg_obj.get("fps", 1.0)),
            ui_change=dict(rta_cfg_obj.get("ui_change", {}) or {}),
            post_action_change=dict(rta_cfg_obj.get("post_action_change", {}) or {}),
            meta=dict(rta_cfg_obj.get("meta", {}) or {}),
            telegram=dict(rta_cfg_obj.get("telegram", {}) or {}),
            tables=dict(rta_cfg_obj.get("tables", {}) or {}),
        )

        self.vision = LiveVisionAdapter(config_path=str(adapter_cfg))

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

        self._tables_state: dict[str, dict[str, Any]] = {}

        self._overlay: _OverlaySink | None = None
        self._telegram: _TelegramSink | None = None

        self._force_next_analysis = threading.Event()

        self.session_id = uuid.uuid4().hex

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def join(self) -> None:
        if self._thread is None:
            return
        self._thread.join()

    def trigger_post_action(self, *, trigger: str = "hotkey") -> None:
        self._force_next_analysis.set()
        for _, st in self._tables_state.items():
            st["pending_trigger"] = trigger if trigger in ("ui_change", "hotkey", "hand_complete", "unknown") else "unknown"
            st["pending_post_action"] = True

    def _get_overlay(self) -> _OverlaySink:
        if self._overlay is None:
            self._overlay = _OverlaySink()
        return self._overlay

    def _get_telegram(self) -> _TelegramSink:
        if self._telegram is None:
            tcfg = self.cfg.telegram
            bot_token = str(tcfg.get("bot_token") or "")
            chat_id = str(tcfg.get("chat_id") or "")
            if not bot_token or not chat_id:
                raise RuntimeError("telegram.enabled=true, но не задан bot_token/chat_id")
            self._telegram = _TelegramSink(bot_token=bot_token, chat_id=chat_id)

    def _output(self, text: str) -> None:
        if self.output_mode == "console":
            print(text)
            return
        if self.output_mode == "overlay":
            self._get_overlay().show(text)
            return
        if self.output_mode == "telegram":
            self._get_telegram().send(text)
            return
        raise ValueError("Unknown output_mode")

    def _detect_table_regions(self) -> list[tuple[str, dict[str, int], tuple[int, int, int, int] | None]]:
        if self.cfg.region is not None:
            r = self.cfg.region
            x = int(r.get("left", r.get("x", 0)))
            y = int(r.get("top", r.get("y", 0)))
            w = int(r.get("width", r.get("w", 0)))
            h = int(r.get("height", r.get("h", 0)))
            return [("default", {"left": x, "top": y, "width": w, "height": h}, (x, y, w, h))]

        tcfg = self.cfg.tables
        if not bool(tcfg.get("enabled", False)):
            return [("default", None, None)]  # type: ignore[list-item]

        title_regex = tcfg.get("title_regex")
        if not isinstance(title_regex, str) or not title_regex.strip():
            title_regex = None

        try:
            import re

            import pygetwindow as gw  # type: ignore[import-not-found]
        except Exception:
            return [("default", None, None)]  # type: ignore[list-item]

        out: list[tuple[str, dict[str, int], tuple[int, int, int, int]]] = []
        for w in gw.getAllWindows():
            try:
                if not w.title:
                    continue
                if title_regex is not None and re.search(title_regex, w.title) is None:
                    continue
                if int(getattr(w, "width", 0)) <= 0 or int(getattr(w, "height", 0)) <= 0:
                    continue
                left = int(getattr(w, "left"))
                top = int(getattr(w, "top"))
                width = int(getattr(w, "width"))
                height = int(getattr(w, "height"))
                if width < 200 or height < 200:
                    continue
                table_id = f"win_{abs(hash((w.title, left, top, width, height))) % 10**12}"
                out.append(
                    (
                        table_id,
                        {"left": left, "top": top, "width": width, "height": height},
                        (left, top, width, height),
                    )
                )
            except Exception:
                continue
        if out:
            return out
        return [("default", None, None)]  # type: ignore[list-item]

    def _loop(self) -> None:
        def hotkey_thread() -> None:
            try:
                import keyboard  # type: ignore[import-not-found]
            except Exception:
                return

            keyboard.add_hotkey("space", lambda: self._force_next_analysis.set())
            keyboard.add_hotkey("esc", lambda: self.stop())
            while not self._stop.is_set():
                time.sleep(0.05)
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass

        threading.Thread(target=hotkey_thread, daemon=True).start()

        frame_interval = 1.0 / max(0.1, float(self.cfg.fps))

        ui_enabled = bool(self.cfg.ui_change.get("enabled", False))
        ui_roi = self.cfg.ui_change.get("roi")
        ui_threshold = float(self.cfg.ui_change.get("threshold", 20.0))

        prev_ui_roi_gray: dict[str, np.ndarray | None] = {}

        post_enabled = bool(self.cfg.post_action_change.get("enabled", self.ethical_mode))
        post_roi = self.cfg.post_action_change.get("roi")
        post_threshold = float(self.cfg.post_action_change.get("threshold", 18.0))
        prev_post_gray: dict[str, np.ndarray | None] = {}

        while not self._stop.is_set():
            tables = self._detect_table_regions()

            if self._force_next_analysis.is_set():
                self._force_next_analysis.clear()
                for _, st in self._tables_state.items():
                    st["pending_trigger"] = "hotkey"
                    st["pending_post_action"] = True

            for table_id, region, anchor_rect in tables:
                if table_id not in self._tables_state:
                    self._tables_state[table_id] = {
                        "last_state_hash": None,
                        "last_global_conf": 0.0,
                        "pending_post_action": False,
                        "pending_trigger": "unknown",
                        "last_status": None,
                    }
                st = self._tables_state[table_id]

                pil_img = self.vision.capture_screen(region=region)
                np_img = np.asarray(pil_img)

                if self.ethical_mode and post_enabled:
                    if isinstance(post_roi, list) and len(post_roi) == 4:
                        x, y, w, h = [int(v) for v in post_roi]
                        area = np_img[y : y + h, x : x + w]
                    else:
                        area = np_img

                    if area.size > 0:
                        try:
                            import cv2

                            gray = cv2.cvtColor(area, cv2.COLOR_RGB2GRAY) if area.ndim == 3 else area
                            gray = cv2.resize(gray, (160, 90))
                        except Exception:
                            gray = area.mean(axis=2).astype(np.uint8) if area.ndim == 3 else area.astype(np.uint8)
                            gray = gray[:: max(1, gray.shape[0] // 90), :: max(1, gray.shape[1] // 160)]

                        prev = prev_post_gray.get(table_id)
                        if prev is not None:
                            score = _roi_change_score(prev, gray)
                            if score >= post_threshold and not bool(st.get("pending_post_action")):
                                if st.get("pending_trigger") == "unknown":
                                    st["pending_trigger"] = "ui_change"
                                st["pending_post_action"] = True
                        prev_post_gray[table_id] = gray

                if ui_enabled and isinstance(ui_roi, list) and len(ui_roi) == 4:
                    x, y, w, h = [int(v) for v in ui_roi]
                    roi = np_img[y : y + h, x : x + w]
                    if roi.size > 0:
                        gray = roi.mean(axis=2).astype(np.uint8) if roi.ndim == 3 else roi.astype(np.uint8)
                        prev = prev_ui_roi_gray.get(table_id)
                        if prev is not None:
                            score = _roi_change_score(prev, gray)
                            if score >= ui_threshold and st.get("pending_trigger") == "unknown":
                                st["pending_trigger"] = "ui_change"
                                if self.ethical_mode:
                                    st["pending_post_action"] = True
                        prev_ui_roi_gray[table_id] = gray

                vision_res = self.vision.parse(pil_img)
                merged = merge_partial_state(None, vision_res)

                if not isinstance(merged.merged_state, PokerGameState):
                    continue

                state = merged.merged_state
                global_conf = float(merged.global_confidence)

                try:
                    validate_poker_state(state)
                except StateValidationError:
                    continue

                state_hash = _stable_json_hash(state.model_dump())
                state_changed = state_hash != st.get("last_state_hash")

                if global_conf < 0.8:
                    continue

                if not state_changed:
                    continue

                if self.ethical_mode and not bool(st.get("pending_post_action")):
                    msg = "Waiting for your action..."
                    if self.output_mode == "overlay":
                        if st.get("last_status") != msg:
                            self._get_overlay().show(msg, table_id=table_id, anchor_rect=anchor_rect)
                            st["last_status"] = msg
                    st["last_state_hash"] = state_hash
                    st["last_global_conf"] = global_conf
                    continue

                report = ParseReport(
                    parser=f"VisionAdapter:{vision_res.adapter_name}",
                    room="unknown",
                    game_type_detected=state.game_type.value,
                    confidence=float(global_conf),
                    missing_fields=["players", "small_blind", "big_blind", "pot", "to_call", "action_history"],
                    warnings=list(merged.warnings),
                    parsed={
                        "hero_hand": [str(c) for c in state.hero_hole],
                        "board": [str(c) for c in state.board],
                        "street": state.street.value,
                    },
                )

                decision = analyze_poker_state(state, report)

                meta = Meta.model_validate(
                    {
                        **self.cfg.meta,
                        "is_realtime": True,
                        "post_action": bool(st.get("pending_post_action")) if self.ethical_mode else False,
                        "trigger": st.get("pending_trigger"),
                        "frame_id": f"live_{table_id}_{int(time.time()*1000)}",
                        "session_id": self.session_id,
                    }
                )

                from coach_app.product.policy import enforce_policy

                policy = enforce_policy(
                    ProductMode.INSTANT_REVIEW if self.ethical_mode else ProductMode.LIVE_RTA,
                    "poker",
                    {"state": state},
                    meta,
                    global_conf,
                )
                if not policy.allowed:
                    msg = str(policy.message)
                    if st.get("last_status") != msg:
                        if self.output_mode == "overlay":
                            self._get_overlay().show(msg, table_id=table_id, anchor_rect=anchor_rect)
                        else:
                            self._output(msg)
                        st["last_status"] = msg
                    st["last_state_hash"] = state_hash
                    st["last_global_conf"] = global_conf
                    st["pending_post_action"] = False
                    st["pending_trigger"] = "unknown"
                    continue

                explanation = explain_from_key_facts(
                    decision_action=decision.action.value,
                    sizing=decision.sizing,
                    confidence=float(min(float(decision.confidence), float(global_conf))),
                    key_facts=decision.key_facts,
                    domain="poker",
                    warnings=list(merged.warnings),
                )

                line_reason = decision.key_facts.get("line_reason")
                if line_reason is None:
                    line_reason = ""
                else:
                    line_reason = str(line_reason)
                sizing_txt = "" if decision.sizing is None else str(decision.sizing)
                text = f"Рекомендация: {decision.action.value} {sizing_txt}\n{line_reason}\n{explanation}".strip()

                if self.output_mode == "overlay":
                    self._get_overlay().show(text, table_id=table_id, anchor_rect=anchor_rect)
                else:
                    self._output(text)
                st["last_status"] = None

                st["last_state_hash"] = state_hash
                st["last_global_conf"] = global_conf
                st["pending_post_action"] = False
                st["pending_trigger"] = "unknown"

            time.sleep(frame_interval)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--mode", default="console", choices=["console", "overlay", "telegram"])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--ethical", dest="ethical", action="store_true")
    g.add_argument("--no-ethical", dest="ethical", action="store_false")
    ap.set_defaults(ethical=True)
    args = ap.parse_args(argv)

    rta = LiveRTA(args.config, output_mode=args.mode, ethical_mode=bool(args.ethical))
    rta.start()
    try:
        rta.join()
    except KeyboardInterrupt:
        rta.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
