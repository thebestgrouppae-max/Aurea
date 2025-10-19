import os
import cv2
from datetime import datetime
from ultralytics import YOLO

# Lista de modelos a usar 
model_paths = [
    "yolo11n.pt",
    "yolo11n_lvis50.pt",
    "yolo11n_lvis152-supermercado.pt"
]

# Carpeta de imágenes
input_base_dir = "imgs_prueba"

# Crear carpeta con la fecha actual (dd-mm-aaaa)
output_base_dir = datetime.now().strftime("%d-%m-%Y")
os.makedirs(output_base_dir, exist_ok=True)

# Cargar todos los modelos
models = {os.path.splitext(os.path.basename(mp))[0]: YOLO(mp) for mp in model_paths}

# Recorrer todas las subcarpetas de imgs_prueba
for subfolder in os.listdir(input_base_dir):
    input_subdir = os.path.join(input_base_dir, subfolder)
    if not os.path.isdir(input_subdir):
        continue

    output_subdir = os.path.join(output_base_dir, subfolder)
    os.makedirs(output_subdir, exist_ok=True)

    for img_name in os.listdir(input_subdir):
        img_path = os.path.join(input_subdir, img_name)

        if not img_name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        base_name = os.path.splitext(img_name)[0]

        for model_name, model in models.items():
            try:
                results = model.predict(img_path, verbose=False)
                result_img = results[0].plot()

                # Obtener dimensiones
                h, w = result_img.shape[:2]
                text = model_name
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness_text = 1
                thickness_border = 3

                text_size, _ = cv2.getTextSize(text, font, font_scale, thickness_text)
                text_x = 10
                text_y = h - 10

                # Contorno blanco
                cv2.putText(result_img, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness_border)
                # Texto negro
                cv2.putText(result_img, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness_text)

                output_filename = f"{base_name}_{model_name}.jpg"
                output_path = os.path.join(output_subdir, output_filename)
                cv2.imwrite(output_path, result_img)

            except Exception as e:
                print(f"⚠️ Error procesando {img_path} con {model_name}: {e}")

print(f"Procesado completado. Resultados en: {output_base_dir}")
