

import sys
from pathlib import Path as _Path
_manual_dir = _Path(__file__).resolve().parent
if str(_manual_dir) not in sys.path:
    sys.path.insert(0, str(_manual_dir))
from _root import setup_project_root
setup_project_root()

import sys
try:
    import pyautogui
    print("pyautogui OK:", pyautogui.__version__)
except Exception as e:
    print("pyautogui FAIL:", e)

from launcher.navigation_manager import AUTOGUI_AVAILABLE
print("AUTOGUI_AVAILABLE:", AUTOGUI_AVAILABLE)
