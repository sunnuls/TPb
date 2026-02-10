#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скачивание рабочей модели для игральных карт"""
import urllib.request
import os
import sys

print("=" * 70)
print("🎴 СКАЧИВАНИЕ РАБОЧЕЙ AI МОДЕЛИ ДЛЯ КАРТ")
print("=" * 70)

# Создаем папку
os.makedirs('weights', exist_ok=True)

# Список проверенных источников
models = [
    {
        'name': 'YOLOv8-small базовая (для начала)',
        'url': 'https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt',
        'filename': 'yolov8s.pt',
        'note': 'Базовая модель, будет использовать фильтры'
    }
]

for model_info in models:
    save_path = os.path.join('weights', model_info['filename'])
    
    if os.path.exists(save_path):
        print(f"\n✅ Модель уже существует: {save_path}")
        continue
    
    print(f"\n📥 Скачивание: {model_info['name']}")
    print(f"🌐 URL: {model_info['url']}")
    print(f"📝 Примечание: {model_info['note']}")
    
    try:
        def show_progress(count, block_size, total_size):
            if total_size > 0:
                percent = min(int(count * block_size * 100 / total_size), 100)
                bar = '█' * (percent // 2) + '░' * (50 - percent // 2)
                print(f"\r[{bar}] {percent}%", end='', flush=True)
        
        urllib.request.urlretrieve(model_info['url'], save_path, reporthook=show_progress)
        print()  # Новая строка
        
        file_size = os.path.getsize(save_path) / 1024 / 1024
        print(f"✅ Успех! Размер: {file_size:.1f} MB")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        continue

print("\n" + "=" * 70)
print("🎯 ТЕПЕРЬ ПРОТЕСТИРУЙ GUI!")
print("=" * 70)
print("\n📋 Что делать:")
print("1. Закрой текущий GUI (если открыт)")
print("2. Запусти: RUN_GUI.bat")
print("3. Выбери скриншот: столок.jpg")
print("4. Нажми: ТЕСТ РАСПОЗНАВАНИЯ")
print("\n⚠️  ВАЖНО:")
print("Это базовая YOLOv8 - она будет искать все объекты")
print("и фильтровать их по форме карт.")
print("\nДля ЛУЧШЕЙ точности скачай модель вручную:")
print("https://www.kaggle.com/models/keremberke/yolov8s-playing-cards-detection")
print()
