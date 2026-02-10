"""
Тестирование реального OCR с настроенными зонами ROI
Использует Tesseract для распознавания карт на скриншоте
"""
import sys
import os
import time
import yaml
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pytesseract

# Исправление кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Опционально: поиск окна
try:
    import pygetwindow as gw
    import mss
    HAS_LIVE = True
except ImportError:
    HAS_LIVE = False

# Если Tesseract не в PATH, укажите путь вручную (Windows):
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def load_config(config_path: str) -> dict:
    """Загрузка конфигурации зон из YAML"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_text_from_roi(image: Image.Image, roi: dict) -> str:
    """Извлечение текста из зоны ROI"""
    x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']
    
    # Вырезаем зону
    cropped = image.crop((x, y, x + w, y + h))
    
    # Сохраняем для отладки
    # cropped.save(f'debug_roi_{x}_{y}.png')
    
    # Распознаем текст
    text = pytesseract.image_to_string(cropped, config='--psm 10')
    return text.strip()


def visualize_zones(image: Image.Image, rois: dict, output_path: str = 'zones_visualization.png'):
    """Визуализация настроенных зон на изображении"""
    img_copy = image.copy()
    draw = ImageDraw.Draw(img_copy)
    
    # Пытаемся загрузить шрифт
    try:
        font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
    
    colors = {
        'hero_card_1': 'lime',
        'hero_card_2': 'lime',
        'board_card_1': 'yellow',
        'board_card_2': 'yellow',
        'board_card_3': 'yellow',
        'board_card_4': 'orange',
        'board_card_5': 'red',
        'pot': 'cyan',
        'hero_stack': 'green',
        'opponent': 'blue'
    }
    
    for zone_name, zone in rois.items():
        x, y, w, h = zone['x'], zone['y'], zone['w'], zone['h']
        
        # Определяем цвет
        color = 'white'
        for key, col in colors.items():
            if key in zone_name:
                color = col
                break
        
        # Рисуем прямоугольник
        draw.rectangle([x, y, x + w, y + h], outline=color, width=3)
        
        # Рисуем название зоны
        draw.text((x, y - 20), zone_name, fill=color, font=font)
    
    img_copy.save(output_path)
    print(f"✅ Визуализация сохранена: {output_path}")
    return img_copy


def test_ocr_on_screenshot(screenshot_path: str, config_path: str):
    """Основная функция тестирования OCR"""
    print("=" * 60)
    print("🎴 ТЕСТ РЕАЛЬНОГО OCR РАСПОЗНАВАНИЯ")
    print("=" * 60)
    
    # Загружаем конфиг
    print(f"\n📄 Загрузка конфигурации: {config_path}")
    config = load_config(config_path)
    rois = config.get('rois', {})
    
    if not rois:
        print("❌ Ошибка: В конфиге нет зон ROI!")
        return
    
    print(f"✅ Загружено зон: {len(rois)}")
    for zone_name in rois.keys():
        print(f"   • {zone_name}")
    
    # Загружаем скриншот
    print(f"\n🖼️ Загрузка скриншота: {screenshot_path}")
    try:
        image = Image.open(screenshot_path)
        print(f"✅ Размер изображения: {image.size}")
    except Exception as e:
        print(f"❌ Ошибка загрузки изображения: {e}")
        return
    
    # Визуализируем зоны
    print(f"\n🎨 Создание визуализации зон...")
    visualize_zones(image, rois)
    
    # Распознаем карты героя
    print("\n" + "=" * 60)
    print("🃏 КАРТЫ ГЕРОЯ")
    print("=" * 60)
    
    hero_cards = []
    for i in [1, 2]:
        zone_name = f'hero_card_{i}'
        if zone_name in rois:
            text = extract_text_from_roi(image, rois[zone_name])
            hero_cards.append(text)
            print(f"{zone_name}: '{text}'")
        else:
            print(f"{zone_name}: НЕ НАЙДЕНА В КОНФИГЕ")
    
    # Распознаем борд
    print("\n" + "=" * 60)
    print("🎴 БОРД (ОБЩИЕ КАРТЫ)")
    print("=" * 60)
    
    board_cards = []
    for i in [1, 2, 3, 4, 5]:
        zone_name = f'board_card_{i}'
        if zone_name in rois:
            text = extract_text_from_roi(image, rois[zone_name])
            board_cards.append(text)
            card_names = ['ФЛОП #1', 'ФЛОП #2', 'ФЛОП #3', 'ТЕРН', 'РИВЕР']
            print(f"{card_names[i-1]} ({zone_name}): '{text}'")
        else:
            print(f"{zone_name}: НЕ НАЙДЕНА В КОНФИГЕ")
    
    # Распознаем банк
    print("\n" + "=" * 60)
    print("💰 БАНК И СТЕКИ")
    print("=" * 60)
    
    if 'pot' in rois:
        pot_text = extract_text_from_roi(image, rois['pot'])
        print(f"Банк: '{pot_text}'")
    else:
        print("Банк: НЕ НАСТРОЕН")
    
    if 'hero_stack' in rois:
        stack_text = extract_text_from_roi(image, rois['hero_stack'])
        print(f"Стек героя: '{stack_text}'")
    else:
        print("Стек героя: НЕ НАСТРОЕН")
    
    # Распознаем оппонентов
    print("\n" + "=" * 60)
    print("👥 ОППОНЕНТЫ")
    print("=" * 60)
    
    for i in range(1, 6):
        zone_name = f'opponent_{i}'
        if zone_name in rois:
            opp_text = extract_text_from_roi(image, rois[zone_name])
            print(f"Оппонент #{i}: '{opp_text}'")
    
    print("\n" + "=" * 60)
    print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)
    print("\n💡 СОВЕТЫ ПО УЛУЧШЕНИЮ РАСПОЗНАВАНИЯ:")
    print("   1. Убедитесь, что зоны точно захватывают карты")
    print("   2. Используйте скриншоты с высоким разрешением")
    print("   3. Проверьте, что текст карт читаемый и контрастный")
    print("   4. Настройте Tesseract параметры для лучшей точности")
    print("\n📁 Проверьте файл: zones_visualization.png")
    print("   Убедитесь, что зоны правильно расположены!\n")


def find_poker_window():
    """Поиск окна покер-клиента"""
    if not HAS_LIVE:
        return None
    
    keywords = ['PokerStars', 'GGPoker', 'PartyPoker', 'Poker', 'Hold', 'Texas']
    all_windows = gw.getAllTitles()
    
    for title in all_windows:
        if not title.strip():
            continue
        for keyword in keywords:
            if keyword.lower() in title.lower():
                try:
                    windows = gw.getWindowsWithTitle(title)
                    if windows:
                        w = windows[0]
                        if w.width > 300 and w.height > 300:
                            print(f"✅ Найдено окно: {title}")
                            print(f"   Размер: {w.width}x{w.height}")
                            return w
                except:
                    pass
    return None


def capture_window(window):
    """Захват окна покер-клиента"""
    if not HAS_LIVE:
        return None
    
    try:
        with mss.mss() as sct:
            monitor = {
                "top": window.top,
                "left": window.left,
                "width": window.width,
                "height": window.height
            }
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img
    except:
        return None


def live_mode(config_path, interval=3):
    """Live-режим с автоматическим захватом окна"""
    print("=" * 60)
    print("🎴 LIVE POKER ASSISTANT")
    print("=" * 60)
    print("\n📡 Поиск окна покер-клиента...\n")
    
    window = find_poker_window()
    if not window:
        print("❌ Окно не найдено! Откройте покер-клиент.")
        return
    
    print(f"\n⏱️  Обновление каждые {interval} сек")
    print("⏸️  Нажмите Ctrl+C для остановки\n")
    
    config = load_config(config_path)
    rois = config.get('rois', {})
    
    count = 0
    try:
        while True:
            img = capture_window(window)
            if not img:
                print("⚠️ Ошибка захвата. Переподключение...")
                window = find_poker_window()
                time.sleep(1)
                continue
            
            count += 1
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print("=" * 60)
            print(f"🎴 LIVE POKER ASSISTANT - Кадр #{count}")
            print("=" * 60)
            
            # Карты героя
            print("\n🃏 ВАШИ КАРТЫ:")
            hero_cards = []
            for i in [1, 2]:
                key = f'hero_card_{i}'
                if key in rois:
                    text = extract_text_from_roi(img, rois[key])
                    hero_cards.append(text if text else '?')
            print(f"   {' '.join(hero_cards) if hero_cards else '[не распознаны]'}")
            
            # Борд
            print("\n🎴 БОРД:")
            board = []
            for i in [1, 2, 3, 4, 5]:
                key = f'board_card_{i}'
                if key in rois:
                    text = extract_text_from_roi(img, rois[key])
                    board.append(text if text else '?')
            print(f"   {' '.join(board) if board else '[не распознан]'}")
            
            # Банк и стек
            print(f"\n💰 БАНК: ", end='')
            if 'pot' in rois:
                pot = extract_text_from_roi(img, rois['pot'])
                print(pot if pot else '[не распознан]')
            else:
                print('[не настроен]')
            
            print(f"💵 СТЕК: ", end='')
            if 'hero_stack' in rois:
                stack = extract_text_from_roi(img, rois['hero_stack'])
                print(stack if stack else '[не распознан]')
            else:
                print('[не настроен]')
            
            print("\n" + "=" * 60)
            print("⏸️  Ctrl+C для остановки")
            print("=" * 60)
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Остановка...\n")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='OCR тест и Live-режим')
    parser.add_argument('screenshot', nargs='?', help='Путь к скриншоту (для теста)')
    parser.add_argument('config', nargs='?', default='stol/poker_table_config (1).yaml', help='Путь к конфигу')
    parser.add_argument('--live', action='store_true', help='Live-режим с захватом окна')
    parser.add_argument('--interval', type=float, default=3.0, help='Интервал обновления (сек)')
    
    args = parser.parse_args()
    
    # Live-режим
    if args.live:
        if not HAS_LIVE:
            print("❌ Для live-режима установите:")
            print("   pip install pygetwindow mss")
            sys.exit(1)
        
        if not Path(args.config).exists():
            print(f"❌ Конфиг не найден: {args.config}")
            sys.exit(1)
        
        live_mode(args.config, args.interval)
    
    # Обычный тест OCR
    else:
        screenshot_path = args.screenshot or 'screenshot_test.png'
        config_path = args.config
        
        if not Path(screenshot_path).exists():
            print(f"❌ Скриншот не найден: {screenshot_path}")
            print(f"\n💡 Использование:")
            print(f"   Тест: python test_real_ocr.py <скриншот> <конфиг>")
            print(f"   Live: python test_real_ocr.py --live --config <конфиг>")
            sys.exit(1)
        
        if not Path(config_path).exists():
            print(f"❌ Конфиг не найден: {config_path}")
            sys.exit(1)
        
        try:
            test_ocr_on_screenshot(screenshot_path, config_path)
        except Exception as e:
            print(f"\n❌ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
