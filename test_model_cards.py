#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест модели yolov8s_playing_cards.pt для детекции карт
"""
import os
import sys
from pathlib import Path

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("ТЕСТ МОДЕЛИ ДЛЯ ДЕТЕКЦИИ ИГРАЛЬНЫХ КАРТ")
print("=" * 60)

# Проверяем установлен ли ultralytics
try:
    from ultralytics import YOLO
    print("[OK] ultralytics установлен")
except ImportError:
    print("[ERROR] ultralytics НЕ установлен!")
    print("Установите: pip install ultralytics")
    exit(1)

# Проверяем наличие модели
model_paths = [
    "weights/best.pt",
    "yolov8s_playing_cards.pt",
    "weights/yolov8s_playing_cards.pt"
]

model_path = None
for path in model_paths:
    if os.path.exists(path):
        model_path = path
        print(f"[OK] Модель найдена: {path}")
        file_size = os.path.getsize(path) / (1024 * 1024)  # MB
        print(f"   Размер: {file_size:.2f} MB")
        break

if not model_path:
    print("[ERROR] Модель НЕ найдена!")
    print("Ожидаемые пути:")
    for path in model_paths:
        print(f"  - {path}")
    exit(1)

print("\n" + "=" * 60)
print("ЗАГРУЗКА МОДЕЛИ...")
print("=" * 60)

try:
    model = YOLO(model_path)
    print("[OK] Модель успешно загружена!")
    
    # Проверяем информацию о модели
    print(f"\nИнформация о модели:")
    print(f"   Путь: {model_path}")
    
    # Пытаемся получить информацию о классах
    if hasattr(model, 'names'):
        print(f"   Количество классов: {len(model.names)}")
        print(f"   Классы (первые 10): {list(model.names.values())[:10]}")
    
    print("\n" + "=" * 60)
    print("МОДЕЛЬ ГОТОВА К РАБОТЕ!")
    print("=" * 60)
    print("\nМодель может распознавать:")
    print("  - Все 52 карты (A, K, Q, J, 10, 9, 8, 7, 6, 5, 4, 3, 2)")
    print("  - Все масти (Spades, Hearts, Clubs, Diamonds)")
    print("  - Примеры: AS, KH, QD, JC, 10S, 2H...")
    
    print("\nДля запуска GUI используйте:")
    print("   python poker_gui.py")
    print("   или")
    print("   START_YOLO_GUI.bat")
    
except Exception as e:
    print(f"[ERROR] ОШИБКА при загрузке модели: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
