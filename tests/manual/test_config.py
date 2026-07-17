#!/usr/bin/env python3
"""
Скрипт для тестирования конфигурации зон захвата
Проверяет корректность конфига и визуализирует зоны
"""

import sys
from pathlib import Path as _Path
_manual_dir = _Path(__file__).resolve().parent
if str(_manual_dir) not in sys.path:
    sys.path.insert(0, str(_manual_dir))
from _root import setup_project_root
setup_project_root()

import yaml
import json
import sys
from pathlib import Path

def load_config(config_path):
    """Загрузка конфигурации"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                config = yaml.safe_load(f)
            else:
                config = json.load(f)
        return config
    except Exception as e:
        print(f"❌ Ошибка загрузки конфига: {e}")
        return None

def validate_config(config):
    """Проверка корректности конфигурации"""
    print("\n🔍 Проверка конфигурации...\n")
    
    errors = []
    warnings = []
    
    # Проверка обязательных полей
    if 'rois' not in config:
        errors.append("Отсутствует секция 'rois'")
        return errors, warnings
    
    rois = config['rois']
    
    # Рекомендуемые зоны
    recommended_zones = {
        'hero_card_1': '🃏 Карта героя #1',
        'hero_card_2': '🃏 Карта героя #2',
        'board_card_1': '🎴 Флоп #1',
        'board_card_2': '🎴 Флоп #2',
        'board_card_3': '🎴 Флоп #3',
        'board_card_4': '🎴 Терн',
        'board_card_5': '🎴 Ривер',
        'pot': '💰 Банк',
        'hero_stack': '💵 Стек героя',
    }
    
    # Проверка наличия зон
    found_zones = []
    missing_zones = []
    
    for zone_key, zone_name in recommended_zones.items():
        if zone_key in rois:
            found_zones.append((zone_key, zone_name))
        else:
            missing_zones.append((zone_key, zone_name))
    
    # Вывод найденных зон
    if found_zones:
        print("✅ Найденные зоны:")
        for key, name in found_zones:
            zone = rois[key]
            print(f"   {name}")
            print(f"      └─ x:{zone['x']}, y:{zone['y']}, w:{zone['w']}, h:{zone['h']}")
    
    # Вывод отсутствующих зон
    if missing_zones:
        print("\n⚠️  Отсутствующие зоны (рекомендуется добавить):")
        for key, name in missing_zones:
            warnings.append(f"Отсутствует зона: {name}")
            print(f"   {name}")
    
    # Проверка размеров зон
    print("\n🔍 Проверка размеров зон:")
    for key, zone in rois.items():
        if zone['w'] < 20 or zone['h'] < 20:
            warnings.append(f"Зона '{key}' слишком маленькая ({zone['w']}x{zone['h']})")
            print(f"   ⚠️  {key}: слишком маленькая ({zone['w']}x{zone['h']})")
        else:
            print(f"   ✅ {key}: {zone['w']}x{zone['h']}")
    
    return errors, warnings

def visualize_config(config):
    """Визуализация конфигурации"""
    print("\n📊 Сводка конфигурации:")
    print(f"   Адаптер: {config.get('adapter', 'N/A')}")
    print(f"   Режим захвата: {config.get('capture_mode', 'N/A')}")
    
    if 'screen_resolution' in config:
        res = config['screen_resolution']
        print(f"   Разрешение: {res['width']}x{res['height']}")
    
    print(f"   Всего зон: {len(config.get('rois', {}))}")

def main():
    print("=" * 60)
    print("🎮 TPb Config Validator")
    print("=" * 60)
    
    # Поиск конфига
    config_files = list(Path('.').glob('*.yaml')) + list(Path('.').glob('*.yml'))
    
    if not config_files:
        print("\n❌ Файл конфигурации не найден!")
        print("   Скачайте конфиг из оверлея и поместите в эту папку")
        return
    
    # Загрузка первого найденного конфига
    config_path = config_files[0]
    print(f"\n📄 Загружаю конфиг: {config_path}")
    
    config = load_config(config_path)
    if not config:
        return
    
    # Валидация
    errors, warnings = validate_config(config)
    
    # Визуализация
    visualize_config(config)
    
    # Итоги
    print("\n" + "=" * 60)
    if errors:
        print("❌ ОШИБКИ:")
        for error in errors:
            print(f"   • {error}")
    
    if warnings:
        print("\n⚠️  ПРЕДУПРЕЖДЕНИЯ:")
        for warning in warnings:
            print(f"   • {warning}")
    
    if not errors:
        print("\n✅ Конфигурация корректна!")
        print("\n📋 Следующие шаги:")
        print("   1. Используйте этот конфиг с Live RTA:")
        print(f"      python -m coach_app.rta.live_rta --config {config_path} --mode overlay")
        print("   2. Или интегрируйте с React overlay")
        print("   3. Проверьте распознавание OCR в оверлее")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
