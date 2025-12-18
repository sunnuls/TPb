from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import numpy as np
import yaml
from PIL import Image

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from PIL import ImageGrab  # type: ignore
except Exception:  # pragma: no cover
    ImageGrab = None  # type: ignore[assignment]

from coach_app.ingest.vision.generic_adapter import GenericVisionAdapter


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _stable_hash(obj: Any) -> str:
    b = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _sha256_hex(b)


def _build_multipart_form(*, fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f"----InstantReviewBoundary{uuid.uuid4().hex}"
    lines: list[bytes] = []

    for name, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        lines.append(value.encode("utf-8"))
        lines.append(b"\r\n")

    for name, (filename, content, content_type) in files.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        lines.append(f"Content-Type: {content_type}\r\n\r\n".encode())
        lines.append(content)
        lines.append(b"\r\n")

    lines.append(f"--{boundary}--\r\n".encode())
    body = b"".join(lines)
    return body, boundary


def _http_post_multipart_json(*, url: str, payload_obj: dict[str, Any], image_bytes: bytes, filename: str) -> tuple[int, dict[str, Any]]:
    payload_str = json.dumps(payload_obj, ensure_ascii=False)
    body, boundary = _build_multipart_form(
        fields={"payload": payload_str},
        files={"image": (filename, image_bytes, "image/png")},
    )
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urlopen(req, timeout=30) as resp:
            status = int(getattr(resp, "status", 200))
            raw = resp.read().decode("utf-8")
            return status, json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read().decode("utf-8") if hasattr(e, "read") else ""
        try:
            data = json.loads(raw) if raw else {}
        except Exception:
            data = {"raw": raw}
        return int(e.code), data


@dataclass
class TrackerConfig:
    api_base_url: str
    endpoint_path: str
    mode: str
    meta: dict[str, Any]
    fps: float
    input_mode: str
    dev_frames_folder: str
    dev_frames_loop: bool
    ui_change: dict[str, Any]
    desktop_capture: dict[str, Any]
    telegram: dict[str, Any]


def load_config(path: str) -> TrackerConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    ui_change = dict(data.get("ui_change", {}) or {})
    if "ui_change_enabled" in data and "enabled" not in ui_change:
        ui_change["enabled"] = bool(data.get("ui_change_enabled"))
    if "ui_change_roi" in data and "roi" not in ui_change:
        ui_change["roi"] = data.get("ui_change_roi")
    if "ui_change_threshold" in data and "threshold" not in ui_change:
        ui_change["threshold"] = float(data.get("ui_change_threshold"))

    return TrackerConfig(
        api_base_url=str(data.get("api_base_url", "http://127.0.0.1:8000")),
        endpoint_path=str(data.get("endpoint_path", "/analyze/poker/screenshot")),
        mode=str(data.get("mode", "instant_review")),
        meta=dict(data.get("meta", {}) or {}),
        fps=float(data.get("fps", 2)),
        input_mode=str(data.get("input_mode", "dev_frames")),
        dev_frames_folder=str(data.get("dev_frames_folder", "tools/frames")),
        dev_frames_loop=bool(data.get("dev_frames_loop", True)),
        ui_change=ui_change,
        desktop_capture=dict(data.get("desktop_capture", {}) or {}),
        telegram=dict(data.get("telegram", {}) or {}),
    )


class InstantReviewStateMachine:
    def __init__(
        self,
        *,
        session_id: str,
        meta_defaults: dict[str, Any],
        vision_parse: Callable[[bytes], dict[str, Any]],
    ) -> None:
        self.session_id = session_id
        self.meta_defaults = dict(meta_defaults)
        self._vision_parse = vision_parse

        self.last_state_hash: str | None = None
        self.pending_post_action: bool = False
        self.pending_trigger: str = "unknown"

    def observe_frame(self, *, frame_bytes: bytes, frame_id: str) -> None:
        _ = frame_id
        partial_state = self._vision_parse(frame_bytes)
        self.last_state_hash = _stable_hash(partial_state)

    def trigger_post_action(self, *, trigger: str) -> None:
        self.pending_post_action = True
        self.pending_trigger = trigger if trigger in ("ui_change", "hotkey", "hand_complete", "unknown") else "unknown"

    def build_payload(self, *, mode: str, frame_id: str) -> dict[str, Any] | None:
        if not self.pending_post_action:
            return None
        meta = dict(self.meta_defaults)
        meta.update(
            {
                "post_action": True,
                "trigger": self.pending_trigger,
                "frame_id": frame_id,
                "session_id": self.session_id,
            }
        )
        return {"mode": mode, "meta": meta}

    def mark_sent(self) -> None:
        self.pending_post_action = False
        self.pending_trigger = "unknown"


def _iter_dev_frames(folder: str, *, loop: bool) -> Callable[[], tuple[str, bytes]]:
    p = Path(folder)
    exts = {".png", ".jpg", ".jpeg", ".bmp"}
    files = sorted([x for x in p.glob("*") if x.suffix.lower() in exts])
    if not files:
        raise FileNotFoundError(f"No frames found in {p}")

    idx = 0

    def next_frame() -> tuple[str, bytes]:
        nonlocal idx
        if idx >= len(files):
            if not loop:
                raise StopIteration
            idx = 0
        fp = files[idx]
        idx += 1
        return fp.name, fp.read_bytes()

    return next_frame


def _capture_desktop(region: list[int] | None) -> tuple[str, bytes]:
    if ImageGrab is None:
        raise RuntimeError("PIL.ImageGrab is not available; use dev_frames input_mode")
    bbox = None
    if region and len(region) == 4:
        bbox = tuple(int(x) for x in region)  # type: ignore[assignment]
    img = ImageGrab.grab(bbox=bbox)
    import io

    b = io.BytesIO()
    img.save(b, format="PNG")
    return f"desktop_{int(time.time()*1000)}.png", b.getvalue()


def _roi_change_score(prev: Image.Image, curr: Image.Image) -> float:
    a = np.asarray(prev.convert("L"), dtype=np.float32)
    b = np.asarray(curr.convert("L"), dtype=np.float32)
    if a.shape != b.shape:
        return float("inf")
    return float(np.mean(np.abs(a - b)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tools/config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)

    api_url = cfg.api_base_url.rstrip("/") + cfg.endpoint_path
    session_id = uuid.uuid4().hex

    adapter = GenericVisionAdapter(game="poker")

    def vision_parse(frame_bytes: bytes) -> dict[str, Any]:
        res = adapter.parse(frame_bytes)
        return dict(res.partial_state or {})

    sm = InstantReviewStateMachine(session_id=session_id, meta_defaults=cfg.meta, vision_parse=vision_parse)

    hotkey_event = threading.Event()

    def hotkey_thread() -> None:
        while True:
            try:
                input()
            except EOFError:
                return
            hotkey_event.set()

    t = threading.Thread(target=hotkey_thread, daemon=True)
    t.start()

    if cfg.input_mode == "dev_frames":
        next_frame = _iter_dev_frames(cfg.dev_frames_folder, loop=bool(cfg.dev_frames_loop))
        get_frame: Callable[[], tuple[str, bytes]] = next_frame
    elif cfg.input_mode == "desktop":
        region = cfg.desktop_capture.get("region")
        get_frame = lambda: _capture_desktop(region)
    else:
        raise ValueError("input_mode must be dev_frames or desktop")

    ui_enabled = bool(cfg.ui_change.get("enabled", False))
    roi = cfg.ui_change.get("roi")
    threshold = float(cfg.ui_change.get("threshold", 20.0))
    prev_roi_img: Image.Image | None = None

    frame_interval = 1.0 / max(0.1, float(cfg.fps))

    while True:
        try:
            frame_id, frame_bytes = get_frame()
        except StopIteration:
            return 0

        sm.observe_frame(frame_bytes=frame_bytes, frame_id=frame_id)

        if hotkey_event.is_set():
            hotkey_event.clear()
            sm.trigger_post_action(trigger="hotkey")

        if ui_enabled and roi and isinstance(roi, list) and len(roi) == 4:
            x, y, w, h = [int(v) for v in roi]
            import io

            curr = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
            curr_roi = curr.crop((x, y, x + w, y + h))
            if prev_roi_img is not None:
                score = _roi_change_score(prev_roi_img, curr_roi)
                if score >= threshold and not sm.pending_post_action:
                    sm.trigger_post_action(trigger="ui_change")
            prev_roi_img = curr_roi

        payload = sm.build_payload(mode=cfg.mode, frame_id=frame_id)
        if payload is not None:
            status, data = _http_post_multipart_json(
                url=api_url,
                payload_obj=payload,
                image_bytes=frame_bytes,
                filename=frame_id,
            )
            if status == 200:
                explanation = data.get("explanation")
                if isinstance(explanation, str) and explanation.strip():
                    print(explanation)
                else:
                    print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                # Do not print any decision/explanation for non-200 responses.
                print(f"HTTP {status}: {json.dumps(data, ensure_ascii=False)}")
            sm.mark_sent()

        time.sleep(frame_interval)


if __name__ == "__main__":
    raise SystemExit(main())
