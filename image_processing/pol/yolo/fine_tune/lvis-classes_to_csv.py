import json
import csv

# Ruta al archivo LVIS en tu sistema
json_path = "/home/abollao/yolo/fine_tune/datasets/lvis/annotations/lvis_v1_val.json"
output_csv = "lvis_classes.csv"

# Cargar JSON
with open(json_path, 'r') as f:
    data = json.load(f)

categories = data["categories"]

# Escribir CSV
with open(output_csv, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["id_original", "lvis_class"])
    for cat in categories:
        writer.writerow([cat['id'], cat['name']])

print(f"✅ Archivo generado: {output_csv}")
