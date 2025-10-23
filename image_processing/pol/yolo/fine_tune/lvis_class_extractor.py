import json

# Ruta al archivo de anotaciones LVIS
json_path = "/home/abollao/yolo/fine_tune/datasets/lvis/annotations/lvis_v1_val.json"

# Ruta del fichero de salida
output_path = "lvis_classes.txt"

# Cargar JSON
with open(json_path, 'r') as f:
    data = json.load(f)

# Extraer categorías
categories = data["categories"]

print(f"Total de clases LVIS: {len(categories)}")
print(f"Guardando clases en {output_path}...")

# Guardar en TXT
with open(output_path, 'w') as out:
    out.write(f"Total de clases LVIS: {len(categories)}\n\n")
    for cat in categories:
        out.write(f"{cat['id']}: {cat['name']}\n")

print("✅ Archivo lvis_classes.txt generado correctamente.")
