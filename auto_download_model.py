#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Автоматическое скачивание модели для игральных карт"""
import os
import sys

print("=" * 70)
print("🎴 АВТОМАТИЧЕСКОЕ СКАЧИВАНИЕ МОДЕЛИ")
print("=" * 70)

# Проверяем, установлен ли roboflow
try:
    from roboflow import Roboflow
    print("✅ Roboflow установлен")
except ImportError:
    print("\n❌ Roboflow не установлен!")
    print("📥 Устанавливаю...")
    os.system("pip install roboflow -q")
    try:
        from roboflow import Roboflow
        print("✅ Roboflow установлен успешно!")
    except:
        print("❌ Не удалось установить Roboflow")
        print("\nУстанови вручную: pip install roboflow")
        sys.exit(1)

# Запрашиваем API ключ
print("\n" + "=" * 70)
print("🔑 НУЖЕН API КЛЮЧ ОТ ROBOFLOW")
print("=" * 70)
print("\n📋 Как получить:")
print("1. Открой: https://app.roboflow.com/")
print("2. Зарегистрируйся (бесплатно)")
print("3. Открой: https://app.roboflow.com/settings/api")
print("4. Скопируй API Key")
print("\n" + "-" * 70)

api_key = input("\n🔑 Вставь API ключ (или нажми Enter для примера): ").strip()

if not api_key:
    print("\n⚠️  API ключ не введён!")
    print("❌ Без ключа не могу скачать модель")
    print("\n📋 Что делать:")
    print("1. Получи API ключ на Roboflow (см. выше)")
    print("2. Запусти скрипт снова")
    print("3. Вставь ключ")
    sys.exit(1)

# Создаём папку для весов
os.makedirs('weights', exist_ok=True)

# Пробуем скачать популярные датасеты с картами
datasets = [
    {
        'name': 'Playing Cards Detection (popular)',
        'workspace': 'roboflow-58fyf',
        'project': 'playing-cards-ir0qh',
        'version': 2
    },
    {
        'name': 'Card Detector',
        'workspace': 'roboflow-100',
        'project': 'playing-cards-ow27d',
        'version': 4
    }
]

print("\n" + "=" * 70)
print("📥 СКАЧИВАНИЕ МОДЕЛИ...")
print("=" * 70)

success = False
for dataset_info in datasets:
    print(f"\n🔄 Пробую: {dataset_info['name']}")
    
    try:
        rf = Roboflow(api_key=api_key)
        project = rf.workspace(dataset_info['workspace']).project(dataset_info['project'])
        dataset = project.version(dataset_info['version']).download("yolov8")
        
        # Ищем best.pt
        possible_paths = [
            os.path.join(dataset.location, 'train', 'weights', 'best.pt'),
            os.path.join(dataset.location, 'weights', 'best.pt'),
            os.path.join(dataset.location, 'runs', 'detect', 'train', 'weights', 'best.pt'),
        ]
        
        best_pt = None
        for path in possible_paths:
            if os.path.exists(path):
                best_pt = path
                break
        
        if best_pt:
            # Копируем в weights/
            import shutil
            target_path = 'weights/best.pt'
            shutil.copy2(best_pt, target_path)
            
            file_size = os.path.getsize(target_path) / 1024 / 1024
            print(f"✅ Успех! Модель скачана: {target_path}")
            print(f"📊 Размер: {file_size:.1f} MB")
            success = True
            break
        else:
            print(f"⚠️  best.pt не найден в датасете")
            print("📝 Нужно обучить модель (см. Способ 4 в инструкции)")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        continue

if success:
    print("\n" + "=" * 70)
    print("🎯 ГОТОВО! МОДЕЛЬ УСТАНОВЛЕНА!")
    print("=" * 70)
    print("\n📋 Что делать дальше:")
    print("1. Запусти: RUN_GUI.bat")
    print("2. Выбери стол (фото)")
    print("3. Нажми: ТЕСТ РАСПОЗНАВАНИЯ")
    print("\n🚀 ПОЕХАЛИ!")
else:
    print("\n" + "=" * 70)
    print("❌ НЕ УДАЛОСЬ СКАЧАТЬ МОДЕЛЬ")
    print("=" * 70)
    print("\n📋 Что делать:")
    print("1. Проверь API ключ")
    print("2. Открой файл: РАБОЧИЕ_ССЫЛКИ_СКАЧАТЬ.md")
    print("3. Попробуй Способ 3 (базовая модель)")
    print("4. Или Способ 4 (Google Colab)")

print("\n" + "=" * 70)
input("Нажми Enter для выхода...")
