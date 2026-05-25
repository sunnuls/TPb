import sys
try:
    import pyautogui
    print("pyautogui OK:", pyautogui.__version__)
except Exception as e:
    print("pyautogui FAIL:", e)

from launcher.navigation_manager import AUTOGUI_AVAILABLE
print("AUTOGUI_AVAILABLE:", AUTOGUI_AVAILABLE)
