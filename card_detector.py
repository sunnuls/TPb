#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматический детектор покерных карт.

Phase 2 (vision_fragility.md) — расширен multi-template matching
и EasyOCR fallback для распознавания рангов/мастей.

Находит карты без заданных координат, распознаёт ранг и масть
через цепочку: Template → Tesseract → EasyOCR → fallback.

⚠️ EDUCATIONAL RESEARCH ONLY.
"""
from __future__ import annotations

import logging
import cv2
import numpy as np
from PIL import Image

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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RANKS = list("A23456789") + ["T", "J", "Q", "K"]
RANK_ALIASES = {"10": "T", "1": "A", "0": "T"}
SUITS = {"s": "♠", "h": "♥", "d": "♦", "c": "♣"}
SUIT_FROM_SYMBOL = {v: k for k, v in SUITS.items()}

# Suit colour ranges in HSV for colour-based suit detection
SUIT_HSV_RANGES = {
    "h": [(np.array([0, 70, 70]), np.array([15, 255, 255])),
          (np.array([160, 70, 70]), np.array([180, 255, 255]))],   # red
    "d": [(np.array([100, 50, 50]), np.array([130, 255, 255]))],   # blue (some skins)
    "s": [],   # black — detected by low saturation
    "c": [(np.array([35, 40, 40]), np.array([85, 255, 255]))],     # green (some skins)
}


# ---------------------------------------------------------------------------
# CardTemplateBank — synthetic rank/suit templates for matchTemplate
# ---------------------------------------------------------------------------

class CardTemplateBank:
    """Generates and stores synthetic rank & suit templates."""

    def __init__(self):
        self.rank_templates: dict = {}   # rank → list[np.ndarray grayscale]
        self.generated = False

    def generate(
        self,
        font_scales=(0.7, 0.9, 1.1),
        thicknesses=(1, 2),
        sizes=((28, 36), (22, 28)),
        bg_vals=(255, 240),
        fg_vals=(0, 30),
    ):
        """Generate synthetic templates for every rank."""
        for rank in RANKS:
            display = "10" if rank == "T" else rank
            templates = []
            for fs in font_scales:
                for thick in thicknesses:
                    for (tw, th) in sizes:
                        for bg in bg_vals:
                            for fg in fg_vals:
                                img = np.full((th, tw), bg, dtype=np.uint8)
                                (ttw, tth), _ = cv2.getTextSize(
                                    display, cv2.FONT_HERSHEY_SIMPLEX, fs, thick,
                                )
                                tx = max(0, (tw - ttw) // 2)
                                ty = max(tth, (th + tth) // 2)
                                cv2.putText(
                                    img, display, (tx, ty),
                                    cv2.FONT_HERSHEY_SIMPLEX, fs, fg, thick, cv2.LINE_AA,
                                )
                                templates.append(img)
            self.rank_templates[rank] = templates
        self.generated = True
        logger.debug("CardTemplateBank: generated %d rank templates",
                     sum(len(v) for v in self.rank_templates.values()))

    def match_rank(self, roi_gray: np.ndarray, scales=(0.8, 1.0, 1.2)) -> tuple:
        """Match *roi_gray* against all rank templates.

        Returns (best_rank, confidence) or (None, 0).
        """
        if not self.generated:
            self.generate()

        best_rank = None
        best_score = 0.0

        for rank, templates in self.rank_templates.items():
            for tpl in templates:
                for sc in scales:
                    tw = max(5, int(tpl.shape[1] * sc))
                    th = max(5, int(tpl.shape[0] * sc))
                    if tw >= roi_gray.shape[1] or th >= roi_gray.shape[0]:
                        continue
                    resized = cv2.resize(tpl, (tw, th), interpolation=cv2.INTER_AREA)
                    result = cv2.matchTemplate(roi_gray, resized, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(result)
                    if max_val > best_score:
                        best_score = max_val
                        best_rank = rank

        if best_score >= 0.45:
            return best_rank, round(best_score, 3)
        return None, 0.0


# Singleton template bank (lazy init)
_card_template_bank: CardTemplateBank | None = None


def _get_card_template_bank() -> CardTemplateBank:
    global _card_template_bank
    if _card_template_bank is None:
        _card_template_bank = CardTemplateBank()
        _card_template_bank.generate()
    return _card_template_bank


# ---------------------------------------------------------------------------
# Multi-strategy OCR helpers
# ---------------------------------------------------------------------------

def _preprocess_variants(gray: np.ndarray) -> list:
    """Return multiple preprocessed versions for OCR robustness."""
    variants = []
    # 1) Simple binary (Otsu)
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(otsu)
    # 2) Adaptive threshold
    adapt = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    variants.append(adapt)
    # 3) CLAHE + Otsu
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(4, 4))
    cl = clahe.apply(gray)
    _, cl_otsu = cv2.threshold(cl, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(cl_otsu)
    # 4) Inverted
    variants.append(cv2.bitwise_not(otsu))
    return variants


def _tesseract_ocr(img: np.ndarray, whitelist: str = "AKQJT98765432") -> str:
    """Run Tesseract on a preprocessed grayscale image."""
    if not HAS_TESSERACT:
        return ""
    try:
        text = pytesseract.image_to_string(
            img,
            config=f'--psm 10 -c tessedit_char_whitelist={whitelist}',
        )
        return text.strip()
    except Exception:
        return ""


def _easyocr_ocr(img: np.ndarray) -> str:
    """Run EasyOCR on a grayscale image (lazy reader init)."""
    if not HAS_EASYOCR:
        return ""
    try:
        if not hasattr(_easyocr_ocr, "_reader"):
            _easyocr_ocr._reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        results = _easyocr_ocr._reader.readtext(img, detail=0, allowlist="AKQJT9876543210")
        return "".join(results).strip()
    except Exception:
        return ""


def _normalise_rank(raw: str) -> str | None:
    """Normalise OCR output to a single-char rank or None."""
    raw = raw.strip().upper()
    if raw in RANK_ALIASES:
        return RANK_ALIASES[raw]
    if raw and raw[0] in "AKQJT98765432":
        return raw[0]
    return None


def _detect_suit_by_color(roi_bgr: np.ndarray) -> str | None:
    """Detect suit by dominant colour in the card region."""
    hsv = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2HSV)
    best_suit = None
    best_ratio = 0.0
    total = roi_bgr.shape[0] * roi_bgr.shape[1]

    for suit, ranges in SUIT_HSV_RANGES.items():
        if not ranges:
            continue
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lo, hi in ranges:
            mask |= cv2.inRange(hsv, lo, hi)
        ratio = cv2.countNonZero(mask) / total
        if ratio > best_ratio:
            best_ratio = ratio
            best_suit = suit

    # Black suits: low saturation + low value
    sat = hsv[:, :, 1].mean()
    val = hsv[:, :, 2].mean()
    if sat < 40 and val < 80:
        return "s"  # spades (black) by default for low-sat dark

    if best_ratio > 0.05:
        return best_suit
    return None


class CardDetector:
    """Автоматический поиск и распознавание карт.

    Расширен (Phase 2 vision_fragility.md):
    - Multi-template matching для рангов через CardTemplateBank
    - Multi-strategy OCR preprocessing (Otsu, Adaptive, CLAHE)
    - Pytesseract → EasyOCR fallback цепочка
    - Colour-based suit detection
    """

    def __init__(self):
        self.min_card_area = 2000  # Минимальная площадь карты
        self.max_card_area = 50000  # Максимальная площадь карты
        self.aspect_ratio_range = (0.5, 0.9)  # Соотношение сторон карты
        self._template_bank = _get_card_template_bank()

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
        Извлечение ранга+масти с карты через multi-strategy pipeline:

        1. Template matching (CardTemplateBank) — быстро и точно
        2. Tesseract OCR с multi-preprocessing
        3. EasyOCR fallback
        4. Colour-based suit detection

        Args:
            image: PIL Image или numpy array
            card: dict с координатами карты

        Returns:
            str: Распознанный текст (e.g. "Ah", "Ks", "Td")
        """
        # Конвертируем в numpy BGR
        if isinstance(image, Image.Image):
            img_arr = np.array(image)
            if len(img_arr.shape) == 3 and img_arr.shape[2] == 3:
                img_bgr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)
            else:
                img_bgr = img_arr
        else:
            img_bgr = image.copy()

        x, y, w, h = card['x'], card['y'], card['w'], card['h']

        # Берем верхнюю часть карты (ранг + масть)
        top_h = max(1, int(h * 0.35))
        roi_bgr = img_bgr[y:y + top_h, x:x + w]
        if roi_bgr.size == 0:
            return "?"

        # Увеличиваем для лучшего распознавания
        scale = 3
        roi_bgr = cv2.resize(roi_bgr, (w * scale, top_h * scale), interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)

        # --- Strategy 1: Template matching ---
        rank, tpl_conf = self._template_bank.match_rank(gray)
        if rank and tpl_conf >= 0.55:
            suit = _detect_suit_by_color(roi_bgr)
            result = rank + (suit if suit else "")
            logger.debug("Template match: %s (conf=%.2f)", result, tpl_conf)
            return result

        # --- Strategy 2: Multi-preprocessing Tesseract ---
        rank_from_ocr = None
        for variant in _preprocess_variants(gray):
            text = _tesseract_ocr(variant)
            rank_from_ocr = _normalise_rank(text)
            if rank_from_ocr:
                break

        # --- Strategy 3: EasyOCR fallback ---
        if not rank_from_ocr:
            text = _easyocr_ocr(gray)
            rank_from_ocr = _normalise_rank(text)

        # --- Strategy 4: Template at lower threshold ---
        if not rank_from_ocr and rank and tpl_conf >= 0.40:
            rank_from_ocr = rank

        # Combine rank + suit
        if rank_from_ocr:
            suit = _detect_suit_by_color(roi_bgr)
            return rank_from_ocr + (suit if suit else "")

        return "?"
    
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
