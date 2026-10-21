"""Clone and npm-install ws-scrcpy into third_party/ws-scrcpy."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "third_party" / "ws-scrcpy"
REPO_PRIMARY = "https://github.com/srevinsaju/ws-scrcpy.git"
REPO_FALLBACK = "https://github.com/NetrisTV/ws-scrcpy.git"
MAIN_JS = DEST / "main.js"


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def _node_major() -> int | None:
    node = shutil.which("node")
    if not node:
        return None
    out = subprocess.check_output([node, "-v"], text=True).strip()
    ver = out.lstrip("v").split(".")[0]
    try:
        return int(ver)
    except ValueError:
        return None


def _write_launcher() -> None:
    MAIN_JS.write_text(
        """\
'use strict';
const fs = require('fs');
const path = require('path');
const distIndex = path.join(__dirname, 'dist', 'index.js');
if (!fs.existsSync(distIndex)) {
  console.error('ws-scrcpy dist/index.js missing. Run: npm run dist');
  process.exit(1);
}
require(distIndex);
""",
        encoding="utf-8",
    )


def main() -> int:
    if shutil.which("git") is None:
        print("git не найден в PATH.")
        return 1

    major = _node_major()
    if major is None:
        print("Node.js не найден. Установи Node.js 18+:")
        print("  winget install OpenJS.NodeJS.LTS")
        print("  или https://nodejs.org/")
        return 1
    if major < 18:
        print(f"Нужен Node.js >= 18, сейчас v{major}.")
        print("Обнови: winget install OpenJS.NodeJS.LTS")
        return 1
    print(f"Node.js major={major} — ok")

    DEST.parent.mkdir(parents=True, exist_ok=True)
    if not (DEST / ".git").is_dir():
        if DEST.exists():
            print(f"Каталог {DEST} есть, но это не git-клон. Удали его и повтори.")
            return 1
        try:
            _run(["git", "clone", "--depth", "1", REPO_PRIMARY, str(DEST)])
        except subprocess.CalledProcessError:
            print("srevinsaju/ws-scrcpy недоступен, клонирую NetrisTV/ws-scrcpy")
            _run(["git", "clone", "--depth", "1", REPO_FALLBACK, str(DEST)])
    else:
        print(f"Уже есть клон: {DEST}")

    npm = shutil.which("npm")
    if not npm:
        print("npm не найден (должен идти вместе с Node.js).")
        return 1

    try:
        _run([npm, "install"], cwd=DEST)
    except subprocess.CalledProcessError:
        print("npm install с нативными скриптами не удался (часто node-pty). Повтор с --ignore-scripts")
        _run([npm, "install", "--ignore-scripts"], cwd=DEST)

    dist_index = DEST / "dist" / "index.js"
    if not dist_index.is_file():
        print("Сборка dist (webpack)...")
        _run([npm, "run", "dist"], cwd=DEST)

    _write_launcher()
    pkg = DEST / "package.json"
    name = "ws-scrcpy"
    if pkg.is_file():
        try:
            name = json.loads(pkg.read_text(encoding="utf-8")).get("name", name)
        except json.JSONDecodeError:
            pass
    print(f"готово ({name}): {DEST}")
    print("запуск через `node third_party/ws-scrcpy/main.js`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
