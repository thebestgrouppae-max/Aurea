import os
import csv
import cv2
import numpy as np
from tqdm import tqdm
from PIL import Image
import torch

# YOLO
from ultralytics import YOLO

# CLIP (usar modelo con safetensors)
from transformers import CLIPProcessor, CLIPModel

# ==========================
# CONFIGURACIÓN
# ==========================

IMAGES_DIR = "cdr_images"                     # Carpeta de entrada con imágenes
YOLO_MODEL_PATH = "yolov8n-oiv7.pt"           # Modelo YOLO (Open Images V7)
CATEGORIES_FILE = "categories_products.txt"    # Fichero con categorías (una por línea)

OUTPUT_DIR = "demo_outputs"                    # Carpeta raíz de salida
CROPS_DIR = os.path.join(OUTPUT_DIR, "crops")
CSV_PATH = os.path.join(OUTPUT_DIR, "results.csv")

# CLIP
CLIP_MODEL_NAME = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"

# Umbrales
YOLO_CONF_THRES = 0.25
SOFTMAX_TEMPERATURE = 0.05
OTHER_THRESHOLD = 0.25
USE_DESCRIPTIVE_CATEGORIES = True

# ==========================
# UTILIDADES
# ==========================

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(CROPS_DIR, exist_ok=True)

def softmax(x, temperature=1.0):
    x = np.array(x, dtype=np.float64)
    x = (x - x.max()) / temperature
    e_x = np.exp(x)
    return e_x / (e_x.sum() + 1e-12)

def cosine_similarity(a, b):
    a = np.asarray(a); b = np.asarray(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))

def clamp_bbox(x1, y1, x2, y2, w, h):
    x1 = max(0, min(int(x1), w - 1))
    y1 = max(0, min(int(y1), h - 1))
    x2 = max(0, min(int(x2), w - 1))
    y2 = max(0, min(int(y2), h - 1))
    if x2 <= x1: x2 = min(w - 1, x1 + 1)
    if y2 <= y1: y2 = min(h - 1, y1 + 1)
    return x1, y1, x2, y2

# ==========================
# CARGA DE MODELOS
# ==========================

def load_yolo(model_path):
    model = YOLO(model_path)
    return model

def load_clip(model_name):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(model_name).to(device)
    processor = CLIPProcessor.from_pretrained(model_name)
    return model, processor, device

def embed_texts(model, processor, device, texts):
    inputs = processor(text=texts, padding=True, truncation=True, return_tensors="pt").to(device)
    with torch.no_grad():
        feats = model.get_text_features(**inputs)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().numpy()

def embed_images(model, processor, device, pil_images):
    inputs = processor(images=pil_images, return_tensors="pt").to(device)
    with torch.no_grad():
        feats = model.get_image_features(**inputs)
        feats = feats / feats.norm(dim=-1, keepdim=True)
    return feats.cpu().numpy()

# ==========================
# PIPELINE
# ==========================

def main():
    ensure_dirs()

    # 1) Cargar modelos
    print("🔍 Cargando YOLO...")
    yolo = load_yolo(YOLO_MODEL_PATH)

    print("🧠 Cargando CLIP...")
    clip_model, clip_processor, device = load_clip(CLIP_MODEL_NAME)

    # 2) Cargar categorías
    if not os.path.exists(CATEGORIES_FILE):
        raise FileNotFoundError(f"No se encuentra {CATEGORIES_FILE}")

    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        raw_categories = [line.strip() for line in f if line.strip()]

    categories = [f"a photo of a {c}" for c in raw_categories] if USE_DESCRIPTIVE_CATEGORIES else raw_categories[:]
    cat_embeddings = embed_texts(clip_model, clip_processor, device, categories)

    # 3) Buscar imágenes en el directorio
    image_files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    if not image_files:
        raise FileNotFoundError(f"No se encontraron imágenes en {IMAGES_DIR}")

    print(f"📂 Se encontraron {len(image_files)} imágenes en {IMAGES_DIR}")

    results_rows = []

    for img_name in tqdm(image_files, desc="Procesando imágenes"):
        input_path = os.path.join(IMAGES_DIR, img_name)
        boxed_image_path = os.path.join(OUTPUT_DIR, f"{os.path.splitext(img_name)[0]}_with_boxes.jpg")

        img_bgr = cv2.imread(input_path)
        if img_bgr is None:
            print(f"⚠️ No se pudo abrir {img_name}, se omite.")
            continue
        H, W = img_bgr.shape[:2]

        # YOLO detección
        results = yolo.predict(source=input_path, conf=YOLO_CONF_THRES, verbose=False)
        r = results[0]

        annotated = r.plot()
        cv2.imwrite(boxed_image_path, annotated)

        # Extraer cajas
        boxes = []
        if r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy()
            for i in range(xyxy.shape[0]):
                x1, y1, x2, y2 = xyxy[i].tolist()
                conf = float(confs[i])
                x1, y1, x2, y2 = clamp_bbox(x1, y1, x2, y2, W, H)
                boxes.append((x1, y1, x2, y2, conf))
        else:
            print(f"⚠️ No se detectaron objetos en {img_name}")
            continue

        # Generar crops
        for idx, (x1, y1, x2, y2, conf) in enumerate(boxes):
            crop = img_bgr[y1:y2, x1:x2]
            crop_name = f"{os.path.splitext(img_name)[0]}_crop_{idx:03d}.jpg"
            out_path = os.path.join(CROPS_DIR, crop_name)
            cv2.imwrite(out_path, crop)

            pil_img = Image.open(out_path).convert("RGB")
            img_emb = embed_images(clip_model, clip_processor, device, [pil_img])[0]

            sims = [cosine_similarity(img_emb, cat_emb) for cat_emb in cat_embeddings]
            probs = softmax(sims, temperature=SOFTMAX_TEMPERATURE)
            best_idx = int(np.argmax(probs))
            best_cat = categories[best_idx]
            best_prob = float(probs[best_idx])
            final_cat = best_cat if best_prob >= OTHER_THRESHOLD else "other"

            results_rows.append({
                "input_image": img_name,
                "boxed_image": os.path.basename(boxed_image_path),
                "crop_image": os.path.basename(out_path),
                "bbox_x1": x1, "bbox_y1": y1, "bbox_x2": x2, "bbox_y2": y2,
                "yolo_conf": round(conf, 4),
                "clip_category": final_cat,
                "clip_prob": round(best_prob, 4)
            })

    # 4) Guardar CSV
    print(f"💾 Guardando resultados en {CSV_PATH}...")
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "input_image", "boxed_image", "crop_image",
            "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2",
            "yolo_conf", "clip_category", "clip_prob"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results_rows)

    print("✅ Proceso completado.")
    print(f" - Carpeta de salida: {OUTPUT_DIR}")
    print(f" - CSV: {CSV_PATH}")

if __name__ == "__main__":
    main()
