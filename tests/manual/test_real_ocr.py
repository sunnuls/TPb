"""
Тестирование реального OCR с настроенными зонами ROI
Использует Tesseract для распознавания карт на скриншоте
"""

import sys
from pathlib import Path as _Path
_manual_dir = _Path(__file__).resolve().parent
if str(_manual_dir) not in sys.path:
    sys.path.insert(0, str(_manual_dir))
from _root import setup_project_root
setup_project_root()

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
except (ImportError, SyntaxError, Exception):
    HAS_LIVE = False

# Если Tesseract не в PATH, укажите путь вручную (Windows):
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def load_config(config_path: str) -> dict:
    """Загрузка конфигурации зон из YAML"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

# Lazy EasyOCR reader
_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None and HAS_EASYOCR:
        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _easyocr_reader


def _preprocess_for_ocr(pil_img: Image.Image) -> list:
    """Return multiple preprocessed PIL Images for OCR robustness."""
    results = [pil_img]
    if not HAS_CV2:
        return results

    arr = np.array(pil_img)
    if len(arr.shape) == 3:
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    else:
        gray = arr

    # 1) Otsu
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(Image.fromarray(otsu))

    # 2) CLAHE + Otsu
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    cl = clahe.apply(gray)
    _, cl_otsu = cv2.threshold(cl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results.append(Image.fromarray(cl_otsu))

    # 3) Adaptive threshold
    adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    results.append(Image.fromarray(adapt))

    # 4) Inverted Otsu
    results.append(Image.fromarray(cv2.bitwise_not(otsu)))

    return results


def extract_text_from_roi(image: Image.Image, roi: dict) -> str:
    """Извлечение текста из зоны ROI.

    Multi-strategy pipeline (Phase 2 vision_fragility.md):
    1. Tesseract с multi-preprocessing (Otsu, CLAHE, Adaptive)
    2. EasyOCR fallback
    3. Голосование по результатам
    """
    x, y, w, h = roi['x'], roi['y'], roi['w'], roi['h']

    # Вырезаем зону
    cropped = image.crop((x, y, x + w, y + h))

    # Scale up for better accuracy
    scale = 2
    cropped = cropped.resize((cropped.width * scale, cropped.height * scale), Image.LANCZOS)

    candidates = []

    # Strategy 1: Tesseract with multiple preprocessings
    for variant in _preprocess_for_ocr(cropped):
        try:
            text = pytesseract.image_to_string(variant, config='--psm 10').strip()
            if text:
                candidates.append(text)
        except Exception:
            pass

    # Strategy 2: EasyOCR fallback
    reader = _get_easyocr_reader()
    if reader is not None:
        try:
            arr = np.array(cropped.convert('L'))
            results = reader.readtext(arr, detail=0)
            easyocr_text = " ".join(results).strip()
            if easyocr_text:
                candidates.append(easyocr_text)
        except Exception:
            pass

    # Voting: pick the most common non-empty result
    if candidates:
        from collections import Counter
        counter = Counter(c for c in candidates if c)
        if counter:
            return counter.most_common(1)[0][0]

    return ""


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


# ---------------------------------------------------------------------------
# Lobby OCR — Phase 1 (lobby_scanner.md)
# ---------------------------------------------------------------------------

def generate_synthetic_lobby(width: int = 1200, height: int = 700) -> Image.Image:
    """Generate a synthetic lobby screenshot for testing OCR.

    Creates a fake table list with player names, stakes, and seat counts.
    Returns a PIL Image.
    """
    if not HAS_CV2:
        # Simple PIL-only fallback
        img = Image.new('RGB', (width, height), (30, 30, 40))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            font = ImageFont.load_default()

        tables_data = [
            ("Mercury",    "$0.01/$0.02", "NL Hold'em", "6/9"),
            ("Venus",      "$0.05/$0.10", "NL Hold'em", "4/6"),
            ("Earth",      "$0.10/$0.25", "PLO",        "8/9"),
            ("Mars",       "$0.25/$0.50", "NL Hold'em", "3/6"),
            ("Jupiter",    "$0.50/$1.00", "NL Hold'em", "9/9"),
            ("Saturn",     "$1/$2",       "NL Hold'em", "5/9"),
            ("Uranus",     "$2/$5",       "PLO",        "2/6"),
            ("Neptune",    "$5/$10",      "NL Hold'em", "7/9"),
        ]

        # Header
        draw.text((20, 10), "Table Name      Stakes        Game         Players", fill=(200, 200, 200), font=font)
        draw.line([(10, 35), (width - 10, 35)], fill=(80, 80, 80), width=1)

        y = 45
        row_h = int((height - 60) / len(tables_data))
        for name, stakes, game, players in tables_data:
            line = f"{name:16s}{stakes:14s}{game:13s}{players}"
            draw.text((20, y + 5), line, fill=(220, 220, 220), font=font)
            draw.line([(10, y + row_h - 2), (width - 10, y + row_h - 2)], fill=(50, 50, 50), width=1)
            y += row_h

        return img

    # OpenCV version — sharper text rendering
    img = np.full((height, width, 3), (40, 30, 30), dtype=np.uint8)

    tables_data = [
        ("Mercury",    "$0.01/$0.02", "NL Hold'em", "6/9"),
        ("Venus",      "$0.05/$0.10", "NL Hold'em", "4/6"),
        ("Earth",      "$0.10/$0.25", "PLO",        "8/9"),
        ("Mars",       "$0.25/$0.50", "NL Hold'em", "3/6"),
        ("Jupiter",    "$0.50/$1.00", "NL Hold'em", "9/9"),
        ("Saturn",     "$1/$2",       "NL Hold'em", "5/9"),
        ("Uranus",     "$2/$5",       "PLO",        "2/6"),
        ("Neptune",    "$5/$10",      "NL Hold'em", "7/9"),
    ]

    # Header
    header = "Table Name        Stakes          Game           Players"
    cv2.putText(img, header, (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
    cv2.line(img, (10, 38), (width - 10, 38), (80, 80, 80), 1)

    row_h = (height - 55) // len(tables_data)
    y = 50
    for name, stakes, game, players in tables_data:
        line = f"{name:18s}{stakes:16s}{game:15s}{players}"
        cv2.putText(img, line, (15, y + row_h // 2 + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.50, (220, 220, 220), 1)
        cv2.line(img, (10, y + row_h - 1), (width - 10, y + row_h - 1), (50, 50, 50), 1)
        y += row_h

    # Convert BGR → RGB PIL
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def test_lobby_ocr(screenshot_path: str | None = None):
    """Test lobby OCR — scan an actual or synthetic lobby screenshot.

    Phase 1 of lobby_scanner.md: recognise players/seats in the lobby.
    """
    from live_capture import LobbyCaptureScanner, LobbyScanResult

    print("=" * 60)
    print("  LOBBY OCR TEST")
    print("=" * 60)

    if screenshot_path and Path(screenshot_path).exists():
        print(f"\n  Screenshot: {screenshot_path}")
        image = Image.open(screenshot_path)
    else:
        print("\n  Using synthetic lobby image")
        image = generate_synthetic_lobby()
        image.save("lobby_synthetic_test.png")
        print("  Saved: lobby_synthetic_test.png")

    scanner = LobbyCaptureScanner()
    result: LobbyScanResult = scanner.scan_image(image)

    print(f"\n  Rows detected: {result.total_rows_detected}")
    print(f"  Tables parsed: {result.table_count}")
    print(f"  OCR confidence: {result.ocr_confidence:.0%}")
    print(f"  Elapsed: {result.elapsed_ms:.0f} ms")

    if result.error:
        print(f"\n  ERROR: {result.error}")

    if result.tables:
        print(f"\n  {'Table':20s} {'Stakes':14s} {'Seats':8s} {'Game'}")
        print("  " + "-" * 55)
        for t in result.tables:
            seats = f"{t.players}/{t.max_players}" if t.max_players else str(t.players)
            print(f"  {t.name:20s} {t.stakes:14s} {seats:8s} {t.game_type}")
    else:
        print("\n  No tables found")

    avail = result.available_tables(min_seats=1)
    print(f"\n  Available tables (>= 1 seat free): {len(avail)}")

    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='OCR тест, Live-режим и Lobby сканер')
    parser.add_argument('screenshot', nargs='?', help='Путь к скриншоту (для теста)')
    parser.add_argument('config', nargs='?', default='stol/poker_table_config (1).yaml', help='Путь к конфигу')
    parser.add_argument('--live', action='store_true', help='Live-режим с захватом окна')
    parser.add_argument('--lobby', action='store_true',
                        help='Lobby OCR test — распознавание таблиц лобби')
    parser.add_argument('--interval', type=float, default=3.0, help='Интервал обновления (сек)')
    
    args = parser.parse_args()
    
    # Lobby OCR test
    if args.lobby:
        test_lobby_ocr(args.screenshot)

    # Live-режим
    elif args.live:
        if not HAS_LIVE:
            print("Для live-режима установите:")
            print("   pip install pygetwindow mss")
            sys.exit(1)
        
        if not Path(args.config).exists():
            print(f"Конфиг не найден: {args.config}")
            sys.exit(1)
        
        live_mode(args.config, args.interval)
    
    # Обычный тест OCR
    else:
        screenshot_path = args.screenshot or 'screenshot_test.png'
        config_path = args.config
        
        if not Path(screenshot_path).exists():
            print(f"Скриншот не найден: {screenshot_path}")
            print(f"\n  Использование:")
            print(f"   Тест: python tests/manual/test_real_ocr.py <скриншот> <конфиг>")
            print(f"   Live: python tests/manual/test_real_ocr.py --live --config <конфиг>")
            print(f"   Lobby: python tests/manual/test_real_ocr.py --lobby [скриншот]")
            sys.exit(1)
        
        if not Path(config_path).exists():
            print(f"Конфиг не найден: {config_path}")
            sys.exit(1)
        
        try:
            test_ocr_on_screenshot(screenshot_path, config_path)
        except Exception as e:
            print(f"\nОШИБКА: {e}")
            import traceback
            traceback.print_exc()
