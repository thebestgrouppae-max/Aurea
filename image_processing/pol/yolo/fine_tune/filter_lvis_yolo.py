import os
import yaml
import shutil

# ==== CONFIGURACIÓN ====
# Ruta base del proyecto
BASE_PATH = "/home/abollao/yolo/fine_tune"
DATASET_ORIGEN = os.path.join(BASE_PATH, "datasets/lvis")
DATASET_DESTINO = os.path.join(BASE_PATH, "datasets/lvis_pure")
YAML_CLASES = os.path.join(BASE_PATH, "lvis_subset_pure.yaml")

# ==== CARGAR CLASES DEL YAML ====
with open(YAML_CLASES, 'r') as f:
    data_yaml = yaml.safe_load(f)

clases_validas = set(data_yaml.get("names", {}).keys())  # índices válidos

# ==== CREAR ESTRUCTURA DESTINO ====
for split in ["train2017", "val2017"]:
    os.makedirs(os.path.join(DATASET_DESTINO, "images", split), exist_ok=True)
    os.makedirs(os.path.join(DATASET_DESTINO, "labels", split), exist_ok=True)

# ==== PROCESAR CADA SPLIT ====
def procesar_split(split):
    origen_labels = os.path.join(DATASET_ORIGEN, "labels", split)
    origen_images = os.path.join(DATASET_ORIGEN, "images", split)

    destino_labels = os.path.join(DATASET_DESTINO, "labels", split)
    destino_images = os.path.join(DATASET_DESTINO, "images", split)

    txt_salida = os.path.join(DATASET_DESTINO, f"{split.replace('2017','')}.txt")

    with open(txt_salida, 'w') as index_file:
        for file in os.listdir(origen_labels):
            if not file.endswith(".txt"):
                continue

            ruta_label = os.path.join(origen_labels, file)
            img_name = file.replace(".txt", ".jpg")
            ruta_imagen = os.path.join(origen_images, img_name)

            if not os.path.exists(ruta_imagen):
                img_name = file.replace(".txt", ".png")
                ruta_imagen = os.path.join(origen_images, img_name)

            clases_en_label = False
            nuevas_lineas = []

            with open(ruta_label, 'r') as lf:
                for linea in lf:
                    try:
                        cls_id = int(linea.split()[0])
                        if cls_id in clases_validas:
                            nuevas_lineas.append(linea)
                            clases_en_label = True
                    except:
                        continue

            if clases_en_label:
                # Copiar label filtrado
                with open(os.path.join(destino_labels, file), 'w') as out_l:
                    out_l.writelines(nuevas_lineas)

                # Copiar imagen asociada
                if os.path.exists(ruta_imagen):
                    shutil.copy(ruta_imagen, destino_images)

                # Añadir al .txt del split
                ruta_abs = os.path.join(DATASET_DESTINO, "images", split, img_name)
                index_file.write(ruta_abs + "\n")

# Ejecutar procesamiento silencioso
procesar_split("train2017")
procesar_split("val2017")

# ==== GENERAR NUEVO YAML DESTINO ====
nuevo_yaml = os.path.join(DATASET_DESTINO, "lvis_pure.yaml")
data_yaml["path"] = DATASET_DESTINO  # actualizar path
with open(nuevo_yaml, "w") as f:
    yaml.dump(data_yaml, f)

# ==== RESUMEN FINAL ====
print("\n✅ Filtrado completado.")
print(f"📁 Dataset generado en: {DATASET_DESTINO}")
print("📝 Archivos generados: train.txt, val.txt, lvis_pure.yaml")
print("🚀 Listo para entrenamiento en YOLO.")
