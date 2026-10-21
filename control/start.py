"""
Start HIVE CONTROL: uvicorn on 127.0.0.1:8000 + open browser.

Usage:
    python control/start.py
"""

from __future__ import annotations

import threading
import time
import webbrowser

import uvicorn


def _open_browser() -> None:
    time.sleep(0.8)
    webbrowser.open("http://127.0.0.1:8000/")


def main() -> None:
    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run(
        "control.server:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
