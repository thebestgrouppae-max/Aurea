import os
import cv2
from datetime import datetime
from ultralytics import YOLO

# Lista de modelos a usar 
model_paths = ["yolo11n.pt"]

# Carpeta de imágenes
input_base_dir = "fotos"

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
            
        original_image = cv2.imread(img_path)
        if original_image is None:
            print(f"⚠️ Error: No se pudo leer la imagen {img_path}. Omitiendo.")
            continue

        base_name = os.path.splitext(img_name)[0]

        for model_name, model in models.items():
            try:
                # 1. Realizar la predicción
                results = model.predict(img_path, verbose=False)
                
                # 2. Obtener las cajas (bounding boxes)
                cajas = results[0].boxes
                
                # --- MODIFICACIÓN 1: GUARDAR .TXT CON NOMBRE Y COORDENADAS ---
                
                # Definir la ruta del .txt
                txt_filename = f"{base_name}_{model_name}.txt"
                txt_output_path = os.path.join(output_subdir, txt_filename)
                
                with open(txt_output_path, 'w') as f:
                    for i in range(len(cajas)):
                        # Obtener ID de clase
                        clase_id = int(cajas.cls[i])
                        
                        # Obtener el NOMBRE de la clase (ej: 'bottle')
                        nombre_clase = results[0].names[clase_id]
                        
                        # Obtener coordenadas normalizadas
                        coords_norm = cajas.xywhn[i]
                        x_c, y_c, w, h = coords_norm.tolist()
                        
                        # Escribir la línea: "nombre X Y W H"
                        f.write(f"{nombre_clase} {x_c} {y_c} {w} {h}\n")
                
                if len(cajas) > 0:
                    print(f"✔️ Archivo de coordenadas guardado en: {txt_output_path}")
                # --- FIN MODIFICACIÓN 1 ---

                # --- MODIFICACIÓN 2: GUARDAR RECORTES CON NUEVO NOMBRE ---
                
                cajas_pix = cajas.xyxy.cpu().numpy().astype(int)
                
                for j, (x1, y1, x2, y2) in enumerate(cajas_pix):
                    recorte = original_image[y1:y2, x1:x2]
                    
                    # Definir el nombre del archivo de recorte (ej: aceite_yolo11n_recortada.jpg)
                    # ADVERTENCIA: Esto se sobrescribirá si hay múltiples detecciones
                    recorte_filename = f"{base_name}_{model_name}_recortada.jpg"
                    recorte_output_path = os.path.join(output_subdir, recorte_filename)
                    
                    cv2.imwrite(recorte_output_path, recorte)
                
                if len(cajas_pix) > 0:
                    print(f"✔️ {len(cajas_pix)} recortes guardados como {recorte_filename}")
                # --- FIN MODIFICACIÓN 2 ---

                # --- MODIFICACIÓN 3: GUARDAR IMAGEN ORIGINAL CON NUEVO NOMBRE ---
                
                result_img = results[0].plot()

                # Poner texto del modelo en la imagen
                h, w = result_img.shape[:2]
                text = model_name
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.5
                thickness_text = 1
                thickness_border = 3
                text_size, _ = cv2.getTextSize(text, font, font_scale, thickness_text)
                text_x = 10
                text_y = h - 10
                cv2.putText(result_img, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness_border)
                cv2.putText(result_img, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness_text)

                # Nuevo nombre para la imagen "original" ploteada
                output_filename = f"{base_name}_{model_name}_original.jpg"
                output_path = os.path.join(output_subdir, output_filename)
                cv2.imwrite(output_path, result_img)
                # --- FIN MODIFICACIÓN 3 ---

            except Exception as e:
                print(f"⚠️ Error procesando {img_path} con {model_name}: {e}")

print(f"Procesado completado. Resultados en: {output_base_dir}")