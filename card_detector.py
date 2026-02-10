#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматический детектор покерных карт
Находит карты без заданных координат
"""
import cv2
import numpy as np
from PIL import Image
import pytesseract


class CardDetector:
    """Автоматический поиск и распознавание карт"""
    
    def __init__(self):
        self.min_card_area = 2000  # Минимальная площадь карты
        self.max_card_area = 50000  # Максимальная площадь карты
        self.aspect_ratio_range = (0.5, 0.9)  # Соотношение сторон карты
        
    def find_cards(self, image):
        """
        Поиск всех карт на изображении
        
        Args:
            image: PIL Image или numpy array
            
        Returns:
            list: Список найденных карт [(x, y, w, h, contour), ...]
        """
        # Конвертируем в numpy array если это PIL Image
        if isinstance(image, Image.Image):
            img = np.array(image)
        else:
            img = image.copy()
        
        # Конвертируем в BGR для OpenCV
        if len(img.shape) == 3 and img.shape[2] == 3:
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img
        
        # Конвертируем в grayscale
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        
        # Применяем адаптивную бинаризацию
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Инвертируем для лучшего обнаружения
        binary_inv = cv2.bitwise_not(binary)
        
        # Находим контуры
        contours, _ = cv2.findContours(
            binary_inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Фильтруем контуры (ищем прямоугольные карты)
        cards = []
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            # Фильтр по площади
            if area < self.min_card_area or area > self.max_card_area:
                continue
            
            # Аппроксимируем контур
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # Карты обычно имеют 4 угла (прямоугольники)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Проверяем соотношение сторон (карты вертикальные)
                aspect_ratio = float(w) / h if h > 0 else 0
                
                if self.aspect_ratio_range[0] <= aspect_ratio <= self.aspect_ratio_range[1]:
                    cards.append({
                        'x': x,
                        'y': y,
                        'w': w,
                        'h': h,
                        'area': area,
                        'contour': contour
                    })
        
        return cards
    
    def classify_card_positions(self, cards, image_height, image_width):
        """
        Классификация карт по позициям (герой/борд)
        
        Args:
            cards: Список найденных карт
            image_height: Высота изображения
            image_width: Ширина изображения
            
        Returns:
            dict: {'hero': [], 'board': []}
        """
        if not cards:
            return {'hero': [], 'board': []}
        
        # Сортируем карты по Y-позиции
        sorted_cards = sorted(cards, key=lambda c: c['y'])
        
        # Карты героя обычно внизу (большой Y)
        # Борд в центре (средний Y)
        
        bottom_threshold = image_height * 0.6  # Нижние 40% - карты героя
        top_threshold = image_height * 0.4     # Верхние 60% - борд или оппоненты
        
        hero_cards = []
        board_cards = []
        
        for card in cards:
            card_center_y = card['y'] + card['h'] / 2
            card_center_x = card['x'] + card['w'] / 2
            
            # Карты в нижней части экрана
            if card_center_y > bottom_threshold:
                # Карты героя обычно по центру горизонтально
                if 0.3 * image_width < card_center_x < 0.7 * image_width:
                    hero_cards.append(card)
            
            # Карты в центре экрана (борд)
            elif 0.3 * image_height < card_center_y < 0.6 * image_height:
                # Борд обычно в центре
                if 0.2 * image_width < card_center_x < 0.8 * image_width:
                    board_cards.append(card)
        
        # Сортируем по X-координате (слева направо)
        hero_cards.sort(key=lambda c: c['x'])
        board_cards.sort(key=lambda c: c['x'])
        
        # Ограничиваем количество
        hero_cards = hero_cards[:2]  # Максимум 2 карты героя
        board_cards = board_cards[:5]  # Максимум 5 карт борда
        
        return {
            'hero': hero_cards,
            'board': board_cards
        }
    
    def extract_card_text(self, image, card):
        """
        Извлечение текста с карты
        
        Args:
            image: PIL Image или numpy array
            card: dict с координатами карты
            
        Returns:
            str: Распознанный текст
        """
        # Конвертируем в PIL Image если numpy
        if isinstance(image, np.ndarray):
            pil_img = Image.fromarray(image)
        else:
            pil_img = image
        
        # Вырезаем карту с небольшим отступом
        x, y, w, h = card['x'], card['y'], card['w'], card['h']
        
        # Берем только верхнюю часть карты (где ранг и масть)
        top_part_h = int(h * 0.3)  # Верхние 30% карты
        
        cropped = pil_img.crop((x, y, x + w, y + top_part_h))
        
        # Увеличиваем для лучшего OCR
        scale = 3
        new_size = (cropped.width * scale, cropped.height * scale)
        cropped_scaled = cropped.resize(new_size, Image.LANCZOS)
        
        # Конвертируем в grayscale
        gray = cropped_scaled.convert('L')
        
        # Бинаризация
        threshold = 128
        binary = gray.point(lambda x: 255 if x > threshold else 0)
        
        # OCR
        try:
            text = pytesseract.image_to_string(
                binary,
                config='--psm 6 -c tessedit_char_whitelist=AKQJT98765432♠♥♦♣shdc'
            )
            return text.strip()
        except:
            return ""
    
    def detect_and_recognize(self, image):
        """
        Полный цикл: поиск и распознавание карт
        
        Args:
            image: PIL Image
            
        Returns:
            dict: {
                'hero_cards': ['As', 'Kh'],
                'board_cards': ['Qd', '8c', '2s'],
                'all_cards': [...],
                'debug_image': annotated image
            }
        """
        # Находим все карты
        all_cards = self.find_cards(image)
        
        # Классифицируем позиции
        height, width = np.array(image).shape[:2]
        classified = self.classify_card_positions(all_cards, height, width)
        
        # Распознаем текст на картах
        hero_texts = []
        for card in classified['hero']:
            text = self.extract_card_text(image, card)
            hero_texts.append(text if text else '?')
        
        board_texts = []
        for card in classified['board']:
            text = self.extract_card_text(image, card)
            board_texts.append(text if text else '?')
        
        # Создаем debug изображение с аннотациями
        debug_img = self.annotate_image(image, classified)
        
        return {
            'hero_cards': hero_texts,
            'board_cards': board_texts,
            'all_cards': all_cards,
            'hero_positions': classified['hero'],
            'board_positions': classified['board'],
            'debug_image': debug_img
        }
    
    def annotate_image(self, image, classified):
        """Рисует найденные карты на изображении"""
        img_array = np.array(image).copy()
        
        # Рисуем карты героя (зеленый)
        for card in classified['hero']:
            x, y, w, h = card['x'], card['y'], card['w'], card['h']
            cv2.rectangle(img_array, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(img_array, 'HERO', (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Рисуем карты борда (синий)
        for card in classified['board']:
            x, y, w, h = card['x'], card['y'], card['w'], card['h']
            cv2.rectangle(img_array, (x, y), (x + w, y + h), (255, 0, 0), 3)
            cv2.putText(img_array, 'BOARD', (x, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        return Image.fromarray(img_array)


if __name__ == '__main__':
    # Тест детектора
    detector = CardDetector()
    
    # Загружаем тестовое изображение
    test_image = Image.open('test_capture_overlay.png')
    
    # Распознаем
    result = detector.detect_and_recognize(test_image)
    
    print("Карты героя:", result['hero_cards'])
    print("Борд:", result['board_cards'])
    
    # Сохраняем debug изображение
    result['debug_image'].save('cards_detected.png')
    print("Debug изображение: cards_detected.png")
