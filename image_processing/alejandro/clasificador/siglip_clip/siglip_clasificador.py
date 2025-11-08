import os
import csv
import numpy as np
from tqdm import tqdm
from PIL import Image
import torch
from numpy.linalg import norm
from transformers import CLIPProcessor, CLIPModel

# Directorios y archivos
IMAGES_DIR = "cropped_imgs"
CATEGORIES_FILE = "categories_test.txt"
OUTPUT_CSV = "results.csv"
EMBEDDINGS_FILE = "embeddings_categories.npy"

# "google/siglip-base-patch16-224"  mas nuevo
# "openai/clip-vit-base-patch32" mas ligero
MODEL_NAME = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"

# Modelo y procesador
print(f"Cargando modelo {MODEL_NAME}...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# Funciones

def cosine_similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))

def embed_texts(texts):
    inputs = processor(text=texts, padding=True, truncation=True, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.get_text_features(**inputs)
    # Normalizar embeddings
    embeddings = outputs / outputs.norm(dim=-1, keepdim=True)
    return embeddings.cpu().numpy()

def embed_images(image_paths):
    images = [Image.open(p).convert("RGB") for p in image_paths]
    inputs = processor(images=images, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.get_image_features(**inputs)
    # Normalizar embeddings
    embeddings = outputs / outputs.norm(dim=-1, keepdim=True)
    return embeddings.cpu().numpy()

def softmax(x, temperature=0.05):
    e_x = np.exp((x - np.max(x)) / temperature)
    return e_x / e_x.sum()


# Carga de categorias

if not os.path.exists(CATEGORIES_FILE):
    raise FileNotFoundError(f"No se encuentra {CATEGORIES_FILE}")

with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
    categories = [line.strip() for line in f if line.strip()]

print(f"{len(categories)} categorías cargadas.")

# Embedding de categorias

if os.path.exists(EMBEDDINGS_FILE):
    print(f"Cargando embeddings de categorías desde {EMBEDDINGS_FILE}...")
    category_embeddings = np.load(EMBEDDINGS_FILE, allow_pickle=True).item()
else:
    print("Calculando embeddings de categorías...")
    text_embeddings = embed_texts(categories)
    category_embeddings = {cat: emb for cat, emb in zip(categories, text_embeddings)}
    np.save(EMBEDDINGS_FILE, category_embeddings)
    print(f"Guardado en {EMBEDDINGS_FILE}")

# Clasificacion

print("Clasificando imágenes...")
results = []

# Procesamos imágenes por lotes pequeños
image_files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]

for filename in tqdm(image_files):
    img_path = os.path.join(IMAGES_DIR, filename)
    img_emb = embed_images([img_path])[0]

    # Similaridad con todas las categorías
    sims = {
        cat: cosine_similarity(img_emb, emb)
        for cat, emb in category_embeddings.items()
    }

    cats = list(sims.keys())
    values = np.array(list(sims.values()))
    probs = softmax(values)

    best_idx = np.argmax(probs)
    best_cat = cats[best_idx]
    best_score = probs[best_idx]

    results.append({
        "imagen": filename,
        "categoria_predicha": best_cat,
        "confianza": round(float(best_score), 4)
    })

# Guardado de resultados

print(f"Guardando resultados en {OUTPUT_CSV}...")
with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["imagen", "categoria_predicha", "confianza"])
    writer.writeheader()
    writer.writerows(results)

print("Proceso completado correctamente.")
print(f"Resultados guardados en: {OUTPUT_CSV}")
