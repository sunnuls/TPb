#!/usr/bin/env python


import sys
from pathlib import Path as _Path
_manual_dir = _Path(__file__).resolve().parent
if str(_manual_dir) not in sys.path:
    sys.path.insert(0, str(_manual_dir))
from _root import setup_project_root
setup_project_root()

# -*- coding: utf-8 -*-
"""
Прямой тест YOLO на изображении столок.jpg
Показывает ВСЕ объекты которые YOLO находит (без фильтров)
"""
from PIL import Image, ImageDraw
from yolo_detector import YoloCardDetector

print("=" * 60)
print("ТЕСТ YOLO ДЕТЕКТОРА")
print("=" * 60)

# Загружаем изображение
img_path = "stol/photo_2026-01-16_19-35-24.jpg"
print(f"\n[1] Загрузка изображения: {img_path}")
img = Image.open(img_path)
print(f"    Размер: {img.size}")

# Создаём детектор
print("\n[2] Инициализация YOLO детектора...")
detector = YoloCardDetector()

if not detector.model:
    print("[ERROR] YOLO модель не загружена!")
    exit(1)

# Запускаем детекцию
print("\n[3] Запуск детекции...")
result = detector.detect_and_recognize(img)

# Выводим результаты
print("\n" + "=" * 60)
print("РЕЗУЛЬТАТЫ:")
print("=" * 60)

print(f"\n✅ Найдено объектов YOLO: {len(result.get('all_detections', []))}")
print(f"✅ Карты героя: {len(result['hero_cards'])}")
print(f"✅ Карты борда: {len(result['board_cards'])}")

# Детали всех детекций
if 'all_detections' in result:
    print(f"\nДетали всех {len(result['all_detections'])} детекций:")
    for i, det in enumerate(result['all_detections'], 1):
        print(f"  #{i}: pos=({det['x']}, {det['y']}) size={det['w']}x{det['h']} conf={det.get('confidence', 0):.2f}")

# Сохраняем debug изображение
debug_path = "yolo_test_debug.png"
result['debug_image'].save(debug_path)
print(f"\n📸 Debug изображение сохранено: {debug_path}")

print("\n" + "=" * 60)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 60)
