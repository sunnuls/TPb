#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Простой детектор карт на основе компьютерного зрения (БЕЗ ML)
Использует OpenCV для поиска белых прямоугольников
"""
from PIL import Image, ImageDraw
import cv2
import numpy as np

try:
    import pytesseract
    HAS_TESSERACT = True
except:
    HAS_TESSERACT = False


class CVCardDetector:
    """Детектор карт на основе компьютерного зрения"""
    
    def __init__(self):
        """Инициализация"""
        self.table_area = None
        print("[SUCCESS] CV Card Detector ready!")
    
    def find_table_area(self, image):
        """Находит область покерного стола"""
        width, height = image.size
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Ищем зеленые пиксели
        green_ranges = [
            ((20, 80, 20), (80, 150, 80)),
            ((30, 100, 30), (100, 180, 100)),
            ((40, 70, 30), (120, 140, 80))
        ]
        
        min_x, min_y = width, height
        max_x, max_y = 0, 0
        found_pixels = 0
        
        for y in range(0, height, 10):
            for x in range(0, width, 10):
                try:
                    r, g, b = image.getpixel((x, y))
                    
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
        
        if found_pixels > 100 and max_x > min_x and max_y > min_y:
            padding = 20
            table_x = max(0, min_x - padding)
            table_y = max(0, min_y - padding)
            table_w = min(width - table_x, max_x - min_x + 2 * padding)
            table_h = min(height - table_y, max_y - min_y + 2 * padding)
            
            self.table_area = (table_x, table_y, table_w, table_h)
            return self.table_area
        
        # Fallback
        margin_w = int(width * 0.1)
        margin_h = int(height * 0.1)
        self.table_area = (margin_w, margin_h, width - 2*margin_w, height - 2*margin_h)
        return self.table_area
    
    def find_white_cards(self, image):
        """
        Находит белые прямоугольники (карты) используя OpenCV
        """
        print("[INFO] Searching for white rectangles...")
        
        # Конвертируем PIL -> OpenCV
        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Конвертируем в HSV для лучшего поиска белого
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        
        # Маска для белого цвета
        # H: 0-180, S: 0-30 (низкая насыщенность), V: 200-255 (высокая яркость)
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask = cv2.inRange(hsv, lower_white, upper_white)
        
        # Морфологические операции для очистки
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # Находим контуры
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        
        for contour in contours:
            # Получаем bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Фильтр по размеру
            if w < 30 or h < 40:
                continue
            
            # Проверяем соотношение сторон (карта обычно 2:3, т.е. 0.6-0.75)
            aspect_ratio = w / h if h > 0 else 0
            
            if 0.4 < aspect_ratio < 0.9:
                # Проверяем площадь (должна быть достаточно большой)
                area = cv2.contourArea(contour)
                bbox_area = w * h
                
                # Соотношение площади контура к bbox (карты = прямоугольники)
                if area / bbox_area > 0.7:
                    print(f"[CARD] Found at ({x}, {y}) size {w}x{h} aspect={aspect_ratio:.2f}")
                    
                    detections.append({
                        'x': x,
                        'y': y,
                        'w': w,
                        'h': h,
                        'confidence': area / bbox_area,
                        'class': 'card'
                    })
        
        print(f"[SUCCESS] Found {len(detections)} white rectangles")
        return detections
    
    def classify_detections(self, detections):
        """Классифицирует на борд и карты героя"""
        if not detections:
            return {'hero': [], 'board': []}
        
        # Сортируем по Y
        sorted_by_y = sorted(detections, key=lambda d: d['y'])
        
        if len(sorted_by_y) >= 3:
            # Ищем самый большой разрыв
            y_gaps = []
            for i in range(len(sorted_by_y) - 1):
                gap = sorted_by_y[i+1]['y'] - sorted_by_y[i]['y']
                y_gaps.append((gap, i))
            
            if y_gaps:
                max_gap_idx = max(y_gaps, key=lambda x: x[0])[1]
                board_detections = sorted_by_y[:max_gap_idx + 1]
                hero_detections = sorted_by_y[max_gap_idx + 1:]
            else:
                board_detections = sorted_by_y[:-2]
                hero_detections = sorted_by_y[-2:]
        else:
            board_detections = sorted_by_y
            hero_detections = []
        
        # Сортируем по X
        board_cards = sorted(board_detections, key=lambda d: d['x'])[:5]
        hero_cards = sorted(hero_detections, key=lambda d: d['x'])[:2]
        
        return {
            'hero': hero_cards,
            'board': board_cards
        }
    
    def recognize_card_ocr(self, image, card):
        """Распознавание карты через OCR (заглушка)"""
        return "?"
    
    def detect_and_recognize(self, image):
        """Полный цикл"""
        # Находим стол
        self.find_table_area(image)
        
        # Детектируем белые прямоугольники
        all_detections = self.find_white_cards(image)
        
        # Классифицируем
        classified = self.classify_detections(all_detections)
        
        # Распознаём
        hero_cards = [self.recognize_card_ocr(image, c) for c in classified['hero']]
        board_cards = [self.recognize_card_ocr(image, c) for c in classified['board']]
        
        # Debug изображение
        debug_img = self.annotate_image(image, classified, all_detections)
        
        return {
            'hero_cards': hero_cards,
            'board_cards': board_cards,
            'hero_positions': classified['hero'],
            'board_positions': classified['board'],
            'debug_image': debug_img,
            'all_detections': all_detections
        }
    
    def annotate_image(self, image, classified, all_detections):
        """Рисует"""
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Стол
        if self.table_area:
            tx, ty, tw, th = self.table_area
            draw.rectangle([tx, ty, tx + tw, ty + th], outline='red', width=4)
            draw.text((tx + 10, ty + 10), 'TABLE', fill='red')
        
        # Все детекции
        for det in all_detections:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            draw.rectangle([x, y, x + w, y + h], outline='gray', width=2)
        
        # Герой
        for det in classified['hero']:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            conf = det.get('confidence', 0)
            draw.rectangle([x, y, x + w, y + h], outline='lime', width=3)
            draw.text((x, y - 20), f'HERO ({conf:.0%})', fill='lime')
        
        # Борд
        for det in classified['board']:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            conf = det.get('confidence', 0)
            draw.rectangle([x, y, x + w, y + h], outline='blue', width=3)
            draw.text((x, y - 20), f'BOARD ({conf:.0%})', fill='blue')
        
        return img_copy


if __name__ == '__main__':
    print("[SUCCESS] CV Card Detector ready!")
