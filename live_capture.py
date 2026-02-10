#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Live захват окна покер-клиента с автоматическим поиском"""

import sys
import time
from PIL import Image

try:
    import mss
except ImportError:
    print("Установите: pip install mss")
    sys.exit(1)

try:
    import pygetwindow as gw
    HAS_PYGETWINDOW = True
except ImportError:
    HAS_PYGETWINDOW = False
    print("Установите: pip install pygetwindow")
    sys.exit(1)


def find_poker_window():
    """Поиск окна покер-клиента"""
    keywords = ['PokerStars', 'GGPoker', 'PartyPoker', 'Poker', 'Hold', 'Texas']
    all_windows = gw.getAllTitles()
    
    print("\n=== Поиск окна покер-клиента ===\n")
    
    for title in all_windows:
        if not title.strip():
            continue
            
        for keyword in keywords:
            if keyword.lower() in title.lower():
                try:
                    windows = gw.getWindowsWithTitle(title)
                    if windows:
                        window = windows[0]
                        if window.width > 300 and window.height > 300:
                            print(f"Найдено: {title}")
                            print(f"Размер: {window.width} x {window.height}")
                            print(f"Позиция: ({window.left}, {window.top})")
                            return window
                except Exception as e:
                    continue
    
    print("Окно НЕ найдено!")
    print("\nДоступные окна:")
    for i, title in enumerate(all_windows[:15]):
        if title.strip():
            print(f"  {i+1}. {title}")
    return None


def capture_window(window):
    """Захват окна"""
    try:
        with mss.mss() as sct:
            monitor = {
                "top": window.top,
                "left": window.left,
                "width": window.width,
                "height": window.height
            }
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img
    except Exception as e:
        print(f"Ошибка захвата: {e}")
        return None


def main():
    print("=" * 60)
    print("  LIVE POKER WINDOW CAPTURE")
    print("=" * 60)
    
    window = find_poker_window()
    
    if not window:
        print("\n!!! Откройте покер-клиент и запустите снова !!!")
        input("\nНажмите Enter для выхода...")
        return
    
    print("\n" + "=" * 60)
    print("  Начинаю захват каждые 3 секунды")
    print("  Нажмите Ctrl+C для остановки")
    print("=" * 60 + "\n")
    
    capture_count = 0
    
    try:
        while True:
            img = capture_window(window)
            
            if img:
                capture_count += 1
                timestamp = time.strftime("%H:%M:%S")
                size_str = f"{img.size[0]}x{img.size[1]}"
                print(f"[{timestamp}] Захват #{capture_count}: {size_str} px")
                
                # Сохраняем последний кадр
                img.save("last_capture.png")
            else:
                print("Переподключение...")
                time.sleep(1)
                window = find_poker_window()
                if not window:
                    print("Окно потеряно!")
                    break
            
            time.sleep(3)
    
    except KeyboardInterrupt:
        print("\n\nОстановка...\n")
        print(f"Всего захватов: {capture_count}")
        print(f"Последний кадр: last_capture.png")


if __name__ == '__main__':
    main()
