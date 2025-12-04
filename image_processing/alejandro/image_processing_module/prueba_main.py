# test_lookup_name.py

from main import lookup_name

# Ruta a la carpeta donde tienes las imágenes reales
IMAGE_DIR = "test_imgs"

print("\n=== Probando lookup_name ===\n")

resultado = lookup_name(IMAGE_DIR)

print("Resultado:")
print(resultado)

print("\nPrueba completada.\n")