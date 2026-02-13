#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
YOLOv8 детектор карт - ЛОКАЛЬНО без интернета.

Phase 2 (vision_fragility.md) — расширен:
- Multi-template fallback когда YOLO недоступен или не нашёл карты
- Реальный OCR вместо заглушки в recognize_card_ocr()
- Pytesseract + EasyOCR fallback pipeline
- Colour-based suit detection

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
import logging
from PIL import Image, ImageDraw
import numpy as np

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except (ImportError, OSError):
    HAS_YOLO = False
    YOLO = None

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

logger = logging.getLogger(__name__)


class YoloCardDetector:
    """Детектор карт на основе YOLOv8 (локально)"""
    
    def __init__(self):
        """Инициализация YOLOv8"""
        self.model = None
        self.table_area = None
        
        if not HAS_YOLO:
            print("[ERROR] YOLO not installed! Install: pip install ultralytics")
            return
        
        try:
            print("[INFO] Loading YOLOv8 model trained on playing cards...")
            
            # СНАЧАЛА проверяем локальные модели (быстрее!)
            import os
            local_models = [
                "yolov8s_playing_cards.pt",  # Обученная модель от Playing-Cards-Detection
                "weights/best.pt",  # Может быть обученная модель!
                "weights/yolov8s_playing_cards.pt",
                "Playing-Cards-Detection-master/Playing-Cards-Detection-master/yolov8s_playing_cards.pt",
                "weights/train-yolov8-object-detection-on-custom-dataset.pt",
                "playing_cards.pt",
                "cards_yolov8.pt",
                "weights/playing_cards.pt"
            ]
            
            model_loaded = False
            for model_path in local_models:
                if os.path.exists(model_path):
                    print(f"[INFO] Found local model: {model_path}")
                    try:
                        self.model = YOLO(model_path)
                        print("[SUCCESS] Local card model loaded!")
                        self.is_pretrained = True
                        model_loaded = True
                        break
                    except Exception as e:
                        print(f"[WARNING] Could not load {model_path}: {e}")
                        continue
            
            # Если локальных нет - загружаем базовую модель
            if not model_loaded:
                print("[WARNING] No pre-trained card model found locally!")
                print("[INFO] Loading base YOLOv8-small with card filters...")
                self.model = YOLO('yolov8s.pt')  # Базовая модель
                print("[SUCCESS] Base YOLOv8-small loaded (will filter by shape/color)")
                self.is_pretrained = False
            
        except Exception as e:
            print(f"[ERROR] Failed to load YOLO: {e}")
            self.model = None
    
    def find_table_area(self, image):
        """Находит область покерного стола"""
        width, height = image.size
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Ищем зеленые пиксели (покерный стол)
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
        margin_w = int(width * 0.1)
        margin_h = int(height * 0.1)
        self.table_area = (margin_w, margin_h, width - 2*margin_w, height - 2*margin_h)
        return self.table_area
    
    def detect_white_rectangles(self, image):
        """
        AI детекция карт - ЧИСТЫЙ ИИ без фильтров!
        Модель обучена на картах, она ЗНАЕТ что это карта!
        """
        if not self.model:
            print("[ERROR] YOLO model not loaded!")
            return []
        
        try:
            print("[INFO] Running AI inference (pure neural network)...")
            
            # Если это обученная модель - используем высокий порог
            # Если базовая - ОЧЕНЬ низкий порог (ищем ВСЕ)
            if hasattr(self, 'is_pretrained') and self.is_pretrained:
                # ОБУЧЕННАЯ МОДЕЛЬ - ОЧЕНЬ НИЗКИЙ порог для онлайн-покера!
                # Онлайн-карты (3D рендер) сильно отличаются от физических карт из датасета
                results = self.model(image, conf=0.01, iou=0.3, imgsz=640, verbose=True)
                print("[INFO] Using pre-trained model with VERY LOW threshold (0.01) for online poker")
            else:
                # Базовая модель - максимальная агрессивность!
                results = self.model(image, conf=0.001, iou=0.3, verbose=False)
                print("[INFO] Using base YOLO (AGGRESSIVE MODE - finding ALL objects)")
            
            detections = []
            
            # Обрабатываем результаты
            for result in results:
                boxes = result.boxes
                print(f"[INFO] AI found {len(boxes)} total objects")
                
                for box in boxes:
                    # Координаты
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    
                    # Размеры
                    w = x2 - x1
                    h = y2 - y1
                    
                    aspect_ratio = w / h if h > 0 else 0
                    
                    # Логируем
                    class_name = self.model.names[cls] if hasattr(self.model, 'names') else f"class_{cls}"
                    print(f"[AI] Detected '{class_name}' at ({int(x1)}, {int(y1)}) size {int(w)}x{int(h)} conf={conf:.2f}")
                    
                    # Если это ОБУЧЕННАЯ модель на картах - принимаем ВСЁ что нашла!
                    if hasattr(self, 'is_pretrained') and self.is_pretrained:
                        # ИИ знает что это карта - доверяем ему!
                        detections.append({
                            'x': int(x1),
                            'y': int(y1),
                            'w': int(w),
                            'h': int(h),
                            'confidence': conf,
                            'class': class_name
                        })
                    else:
                        # Базовая модель - МЯГКИЕ фильтры (карты бывают разные!)
                        # Принимаем любые прямоугольники с разумным соотношением сторон
                        if 0.4 < aspect_ratio < 1.0 and w > 20 and h > 25 and w < 300 and h < 400:
                            print(f"[CARD] Card-like object (AR={aspect_ratio:.2f})")
                            detections.append({
                                'x': int(x1),
                                'y': int(y1),
                                'w': int(w),
                                'h': int(h),
                                'confidence': conf,
                                'class': 'card'
                            })
                        else:
                            print(f"[SKIP] Rejected: AR={aspect_ratio:.2f}, size={int(w)}x{int(h)}")
            
            print(f"[SUCCESS] AI found {len(detections)} cards")
            return detections
            
        except Exception as e:
            print(f"[ERROR] YOLO detection failed: {e}")
            import traceback
            print(traceback.format_exc()[:300])
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
    
    def recognize_card_ocr(self, image, card):
        """
        Распознавание ранга + масти карты через multi-strategy pipeline:

        1. Multi-preprocessing Tesseract OCR
        2. EasyOCR fallback
        3. Colour-based suit detection

        Args:
            image: PIL Image
            card: dict с x, y, w, h

        Returns:
            str: e.g. "Ah", "Ks", "?" если не распознано
        """
        if not HAS_CV2:
            return "?"

        try:
            img_arr = np.array(image)
            if len(img_arr.shape) == 3 and img_arr.shape[2] == 3:
                img_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
            else:
                img_bgr = img_arr

            x, y, w, h = card['x'], card['y'], card['w'], card['h']

            # Top 35% of card (rank + suit area)
            top_h = max(1, int(h * 0.35))
            roi = img_bgr[y:y + top_h, x:x + w]
            if roi.size == 0:
                return "?"

            # Scale up
            scale = 3
            roi = cv2.resize(roi, (w * scale, top_h * scale), interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            rank = None

            # Strategy 1: Tesseract multi-preprocessing
            if HAS_TESSERACT:
                for preprocess in self._preprocess_variants(gray):
                    try:
                        text = pytesseract.image_to_string(
                            preprocess,
                            config='--psm 10 -c tessedit_char_whitelist=AKQJT98765432',
                        ).strip().upper()
                        rank = self._normalise_rank(text)
                        if rank:
                            break
                    except Exception:
                        continue

            # Strategy 2: EasyOCR fallback
            if not rank and HAS_EASYOCR:
                try:
                    if not hasattr(self, '_easyocr_reader'):
                        self._easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                    results = self._easyocr_reader.readtext(
                        gray, detail=0, allowlist="AKQJT9876543210",
                    )
                    raw = "".join(results).strip().upper()
                    rank = self._normalise_rank(raw)
                except Exception:
                    pass

            # Suit detection by colour
            suit = self._detect_suit_color(roi)

            if rank:
                return rank + (suit if suit else "")
            return "?"
        except Exception as e:
            logger.debug("recognize_card_ocr failed: %s", e)
            return "?"

    # ---- OCR helpers ----

    @staticmethod
    def _preprocess_variants(gray):
        """Return multiple preprocessed versions for OCR robustness."""
        variants = []
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(otsu)
        adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        variants.append(adapt)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
        cl = clahe.apply(gray)
        _, cl_otsu = cv2.threshold(cl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        variants.append(cl_otsu)
        variants.append(cv2.bitwise_not(otsu))
        return variants

    @staticmethod
    def _normalise_rank(raw):
        """Normalise OCR output to single-char rank or None."""
        aliases = {"10": "T", "1": "A", "0": "T"}
        raw = raw.strip().upper()
        if raw in aliases:
            return aliases[raw]
        if raw and raw[0] in "AKQJT98765432":
            return raw[0]
        return None

    @staticmethod
    def _detect_suit_color(roi_bgr):
        """Detect suit by dominant colour."""
        hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
        total = roi_bgr.shape[0] * roi_bgr.shape[1]
        if total == 0:
            return None

        # Red → hearts
        red_mask = cv2.inRange(hsv, np.array([0, 70, 70]), np.array([15, 255, 255]))
        red_mask |= cv2.inRange(hsv, np.array([160, 70, 70]), np.array([180, 255, 255]))
        if cv2.countNonZero(red_mask) / total > 0.05:
            return "h"

        # Blue → diamonds (some skins)
        blue_mask = cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255]))
        if cv2.countNonZero(blue_mask) / total > 0.05:
            return "d"

        # Green → clubs (some skins)
        green_mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
        if cv2.countNonZero(green_mask) / total > 0.05:
            return "c"

        # Default: spades (black)
        return "s"

    # ---- Template-based fallback ----

    def detect_cards_template_fallback(self, image):
        """
        Fallback card detection using CV contours + template matching.

        Used when YOLO model is unavailable or finds nothing.

        Args:
            image: PIL Image

        Returns:
            list of detection dicts
        """
        if not HAS_CV2:
            return []

        img_arr = np.array(image)
        if len(img_arr.shape) == 3 and img_arr.shape[2] == 3:
            img_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_arr

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        h_img, w_img = gray.shape[:2]

        # Multi-threshold card detection
        detections = []
        for thresh_val in (170, 180, 190, 200):
            _, binary = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w < 20 or h < 25 or w > w_img * 0.12 or h > h_img * 0.18:
                    continue
                ratio = h / w if w > 0 else 0
                if not (1.1 < ratio < 1.8):
                    continue
                area = cv2.contourArea(cnt)
                fill = area / (w * h) if w * h > 0 else 0
                if fill < 0.65:
                    continue

                # Check not already found (dedup by overlap)
                duplicate = False
                for d in detections:
                    if abs(d['x'] - x) < 10 and abs(d['y'] - y) < 10:
                        duplicate = True
                        break
                if not duplicate:
                    detections.append({
                        'x': x, 'y': y, 'w': w, 'h': h,
                        'confidence': round(fill, 2),
                        'class': 'card_template',
                    })

        logger.info("Template fallback found %d card-like regions", len(detections))
        return detections

    def detect_and_recognize(self, image):
        """Полный цикл детекции и распознавания.

        Pipeline:
        1. YOLO detection (if available)
        2. Template fallback (if YOLO finds nothing)
        3. Multi-strategy OCR for rank/suit
        """
        # Находим область стола
        self.find_table_area(image)
        
        # Детектируем YOLO
        all_detections = self.detect_white_rectangles(image)

        # Fallback: template-based detection if YOLO found nothing
        if not all_detections:
            logger.info("YOLO found nothing — using template fallback")
            all_detections = self.detect_cards_template_fallback(image)

        # Классифицируем
        classified = self.classify_detections(all_detections)
        
        # Распознаём через OCR pipeline
        hero_cards = [self.recognize_card_ocr(image, c) for c in classified['hero']]
        board_cards = [self.recognize_card_ocr(image, c) for c in classified['board']]
        
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
            conf = det.get('confidence', 0)
            draw.rectangle([x, y, x + w, y + h], outline='lime', width=3)
            draw.text((x, y - 20), f'HERO ({conf:.0%})', fill='lime')
        
        # Борд (синий)
        for det in classified['board']:
            x, y, w, h = det['x'], det['y'], det['w'], det['h']
            conf = det.get('confidence', 0)
            draw.rectangle([x, y, x + w, y + h], outline='blue', width=3)
            draw.text((x, y - 20), f'BOARD ({conf:.0%})', fill='blue')
        
        return img_copy


if __name__ == '__main__':
    # Тест
    if not HAS_YOLO:
        print("[ERROR] YOLO not installed!")
        print("Install: pip install ultralytics")
    else:
        print("[SUCCESS] YOLOv8 detector ready!")
        detector = YoloCardDetector()
        
        if detector.model:
            print("[INFO] Model loaded successfully!")
            print("[INFO] Ready for card detection!")
