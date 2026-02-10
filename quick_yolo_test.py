from ultralytics import YOLO
from PIL import Image

print("Загружаем модель...")
model = YOLO("weights/best.pt")

print("Загружаем изображение...")
img = Image.open("test_capture_overlay.png")
print(f"Размер: {img.size}")

print("\nТест с порогом 0.05...")
results = model(img, conf=0.05, iou=0.3, verbose=True)

print(f"\nНайдено объектов: {len(results[0].boxes)}")

if len(results[0].boxes) > 0:
    for i, box in enumerate(results[0].boxes[:5], 1):
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        card = model.names[cls_id]
        print(f"{i}. {card} - {conf:.1%}")
    results[0].save("quick_test_result.jpg")
    print("\nСохранено: quick_test_result.jpg")
else:
    print("\nКАРТЫ НЕ НАЙДЕНЫ!")
    print("Попробуем еще ниже порог...")
    
    results2 = model(img, conf=0.01, verbose=True)
    print(f"С порогом 0.01: {len(results2[0].boxes)} объектов")
