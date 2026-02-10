#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ШАГ 3: Обучение модели на онлайн-покере
"""
import os
import sys
from pathlib import Path

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("ОБУЧЕНИЕ МОДЕЛИ НА ОНЛАЙН-ПОКЕРЕ")
print("=" * 70)

# Проверяем ultralytics
try:
    from ultralytics import YOLO
    print("[OK] ultralytics установлен")
except ImportError:
    print("[ERROR] ultralytics не установлен!")
    print("Установите: pip install ultralytics")
    sys.exit(1)

# Проверяем наличие базовой модели
base_model = "weights/best.pt"
if not os.path.exists(base_model):
    print(f"[ERROR] Базовая модель не найдена: {base_model}")
    print("Убедитесь что файл weights/best.pt существует")
    sys.exit(1)

print(f"[OK] Базовая модель найдена: {base_model}")

# Проверяем наличие датасета
dataset_yaml = "training_data/online_poker_dataset/data.yaml"
if not os.path.exists(dataset_yaml):
    print(f"[ERROR] Датасет не найден: {dataset_yaml}")
    print("\nВыполните предыдущие шаги:")
    print("1. Соберите скриншоты: python 1_collect_screenshots.py")
    print("2. Разметьте на Roboflow: см. 2_annotate_guide.txt")
    print("3. Скачайте и распакуйте датасет в: training_data/online_poker_dataset/")
    sys.exit(1)

print(f"[OK] Датасет найден: {dataset_yaml}")

print("\n" + "=" * 70)
print("ПАРАМЕТРЫ ОБУЧЕНИЯ:")
print("=" * 70)

# Параметры обучения
EPOCHS = 100          # Количество эпох (можно увеличить до 200 для лучшего результата)
BATCH = 16           # Размер батча (уменьшите до 8 если мало памяти)
IMGSZ = 640          # Размер изображений
PATIENCE = 20        # Early stopping (остановка если нет улучшений)
PROJECT = "online_poker_training"
NAME = "yolov8_online_poker"

print(f"""
Epochs:        {EPOCHS}
Batch size:    {BATCH}
Image size:    {IMGSZ}
Patience:      {PATIENCE}
Base model:    {base_model}
Dataset:       {dataset_yaml}
Output folder: {PROJECT}/{NAME}
""")

print("=" * 70)
print("ОЦЕНКА ВРЕМЕНИ ОБУЧЕНИЯ:")
print("=" * 70)

# Оценка времени
print("""
С GPU (NVIDIA):
  - 100 эпох: 1-2 часа
  - 200 эпох: 2-4 часа

Без GPU (CPU only):
  - 100 эпох: 8-12 часов
  - 200 эпох: 16-24 часа

💡 СОВЕТ: Если есть GPU - используйте его!
   Проверить: nvidia-smi (в командной строке)
""")

print("\n" + "=" * 70)
input("Нажмите ENTER для начала обучения (или Ctrl+C для отмены)...")
print("=" * 70)

print("\n🚀 НАЧИНАЕМ ОБУЧЕНИЕ!\n")
print("=" * 70)

try:
    # Загружаем базовую модель
    print("Загружаем базовую модель...")
    model = YOLO(base_model)
    print("[OK] Модель загружена\n")
    
    # Запускаем обучение
    print("Начинаем обучение...")
    print("=" * 70)
    
    results = model.train(
        data=dataset_yaml,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        patience=PATIENCE,
        save=True,
        project=PROJECT,
        name=NAME,
        exist_ok=True,
        
        # Оптимизация
        optimizer='AdamW',
        lr0=0.001,
        lrf=0.01,
        momentum=0.937,
        weight_decay=0.0005,
        warmup_epochs=3,
        warmup_momentum=0.8,
        warmup_bias_lr=0.1,
        
        # Аугментации для лучшей генерализации
        hsv_h=0.015,      # Изменение оттенка
        hsv_s=0.7,        # Изменение насыщенности
        hsv_v=0.4,        # Изменение яркости
        degrees=5,        # Поворот
        translate=0.1,    # Сдвиг
        scale=0.5,        # Масштаб
        shear=0.0,        # Искажение
        perspective=0.0,  # Перспектива
        flipud=0.0,       # Вертикальное отражение (не нужно для карт)
        fliplr=0.5,       # Горизонтальное отражение
        mosaic=1.0,       # Mosaic аугментация
        mixup=0.0,        # Mixup аугментация
        
        # Валидация
        val=True,
        plots=True,
        save_period=10,   # Сохранять каждые 10 эпох
    )
    
    print("\n" + "=" * 70)
    print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")
    print("=" * 70)
    
    # Путь к обученной модели
    best_model = f"{PROJECT}/{NAME}/weights/best.pt"
    
    print(f"\n📊 РЕЗУЛЬТАТЫ:")
    print(f"   Обученная модель: {best_model}")
    print(f"   Метрики: {PROJECT}/{NAME}/results.png")
    print(f"   Confusion matrix: {PROJECT}/{NAME}/confusion_matrix.png")
    
    # Показываем метрики
    if hasattr(results, 'results_dict'):
        print(f"\n📈 МЕТРИКИ:")
        metrics = results.results_dict
        if 'metrics/mAP50(B)' in metrics:
            print(f"   mAP50: {metrics['metrics/mAP50(B)']:.4f}")
        if 'metrics/mAP50-95(B)' in metrics:
            print(f"   mAP50-95: {metrics['metrics/mAP50-95(B)']:.4f}")
    
    print("\n" + "=" * 70)
    print("СЛЕДУЮЩИЙ ШАГ:")
    print("=" * 70)
    print(f"""
1. Протестируйте модель:
   python 4_test_model.py

2. Скопируйте модель в проект:
   copy "{best_model}" "weights\\online_poker_best.pt"

3. Обновите yolo_detector.py чтобы использовать новую модель

4. Запустите GUI:
   START_YOLO_GUI.bat
""")

except KeyboardInterrupt:
    print("\n[CTRL+C] Обучение прервано пользователем")
    sys.exit(1)

except Exception as e:
    print(f"\n[ERROR] Ошибка при обучении: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🎉 ГОТОВО!")
