# vision_fragility.md — Улучшение стабильности vision

Цель: сделать vision надёжным на разных скинах, разрешениях, темах.

## Фаза 1 — Auto-calibration
- Добавить auto_roi_finder.py — поиск зон по anchors (кнопки, logos)
- Тест: 10 разных скриншотов → авто-наход ROI

## Фаза 2 — Multi-template fallback
- Добавить multi_template_matching.py — несколько шаблонов для карт/чисел
- Fine-tune OCR (EasyOCR / Tesseract)

## Фаза 3 — ML-улучшения
- Интегрировать YOLOv8 для регионов
- Датасет 1000+ скриншотов — дообучение
- Тест: точность >95%

