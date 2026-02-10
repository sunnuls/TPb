#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Детектор карт используя Roboflow API
"""
from PIL import Image, ImageDraw
import requests
import base64
from io import BytesIO

try:
    from roboflow import Roboflow
    HAS_ROBOFLOW = True
except ImportError:
    HAS_ROBOFLOW = False


class RoboflowCardDetector:
    """Детектор карт на основе Roboflow"""
    
    def __init__(self, api_key=None):
        """
        Инициализация Roboflow детектора
        
        Args:
            api_key: API ключ Roboflow
        """
        self.api_key = api_key
        self.model = None
        self.table_area = None
        self.use_inference_api = True  # Используем прямой API вместо SDK
        
        if not api_key:
            print("[WARNING] API key not provided!")
            return
        
        if not HAS_ROBOFLOW:
            print("[ERROR] Roboflow not installed! Install: pip install roboflow")
            return
        
        # Используем публичную модель через Inference API
        self.inference_url = "https://detect.roboflow.com/playing-cards-ow27d/4"
        print("[SUCCESS] Roboflow Inference API ready!")
        print(f"[INFO] URL: {self.inference_url}")
        self.model = "inference_api"  # Флаг что API готов
    
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
        
        # Fallback: центральная область
        margin_w = int(width * 0.2)
        margin_h = int(height * 0.2)
        self.table_area = (margin_w, margin_h, width - 2*margin_w, height - 2*margin_h)
        return self.table_area
    
    def detect_cards_roboflow(self, image):
        """
        Детекция карт через Roboflow Inference API
        
        Returns:
            List of detections with bounding boxes and card labels
        """
        if not self.model:
            print("[ERROR] Roboflow not initialized!")
            with open('roboflow_error.log', 'a', encoding='utf-8') as f:
                f.write("[ERROR] Roboflow not initialized!\n")
            return []
        
        try:
            # Конвертируем изображение в base64
            buffered = BytesIO()
            image.save(buffered, format="JPEG", quality=95)
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            print("[INFO] Sending image to Roboflow Inference API...")
            with open('roboflow_error.log', 'a', encoding='utf-8') as f:
                f.write(f"[INFO] Sending to: {self.inference_url}\n")
                f.write(f"[INFO] Image size: {len(img_str)} bytes\n")
            
            # Отправляем запрос к Inference API
            response = requests.post(
                self.inference_url,
                params={
                    "api_key": self.api_key,
                    "confidence": 25,  # Минимальная уверенность 25%
                    "overlap": 30
                },
                json=img_str,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"[INFO] Response status: {response.status_code}")
            with open('roboflow_error.log', 'a', encoding='utf-8') as f:
                f.write(f"[INFO] Response status: {response.status_code}\n")
                f.write(f"[INFO] Response: {response.text[:500]}\n")
            
            if response.status_code != 200:
                print(f"[ERROR] API error: {response.status_code}")
                print(f"[INFO] Response: {response.text[:200]}")
                return []
            
            result = response.json()
            predictions = result.get('predictions', [])
            
            print(f"[SUCCESS] Received predictions: {len(predictions)}")
            
            detections = []
            for pred in predictions:
                card_class = pred.get('class', '?')
                confidence = pred.get('confidence', 0)
                
                print(f"[CARD] Found: {card_class} ({confidence:.1%})")
                
                detections.append({
                    'x': int(pred['x'] - pred['width'] / 2),
                    'y': int(pred['y'] - pred['height'] / 2),
                    'w': int(pred['width']),
                    'h': int(pred['height']),
                    'class': card_class,
                    'confidence': confidence
                })
            
            return detections
            
        except requests.Timeout:
            print("[TIMEOUT] Roboflow API not responding")
            with open('roboflow_error.log', 'a', encoding='utf-8') as f:
                f.write("[TIMEOUT] Roboflow API not responding\n")
            return []
        except Exception as e:
            print(f"[ERROR] Roboflow API: {e}")
            with open('roboflow_error.log', 'a', encoding='utf-8') as f:
                f.write(f"[ERROR] {e}\n")
            import traceback
            err_trace = traceback.format_exc()
            print(err_trace[:500])
            with open('roboflow_error.log', 'a', encoding='utf-8') as f:
                f.write(err_trace + "\n")
            return []
    
    def classify_detections(self, detections):
        """Классифицирует детекции на борд и карты героя"""
        if not detections:
            return {'hero': [], 'board': []}
        
        # Сортируем по Y (сверху вниз)
        sorted_by_y = sorted(detections, key=lambda d: d['y'])
        
        # Находим границу между бордом и картами героя
        if len(sorted_by_y) >= 3:
            # Ищем самый большой разрыв по Y
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
        
        # Сортируем по X внутри каждой группы
        board_cards = sorted(board_detections, key=lambda d: d['x'])[:5]
        hero_cards = sorted(hero_detections, key=lambda d: d['x'])[:2]
        
        return {
            'hero': hero_cards,
            'board': board_cards
        }
    
    def detect_and_recognize(self, image):
        """Полный цикл детекции и распознавания"""
        # Находим область стола
        self.find_table_area(image)
        
        # Детектируем карты через Roboflow
        all_detections = self.detect_cards_roboflow(image)
        
        # Классифицируем
        classified = self.classify_detections(all_detections)
        
        # Извлекаем названия карт из class
        hero_cards = [d.get('class', '?') for d in classified['hero']]
        board_cards = [d.get('class', '?') for d in classified['board']]
        
        # Создаём debug изображение
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
        """Рисует найденные карты на изображении"""
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Область стола (красный)
        if self.table_area:
            tx, ty, tw, th = self.table_area
            draw.rectangle([tx, ty, tx + tw, ty + th], outline='red', width=4)
            draw.text((tx + 10, ty + 10), 'TABLE AREA', fill='red')
        
        # Все детекции (серый)
        for det in all_detections:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            draw.rectangle([x, y, x + w, y + h], outline='gray', width=2)
        
        # Карты героя (зеленый)
        for det in classified['hero']:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            card_class = det.get('class', '?')
            conf = det.get('confidence', 0)
            draw.rectangle([x, y, x + w, y + h], outline='lime', width=3)
            draw.text((x, y - 20), f'HERO: {card_class} ({conf:.0%})', fill='lime')
        
        # Борд (синий)
        for det in classified['board']:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            card_class = det.get('class', '?')
            conf = det.get('confidence', 0)
            draw.rectangle([x, y, x + w, y + h], outline='blue', width=3)
            draw.text((x, y - 20), f'BOARD: {card_class} ({conf:.0%})', fill='blue')
        
        return img_copy


if __name__ == '__main__':
    # Тест
    if not HAS_ROBOFLOW:
        print("❌ Roboflow не установлен!")
        print("Установите: pip install roboflow")
    else:
        print("✅ Roboflow доступен!")
        print("\nДля использования:")
        print("1. Зарегистрируйтесь на https://roboflow.com")
        print("2. Получите API ключ")
        print("3. Используйте: detector = RoboflowCardDetector(api_key='YOUR_KEY')")
