Цель: сделать vision надёжным на разных скинах, разрешениях, темах, румах.

## Фаза 1 — Auto-calibration ROI
- Добавить auto_roi_finder.py — поиск зон по anchors (кнопки, logos, using opencv matchTemplate)

## Фаза 2 — Multi-template fallback
- Расширить card_detector.py и yolo_detector.py — несколько шаблонов для карт/чисел (templates/cards/ folder)
- Fine-tune OCR (pytesseract + EasyOCR fallback in test_real_ocr.py)

## Фаза 3 — ML-doobuchenie
- Добавить training_data_collector.py — сбор 1000+ скриншотов (using live_capture.py)
- Дообучить YOLOv8 / Roboflow (roboflow_detector.py)
- Тест: точность >95% на 200 скриншотах (test_model_with_image.py)

