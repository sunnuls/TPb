#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест CV детектора с OpenCV
"""
from PIL import Image
from cv_detector import CVCardDetector

print("=" * 60)
print("ТЕСТ CV ДЕТЕКТОРА (OpenCV)")
print("=" * 60)

# Загружаем изображение
img_path = "stol/photo_2026-01-16_19-35-24.jpg"
print(f"\n[1] Загрузка: {img_path}")
img = Image.open(img_path)
print(f"    Размер: {img.size}")

# Создаём детектор
print("\n[2] Инициализация CV детектора...")
detector = CVCardDetector()

# Запускаем детекцию
print("\n[3] Запуск детекции...")
result = detector.detect_and_recognize(img)

# Выводим результаты
print("\n" + "=" * 60)
print("РЕЗУЛЬТАТЫ:")
print("=" * 60)

print(f"\n✓ Карты героя: {len(result['hero_cards'])} - {result['hero_cards']}")
print(f"✓ Карты борда: {len(result['board_cards'])} - {result['board_cards']}")
print(f"✓ Всего найдено: {len(result.get('all_detections', []))}")

# Сохраняем debug
debug_path = "cv_test_debug.png"
result['debug_image'].save(debug_path)
print(f"\n📸 Debug: {debug_path}")

print("\n" + "=" * 60)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 60)
