#!/usr/bin/env python


import sys
from pathlib import Path as _Path
_manual_dir = _Path(__file__).resolve().parent
if str(_manual_dir) not in sys.path:
    sys.path.insert(0, str(_manual_dir))
from _root import setup_project_root
setup_project_root()

# -*- coding: utf-8 -*-
"""Быстрый тест текущей модели"""
import os
import sys

print("=" * 70)
print("🔍 ПРОВЕРКА ТЕКУЩИХ МОДЕЛЕЙ")
print("=" * 70)

model_path = 'weights/best.pt'
if not os.path.exists(model_path):
    print(f"\n❌ Модель не найдена: {model_path}")
    print("\n💡 Скачай модель вручную! Инструкция в файле:")
    print("   КАК_СКАЧАТЬ_РАБОЧУЮ_МОДЕЛЬ.md")
    sys.exit(1)

size_mb = os.path.getsize(model_path) / 1024 / 1024
print(f"\n📄 Файл: {model_path}")
print(f"💾 Размер: {size_mb:.1f} MB")

if size_mb < 5:
    print("❌ ПРОБЛЕМА: Файл слишком маленький!")
    print("   Это НЕ обученная модель для карт!")
    print("   Размер должен быть 20-100 MB")
    is_good = False
elif size_mb < 15:
    print("⚠️  ВНИМАНИЕ: Это базовая YOLOv8-nano/small")
    print("   НЕ обучена на картах, будет работать плохо!")
    is_good = False
elif size_mb < 70:
    print("✅ ОТЛИЧНО: Это YOLOv8-medium размер")
    print("   Вероятно обучена на картах!")
    is_good = True
else:
    print("✅ ОТЛИЧНО: Это YOLOv8-large размер")
    print("   Вероятно обучена на картах!")
    is_good = True

print("\n" + "=" * 70)
if is_good:
    print("✅ МОДЕЛЬ ВЫГЛЯДИТ ХОРОШО - ТЕСТИРУЕМ!")
    print("=" * 70)
    print("\n🚀 Запускаю тест на скриншоте...")
    
    # Тестируем модель
    try:
        from ultralytics import YOLO
        from PIL import Image
        
        model = YOLO(model_path)
        print("✅ Модель загружена успешно!")
        
        # Пробуем тест на столе
        if os.path.exists('stol/photo_2026-01-16_19-35-24.jpg'):
            img_path = 'stol/photo_2026-01-16_19-35-24.jpg'
        elif os.path.exists('столок.jpg'):
            img_path = 'столок.jpg'
        else:
            print("⚠️  Скриншот стола не найден")
            sys.exit(0)
        
        print(f"🖼️  Тестируем на: {img_path}")
        results = model(img_path, conf=0.25, verbose=False)
        
        total_detections = len(results[0].boxes) if results else 0
        print(f"\n🎯 AI нашел объектов: {total_detections}")
        
        if total_detections >= 5:
            print("✅ ОТЛИЧНО! Модель находит карты!")
            print("   Запусти GUI и протестируй!")
        elif total_detections > 0:
            print("⚠️  Модель что-то находит, но мало...")
            print("   Возможно, нужна модель получше")
        else:
            print("❌ ПРОБЛЕМА: Модель НЕ находит карты!")
            print("   Нужна модель, обученная на игральных картах!")
            print("\n💡 Скачай правильную модель:")
            print("   Читай: КАК_СКАЧАТЬ_РАБОЧУЮ_МОДЕЛЬ.md")
        
    except Exception as e:
        print(f"❌ Ошибка при тесте: {e}")
        
else:
    print("❌ МОДЕЛЬ НЕ ПОДХОДИТ!")
    print("=" * 70)
    print("\n💡 СКАЧАЙ РАБОЧУЮ МОДЕЛЬ:")
    print("   Инструкция: КАК_СКАЧАТЬ_РАБОЧУЮ_МОДЕЛЬ.md")
    print("\n🔗 Прямая ссылка (самая простая):")
    print("   https://universe.roboflow.com/roboflow-100/playing-cards-ow27d")
    print("   Нажми Export -> YOLOv8 -> Download")

print()
