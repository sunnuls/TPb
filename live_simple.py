import sys
import os
import time
import codecs

if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

import yaml
import mss
import numpy as np
from PIL import Image
import pytesseract

try:
    import pygetwindow as gw
    HAS_WINDOW_LIB = True
except ImportError:
    HAS_WINDOW_LIB = False
    print('РЈСЃС‚Р°РЅРѕРІРёС‚Рµ pygetwindow')

class PokerWindowCapture:
    def __init__(self):
        self.window = None
        self.sct = mss.mss()
        self.keywords = ['PokerStars', 'GGPoker', 'Poker', 'Hold']
    
    def find_window(self):
        if not HAS_WINDOW_LIB:
            return None
        all_windows = gw.getAllTitles()
        for title in all_windows:
            for keyword in self.keywords:
                if keyword.lower() in title.lower():
                    try:
                        w = gw.getWindowsWithTitle(title)[0]
                        if w.width > 300 and w.height > 300:
                            self.window = w
                            print(f'РќР°Р№РґРµРЅРѕ: {title}')
                            print(f'Р Р°Р·РјРµСЂ: {w.width}x{w.height}')
                            return w
                    except:
                        pass
        print('РћРєРЅРѕ РЅРµ РЅР°Р№РґРµРЅРѕ')
        return None
    
    def capture(self):
        if not self.window:
            self.find_window()
            if not self.window:
                return None
        try:
            mon = {
                'top': self.window.top,
                'left': self.window.left,
                'width': self.window.width,
                'height': self.window.height
            }
            sct = self.sct.grab(mon)
            return Image.frombytes('RGB', sct.size, sct.bgra, 'raw', 'BGRX')
        except:
            self.window = None
            return None

capture = PokerWindowCapture()
print('РџРѕРёСЃРє РѕРєРЅР°...')
if capture.find_window():
    print('Р—Р°С…РІР°С‚ РєР°Р¶РґС‹Рµ 3 СЃРµРє. Ctrl+C РґР»СЏ РѕСЃС‚Р°РЅРѕРІРєРё.')
    while True:
        img = capture.capture()
        if img:
            print(f'{time.strftime(\"%H:%M:%S\")} - Р—Р°С…РІР°С‡РµРЅРѕ: {img.size}')
        else:
            print('РћС€РёР±РєР° Р·Р°С…РІР°С‚Р°')
        time.sleep(3)
else:
    print('РћС‚РєСЂРѕР№С‚Рµ РїРѕРєРµСЂ-РєР»РёРµРЅС‚!')
