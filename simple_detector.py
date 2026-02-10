#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Простой детектор карт БЕЗ OpenCV
Только PIL и базовая обработка
"""
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import pytesseract


class SimpleCardDetector:
    """Упрощенный детектор карт без OpenCV"""
    
    def __init__(self):
        self.table_area = None  # Сохраняем найденную область стола
    
    def find_table_area(self, image):
        """
        Находит область покерного стола (зеленая зона)
        Возвращает (x, y, width, height) найденной области
        """
        width, height = image.size
        
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Ищем зеленые пиксели (покерный стол обычно зеленый/коричневый)
        # Определяем диапазоны для зеленого цвета стола
        green_ranges = [
            # Темно-зеленый
            ((20, 80, 20), (80, 150, 80)),
            # Средне-зеленый  
            ((30, 100, 30), (100, 180, 100)),
            # Коричнево-зеленый
            ((40, 70, 30), (120, 140, 80))
        ]
        
        # Проходим по изображению и ищем зеленые области
        min_x, min_y = width, height
        max_x, max_y = 0, 0
        
        # Сканируем каждый 10-й пиксель для скорости
        found_pixels = 0
        for y in range(0, height, 10):
            for x in range(0, width, 10):
                try:
                    r, g, b = image.getpixel((x, y))
                    
                    # Проверяем попадание в диапазоны зеленого
                    for (r_min, g_min, b_min), (r_max, g_max, b_max) in green_ranges:
                        if (r_min <= r <= r_max and 
                            g_min <= g <= g_max and 
                            b_min <= b <= b_max):
                            found_pixels += 1
                            min_x = min(min_x, x)
                            min_y = min(min_y, y)
                            max_x = max(max_x, x)
                            max_y = max(max_y, y)
                            break
                except:
                    continue
        
        # Если нашли достаточно зеленых пикселей
        if found_pixels > 100 and max_x > min_x and max_y > min_y:
            # Добавляем небольшой отступ
            padding = 20
            table_x = max(0, min_x - padding)
            table_y = max(0, min_y - padding)
            table_w = min(width - table_x, max_x - min_x + 2 * padding)
            table_h = min(height - table_y, max_y - min_y + 2 * padding)
            
            self.table_area = (table_x, table_y, table_w, table_h)
            return self.table_area
        
        # Если не нашли стол, используем центральную область (60% от центра)
        margin_w = int(width * 0.2)
        margin_h = int(height * 0.2)
        self.table_area = (margin_w, margin_h, width - 2*margin_w, height - 2*margin_h)
        return self.table_area
    
    def check_white_in_zone(self, image, x, y, w, h):
        """Проверяет процент белых пикселей в зоне (быстрая проверка)"""
        white_count = 0
        total = 0
        step = 3  # Проверяем каждый 3-й пиксель (было 5)
        
        for py in range(y, min(y + h, image.height), step):
            for px in range(x, min(x + w, image.width), step):
                try:
                    r, g, b = image.getpixel((px, py))
                    total += 1
                    if r > 180 and g > 180 and b > 180:  # Было 200, теперь 180 (мягче)
                        white_count += 1
                except:
                    pass
        
        return (white_count / total) if total > 0 else 0
    
    def find_cards_in_zones(self, image):
        """
        Ищет карты в предполагаемых зонах с проверкой белого цвета
        БЫСТРЫЙ и БЕЗОПАСНЫЙ метод
        """
        if self.table_area is None:
            self.find_table_area(image)
        
        table_x, table_y, table_w, table_h = self.table_area
        
        # Размеры предполагаемой карты
        card_width = int(table_w * 0.065)
        card_height = int(table_h * 0.18)
        
        regions = []
        
        # 1. БОРД - проверяем 5 позиций по горизонтали в центре
        board_y = table_y + int(table_h * 0.46)
        board_x_center = table_x + table_w // 2
        total_board_width = card_width * 5 + 15 * 4
        board_x_start = board_x_center - total_board_width // 2
        
        for i in range(5):
            x = board_x_start + i * (card_width + 15)
            
            # Проверяем есть ли белый цвет в этой зоне
            white_percent = self.check_white_in_zone(image, x, board_y, card_width, card_height)
            
            if white_percent > 0.15:  # Было 0.2, теперь 0.15 (мягче)
                regions.append({
                    'x': x,
                    'y': board_y,
                    'w': card_width,
                    'h': card_height,
                    'pixels': int(card_width * card_height * white_percent),
                    'type': 'board',
                    'index': i
                })
        
        # 2. КАРТЫ ГЕРОЯ - проверяем 2 позиции внизу
        hero_y = table_y + int(table_h * 0.68)
        hero_x_center = table_x + table_w // 2
        
        for i in range(2):
            x = hero_x_center + (i * (card_width + 10) if i == 1 else -(card_width + 10))
            
            # Проверяем есть ли белый цвет
            white_percent = self.check_white_in_zone(image, x, hero_y, card_width, card_height)
            
            if white_percent > 0.15:  # Было 0.2, теперь 0.15
                regions.append({
                    'x': x,
                    'y': hero_y,
                    'w': card_width,
                    'h': card_height,
                    'pixels': int(card_width * card_height * white_percent),
                    'type': 'hero',
                    'index': i
                })
        
        return regions
    
    
    def classify_cards(self, regions):
        """
        Классифицирует найденные карты на борд и карты героя
        """
        if not regions:
            return {'hero': [], 'board': []}
        
        hero_cards = []
        board_cards = []
        
        for region in regions:
            if region.get('type') == 'hero':
                region['label'] = f'hero_{region["index"] + 1}'
                hero_cards.append(region)
            elif region.get('type') == 'board':
                region['label'] = f'board_{region["index"] + 1}'
                board_cards.append(region)
        
        return {
            'hero': sorted(hero_cards, key=lambda r: r['index']),
            'board': sorted(board_cards, key=lambda r: r['index'])
        }
    
    def find_cards_simple(self, image):
        """
        БЫСТРЫЙ поиск карт в предполагаемых зонах
        """
        # Находим карты в предполагаемых зонах с проверкой белого цвета
        regions = self.find_cards_in_zones(image)
        
        # Сохраняем для отладки
        self.all_found_regions = regions
        self.regions_count = len(regions)
        
        # Классифицируем их на борд и карты героя
        classified = self.classify_cards(regions)
        
        return classified
    
    def extract_card_text(self, image, card):
        """Извлечение текста с карты"""
        try:
            x, y, w, h = card['x'], card['y'], card['w'], card['h']
            
            # Вырезаем область карты
            cropped = image.crop((x, y, x + w, y + h))
            
            # Берем только верхнюю левую часть (там обычно ранг и масть)
            top_h = int(h * 0.30)  # Уменьшил с 0.35 до 0.30
            top_w = int(w * 0.40)  # Берем только левую часть
            top_part = cropped.crop((0, 0, top_w, top_h))
            
            # Увеличиваем БОЛЬШЕ для лучшего OCR
            scale = 6  # Увеличил с 4 до 6
            enlarged = top_part.resize(
                (top_part.width * scale, top_part.height * scale),
                Image.LANCZOS
            )
            
            # Повышаем контраст СИЛЬНЕЕ
            enhancer = ImageEnhance.Contrast(enlarged)
            enhanced = enhancer.enhance(2.5)  # Увеличил с 2.0 до 2.5
            
            # Конвертируем в grayscale
            gray = enhanced.convert('L')
            
            # Бинаризация с адаптивным порогом
            # Попробуем два разных порога и выберем лучший результат
            results = []
            for threshold in [130, 150, 170]:
                binary = gray.point(lambda x: 255 if x > threshold else 0)
                
                # OCR с более строгим PSM (одна строка)
                text = pytesseract.image_to_string(
                    binary,
                    config='--psm 7 -c tessedit_char_whitelist=AKQJT98765432'
                )
                
                cleaned = ''.join(c for c in text if c.isalnum())
                if cleaned:
                    results.append(cleaned)
            
            # Выбираем самый частый результат или первый непустой
            if results:
                # Выбираем наиболее короткий (обычно точнее)
                best = min(results, key=len)
                return best[:2] if best else '?'
            
            return '?'
            
        except Exception as e:
            return f'?'
    
    def detect_and_recognize(self, image):
        """Полный цикл распознавания"""
        # Находим позиции карт (внутри уже вызывается find_white_regions)
        positions = self.find_cards_simple(image)
        
        # Распознаем карты героя
        hero_texts = []
        for card in positions['hero']:
            text = self.extract_card_text(image, card)
            hero_texts.append(text)
        
        # Распознаем борд
        board_texts = []
        for card in positions['board']:
            text = self.extract_card_text(image, card)
            board_texts.append(text)
        
        # Создаем debug изображение
        debug_img = self.annotate_image(image, positions)
        
        return {
            'hero_cards': hero_texts,
            'board_cards': board_texts,
            'hero_positions': positions['hero'],
            'board_positions': positions['board'],
            'debug_image': debug_img
        }
    
    def annotate_image(self, image, positions):
        """Рисует найденные зоны на изображении"""
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Рисуем область стола (красный)
        if self.table_area:
            tx, ty, tw, th = self.table_area
            draw.rectangle([tx, ty, tx + tw, ty + th], outline='red', width=4)
            draw.text((tx + 10, ty + 10), 'TABLE AREA', fill='red', font=None)
        
        # Рисуем ВСЕ найденные регионы (серый) для отладки
        if hasattr(self, 'all_found_regions'):
            for region in self.all_found_regions:
                x, y, w, h = region['x'], region['y'], region['w'], region['h']
                draw.rectangle([x, y, x + w, y + h], outline='gray', width=1)
        
        # Рисуем карты героя (зеленый)
        for card in positions['hero']:
            x, y, w, h = card['x'], card['y'], card['w'], card['h']
            draw.rectangle([x, y, x + w, y + h], outline='lime', width=3)
            draw.text((x, y - 20), 'HERO', fill='lime')
        
        # Рисуем борд (синий)
        for card in positions['board']:
            x, y, w, h = card['x'], card['y'], card['w'], card['h']
            draw.rectangle([x, y, x + w, y + h], outline='blue', width=3)
            draw.text((x, y - 20), 'BOARD', fill='blue')
        
        return img_copy


if __name__ == '__main__':
    # Тест
    detector = SimpleCardDetector()
    test_img = Image.open('test_capture_overlay.png')
    result = detector.detect_and_recognize(test_img)
    
    print("Карты героя:", result['hero_cards'])
    print("Борд:", result['board_cards'])
    
    result['debug_image'].save('cards_simple_debug.png')
    print("Сохранено: cards_simple_debug.png")
