import cv2
import os
from ultralytics import YOLO

# --- Configuración ---
IMAGE_PATH = "sofa.jpg"           # Imagen de entrada
MODEL_PATH = "yolov8n-oiv7.pt"     # Modelo YOLO
OUTPUT_DIR = "detected_objects"    # Carpeta de salida

# Crear carpeta de salida si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Cargar modelo YOLO
model = YOLO(MODEL_PATH)

# Ejecutar detección
results = model(IMAGE_PATH)

# Cargar imagen original con OpenCV
image = cv2.imread(IMAGE_PATH)

# Iterar sobre las detecciones
for i, box in enumerate(results[0].boxes):
    # Coordenadas (x1, y1, x2, y2)
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    
    # Recortar el objeto de la imagen original
    cropped = image[y1:y2, x1:x2]

    # Obtener nombre de clase
    cls_id = int(box.cls[0])
    cls_name = results[0].names[cls_id]

    # Guardar imagen recortada
    output_path = os.path.join(OUTPUT_DIR, f"{i+1}_{cls_name}.jpg")
    cv2.imwrite(output_path, cropped)
    print(f"Guardado: {output_path}")

print(f"\nObjetos detectados y guardados en: '{OUTPUT_DIR}/'")
