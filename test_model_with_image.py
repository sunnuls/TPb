#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Тест модели на реальном изображении карт
"""
import os
import sys
from pathlib import Path

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("ТЕСТ МОДЕЛИ НА РЕАЛЬНОМ ИЗОБРАЖЕНИИ КАРТ")
print("=" * 70)

# Проверяем ultralytics
try:
    from ultralytics import YOLO
    print("[OK] ultralytics установлен")
except ImportError:
    print("[ERROR] ultralytics не установлен!")
    print("Установите: pip install ultralytics")
    exit(1)

# Загружаем модель
model_path = "weights/best.pt"
if not os.path.exists(model_path):
    print(f"[ERROR] Модель не найдена: {model_path}")
    exit(1)

print(f"[OK] Модель найдена: {model_path}")
model = YOLO(model_path)
print("[OK] Модель загружена")

# Ищем тестовое изображение
test_images = [
    "Playing-Cards-Detection-master/Playing-Cards-Detection-master/assets/test.jpg",
    "stol/screenshot.png",
    "test_capture_overlay.png"
]

test_image = None
for img_path in test_images:
    if os.path.exists(img_path):
        test_image = img_path
        break

if not test_image:
    print("[WARNING] Тестовое изображение не найдено")
    print("Попробуйте положить изображение карт в корень проекта")
    exit(0)

print(f"[OK] Тестовое изображение: {test_image}")

print("\n" + "=" * 70)
print("ЗАПУСК ДЕТЕКЦИИ...")
print("=" * 70)

# Запускаем детекцию
results = model(test_image, conf=0.25, verbose=True)

print("\n" + "=" * 70)
print("РЕЗУЛЬТАТЫ ДЕТЕКЦИИ:")
print("=" * 70)

# Анализируем результаты
result = results[0]
if len(result.boxes) == 0:
    print("[WARNING] Карты не обнаружены!")
else:
    print(f"[OK] Обнаружено карт: {len(result.boxes)}")
    print("\nСписок обнаруженных карт:")
    
    for i, box in enumerate(result.boxes, 1):
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        card_name = model.names[cls_id]
        print(f"  {i}. {card_name} (уверенность: {conf:.2%})")

# Сохраняем результат
output_path = "test_model_result.jpg"
result.save(output_path)
print(f"\n[OK] Результат сохранен: {output_path}")

print("\n" + "=" * 70)
print("ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
print("=" * 70)
print("\nОткройте файл 'test_model_result.jpg' чтобы увидеть результат")
