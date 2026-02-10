#!/usr/bin/env python3
"""Verification script for simulation research dependencies."""

import sys

print("=" * 60)
print("Verifying Simulation Research Dependencies")
print("=" * 60)
print(f"Python: {sys.version}\n")

dependencies = {
    "Core": [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
    ],
    "Vision (Live)": [
        ("cv2", "OpenCV"),
        ("pytesseract", "PyTesseract"),
        ("mss", "MSS"),
        ("keyboard", "Keyboard"),
        ("ultralytics", "Ultralytics YOLO"),
    ],
    "Simulation": [
        ("websockets", "Websockets"),
        ("torch", "PyTorch"),
    ],
    "Development": [
        ("pytest", "Pytest"),
        ("httpx", "HTTPX"),
    ],
}

missing = []
installed = []

for category, deps in dependencies.items():
    print(f"\n{category}:")
    for module_name, display_name in deps:
        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", "installed")
            print(f"  [OK] {display_name}: {version}")
            installed.append(display_name)
        except ImportError:
            print(f"  [MISSING] {display_name}: NOT FOUND")
            missing.append(display_name)
        except Exception as e:
            print(f"  [ERROR] {display_name}: {type(e).__name__}")
            missing.append(display_name)

print("\n" + "=" * 60)
print(f"Summary: {len(installed)} installed, {len(missing)} missing")
print("=" * 60)

if missing:
    print(f"\nMissing packages: {', '.join(missing)}")
    print("\nOptional: Run INSTALL_SIMULATION_DEPS.bat to install missing deps")
else:
    print("\n[OK] All critical dependencies are installed!")
    print("[OK] Ready for simulation research framework development")

sys.exit(0 if len(missing) == 0 else 1)
