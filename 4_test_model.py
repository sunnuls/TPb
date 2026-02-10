#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ШАГ 4: Тестирование обученной модели
"""
import os
import sys
from pathlib import Path

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("ТЕСТИРОВАНИЕ ОБУЧЕННОЙ МОДЕЛИ")
print("=" * 70)

# Проверяем ultralytics
try:
    from ultralytics import YOLO
    from PIL import Image
    print("[OK] ultralytics установлен")
except ImportError:
    print("[ERROR] ultralytics не установлен!")
    print("Установите: pip install ultralytics")
    sys.exit(1)

# Ищем обученную модель
trained_model = "online_poker_training/yolov8_online_poker/weights/best.pt"

if not os.path.exists(trained_model):
    print(f"[ERROR] Обученная модель не найдена: {trained_model}")
    print("\nВыполните сначала обучение: python 3_train_model.py")
    sys.exit(1)

print(f"[OK] Обученная модель найдена: {trained_model}")

# Загружаем модель
print("\nЗагружаем модель...")
model = YOLO(trained_model)
print("[OK] Модель загружена")

print(f"\n📊 Информация о модели:")
print(f"   Классов: {len(model.names)}")
print(f"   Примеры классов: {list(model.names.values())[:10]}")

# Ищем тестовые изображения
test_images = [
    "test_capture_overlay.png",
    "training_data/raw_screenshots/",
]

test_image = None
for path in test_images:
    if os.path.exists(path):
        if os.path.isdir(path):
            # Берем первое изображение из папки
            files = [f for f in os.listdir(path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            if files:
                test_image = os.path.join(path, files[0])
                break
        else:
            test_image = path
            break

if not test_image:
    print("\n[WARNING] Тестовое изображение не найдено")
    print("Положите изображение онлайн-покера в корень проекта")
    print("или укажите путь:")
    test_image = input("\nПуть к изображению: ").strip()
    
    if not os.path.exists(test_image):
        print(f"[ERROR] Файл не найден: {test_image}")
        sys.exit(1)

print(f"\n[OK] Тестовое изображение: {test_image}")

# Открываем изображение
img = Image.open(test_image)
print(f"[OK] Размер изображения: {img.size}")

print("\n" + "=" * 70)
print("ТЕСТИРОВАНИЕ С РАЗНЫМИ ПОРОГАМИ")
print("=" * 70)

# Тестируем с разными порогами confidence
thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]

best_threshold = None
best_count = 0

for conf_threshold in thresholds:
    print(f"\n--- Порог confidence: {conf_threshold} ---")
    results = model(img, conf=conf_threshold, iou=0.3, verbose=False)
    
    result = results[0]
    num_detections = len(result.boxes)
    
    print(f"Найдено карт: {num_detections}")
    
    if num_detections > 0:
        print("Карты:")
        for i, box in enumerate(result.boxes[:10], 1):
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            card_name = model.names[cls_id]
            print(f"  {i}. {card_name} ({confidence:.1%})")
        
        if num_detections > 10:
            print(f"  ... и еще {num_detections - 10} карт")
    
    # Запоминаем лучший результат
    if num_detections > best_count:
        best_count = num_detections
        best_threshold = conf_threshold

print("\n" + "=" * 70)
print(f"ФИНАЛЬНОЕ ТЕСТИРОВАНИЕ (порог {best_threshold or 0.25})")
print("=" * 70)

# Финальная детекция с оптимальным порогом
final_threshold = best_threshold or 0.25
results = model(img, conf=final_threshold, iou=0.3, verbose=True)
result = results[0]

if len(result.boxes) == 0:
    print("\n[WARNING] Карты не обнаружены!")
    print("\nВозможные причины:")
    print("  1. Модель еще недостаточно обучена (нужно больше эпох)")
    print("  2. Недостаточно размеченных данных")
    print("  3. Тестовое изображение сильно отличается от обучающих")
    print("\nРекомендации:")
    print("  - Продолжите обучение (больше эпох)")
    print("  - Добавьте больше размеченных скриншотов")
    print("  - Попробуйте другое тестовое изображение")
else:
    print(f"\n✅ Обнаружено карт: {len(result.boxes)}")
    print("\nДетали:")
    
    # Группируем по классам
    cards_by_class = {}
    for box in result.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        card_name = model.names[cls_id]
        
        if card_name not in cards_by_class:
            cards_by_class[card_name] = []
        cards_by_class[card_name].append(conf)
    
    # Выводим результаты
    for i, (card, confidences) in enumerate(sorted(cards_by_class.items()), 1):
        avg_conf = sum(confidences) / len(confidences)
        count = len(confidences)
        if count > 1:
            print(f"  {i}. {card} × {count} (средняя уверенность: {avg_conf:.1%})")
        else:
            print(f"  {i}. {card} ({avg_conf:.1%})")
    
    # Сохраняем результат
    output_path = "test_trained_model_result.jpg"
    result.save(output_path)
    print(f"\n[OK] Результат сохранен: {output_path}")
    
    # Сравниваем с базовой моделью
    print("\n" + "=" * 70)
    print("СРАВНЕНИЕ С БАЗОВОЙ МОДЕЛЬЮ")
    print("=" * 70)
    
    base_model_path = "weights/best.pt"
    if os.path.exists(base_model_path):
        print(f"\nТестируем базовую модель (не обученную на онлайн-покере)...")
        base_model = YOLO(base_model_path)
        base_results = base_model(img, conf=final_threshold, verbose=False)
        base_count = len(base_results[0].boxes)
        
        print(f"\nРЕЗУЛЬТАТЫ:")
        print(f"  Базовая модель:    {base_count} карт")
        print(f"  Обученная модель:  {len(result.boxes)} карт")
        
        improvement = len(result.boxes) - base_count
        if improvement > 0:
            print(f"\n✅ УЛУЧШЕНИЕ: +{improvement} карт!")
        elif improvement < 0:
            print(f"\n⚠️ Обученная модель хуже на {abs(improvement)} карт")
            print("   Рекомендуем продолжить обучение или добавить данных")
        else:
            print("\n➡️ Результаты одинаковые")

print("\n" + "=" * 70)
print("СЛЕДУЮЩИЙ ШАГ:")
print("=" * 70)
print(f"""
Если результаты хорошие:

1. Скопируйте модель в проект:
   copy "{trained_model}" "weights\\online_poker_best.pt"

2. Обновите yolo_detector.py:
   В строке ~35 добавьте в начало списка:
   "weights/online_poker_best.pt",

3. Запустите GUI:
   START_YOLO_GUI.bat

4. Протестируйте на реальных скриншотах!

Если результаты плохие:
- Добавьте больше размеченных изображений (500-1000+)
- Увеличьте epochs до 200-300
- Проверьте качество разметки на Roboflow
""")

print("\n🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
