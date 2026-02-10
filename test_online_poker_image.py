#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест модели на изображении онлайн-покера
"""
import os
import sys
from PIL import Image

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("ТЕСТ YOLO НА ОНЛАЙН-ПОКЕРЕ")
print("=" * 70)

# Импортируем YOLO
try:
    from ultralytics import YOLO
    print("[OK] ultralytics установлен")
except ImportError:
    print("[ERROR] ultralytics не установлен!")
    exit(1)

# Загружаем модель
model_path = "weights/best.pt"
if not os.path.exists(model_path):
    print(f"[ERROR] Модель не найдена: {model_path}")
    exit(1)

print(f"[OK] Загружаем модель: {model_path}")
model = YOLO(model_path)
print("[OK] Модель загружена")

# Ищем изображение из скриншота
test_image = "test_capture_overlay.png"
if not os.path.exists(test_image):
    # Пробуем другие варианты
    alternatives = [
        "photo_2026-01-16_19-35-24.jpg",
        "stol/screenshot.png",
        "Playing-Cards-Detection-master/Playing-Cards-Detection-master/assets/test.jpg"
    ]
    for alt in alternatives:
        if os.path.exists(alt):
            test_image = alt
            break

if not os.path.exists(test_image):
    print("[ERROR] Тестовое изображение не найдено")
    print("Положите изображение покерного стола в корень проекта")
    exit(1)

print(f"[OK] Тестовое изображение: {test_image}")

# Открываем изображение
img = Image.open(test_image)
print(f"[OK] Размер изображения: {img.size}")

print("\n" + "=" * 70)
print("ДЕТЕКЦИЯ С РАЗНЫМИ ПОРОГАМИ")
print("=" * 70)

# Тест с разными порогами
thresholds = [0.01, 0.05, 0.1, 0.15, 0.2, 0.25]

for conf_threshold in thresholds:
    print(f"\n--- Порог confidence: {conf_threshold} ---")
    results = model(img, conf=conf_threshold, iou=0.3, verbose=False)
    
    result = results[0]
    num_detections = len(result.boxes)
    
    print(f"Найдено объектов: {num_detections}")
    
    if num_detections > 0:
        print("Детекции:")
        for i, box in enumerate(result.boxes[:10], 1):  # Показываем первые 10
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            card_name = model.names[cls_id]
            print(f"  {i}. {card_name} (уверенность: {confidence:.2%})")
        
        if num_detections > 10:
            print(f"  ... и еще {num_detections - 10} объектов")

# Финальная детекция с оптимальным порогом
print("\n" + "=" * 70)
print("ФИНАЛЬНАЯ ДЕТЕКЦИЯ (порог 0.05)")
print("=" * 70)

results = model(img, conf=0.05, iou=0.3, verbose=False)
result = results[0]

if len(result.boxes) == 0:
    print("\n[WARNING] Карты не обнаружены!")
    print("\nВозможные причины:")
    print("  1. Модель обучена на физических картах, а на изображении 3D-карты")
    print("  2. Карты слишком малы или плохо видны")
    print("  3. Нужна модель обученная на онлайн-покере")
    print("\nРекомендации:")
    print("  - Попробуйте использовать изображение с физическими картами")
    print("  - Или нужно дообучить модель на онлайн-покере")
else:
    print(f"\n[OK] Обнаружено карт: {len(result.boxes)}")
    print("\nДетали:")
    for i, box in enumerate(result.boxes, 1):
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        card_name = model.names[cls_id]
        coords = box.xyxy[0].tolist()
        print(f"  {i}. {card_name}")
        print(f"     Уверенность: {conf:.2%}")
        print(f"     Координаты: ({int(coords[0])}, {int(coords[1])}) - ({int(coords[2])}, {int(coords[3])})")
    
    # Сохраняем результат
    output_path = "test_online_poker_result.jpg"
    result.save(output_path)
    print(f"\n[OK] Результат сохранен: {output_path}")

print("\n" + "=" * 70)
print("ТЕСТ ЗАВЕРШЕН")
print("=" * 70)
