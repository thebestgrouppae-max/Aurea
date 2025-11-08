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

INPUT_IMAGE = "image.jpg"                     # Imagen de la demo
YOLO_MODEL_PATH = "yolov8n-oiv7.pt"           # Modelo YOLO (Open Images V7)
CATEGORIES_FILE = "categories_products.txt"            # Fichero con categorías (una por línea)

OUTPUT_DIR = "demo_outputs"                   # Carpeta raíz de salida
BOXED_IMAGE_PATH = os.path.join(OUTPUT_DIR, "image_with_boxes.jpg")
CROPS_DIR = os.path.join(OUTPUT_DIR, "crops")
CSV_PATH = os.path.join(OUTPUT_DIR, "results.csv")

# CLIP
CLIP_MODEL_NAME = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"

# Umbrales
YOLO_CONF_THRES = 0.25                        # confianza mínima de detección YOLO
SOFTMAX_TEMPERATURE = 0.05                    # temperatura para calibrar probabilidades CLIP
OTHER_THRESHOLD = 0.25                         # si la probabilidad < 0.25 => "other"

# Si quieres “estilo CLIP” en categorías, pon a True para envolver con "a photo of a {cat}"
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

    # 1) YOLO: detección + imagen con cajas + guardar bboxes
    print("🔍 Ejecutando YOLO sobre la imagen...")
    yolo = load_yolo(YOLO_MODEL_PATH)

    # Cargar imagen con OpenCV para dibujar y para crops
    img_bgr = cv2.imread(INPUT_IMAGE)
    if img_bgr is None:
        raise FileNotFoundError(f"No se pudo abrir {INPUT_IMAGE}")
    H, W = img_bgr.shape[:2]

    # Inferencia YOLO
    results = yolo.predict(source=INPUT_IMAGE, conf=YOLO_CONF_THRES, verbose=False)
    r = results[0]

    # Dibujar y guardar imagen con boxes
    # Ultralytics provee un visualizado rápido:
    annotated = r.plot()  # ndarray BGR
    cv2.imwrite(BOXED_IMAGE_PATH, annotated)

    # Extraer bboxes
    boxes = []
    if r.boxes is not None and len(r.boxes) > 0:
        xyxy = r.boxes.xyxy.cpu().numpy()   # [N, 4]
        confs = r.boxes.conf.cpu().numpy()  # [N]
        # Nota: no usamos r.boxes.cls (la etiqueta de YOLO) para no sesgar la clasificación
        for i in range(xyxy.shape[0]):
            x1, y1, x2, y2 = xyxy[i].tolist()
            conf = float(confs[i])
            x1, y1, x2, y2 = clamp_bbox(x1, y1, x2, y2, W, H)
            boxes.append((x1, y1, x2, y2, conf))
    else:
        print("⚠️ YOLO no encontró objetos por encima del umbral. Continuo (CSV vacío).")
        input("Presiona ENTER para continuar")

    #input("Presiona ENTER para continuar")
    # 2) Generar sub-fotos (crops)
    print(f"✂️ Generando {len(boxes)} sub-fotos...")

    crop_paths = []
    for idx, (x1, y1, x2, y2, conf) in enumerate(boxes):
        crop = img_bgr[y1:y2, x1:x2]
        crop_name = f"crop_{idx:03d}_{x1}_{y1}_{x2}_{y2}.jpg"
        out_path = os.path.join(CROPS_DIR, crop_name)
        cv2.imwrite(out_path, crop)
        crop_paths.append((out_path, (x1, y1, x2, y2), conf))

    # 3) CLIP: clasificar cada sub-foto con categories.txt
    if not os.path.exists(CATEGORIES_FILE):
        raise FileNotFoundError(f"No se encuentra {CATEGORIES_FILE}")

    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        raw_categories = [line.strip() for line in f if line.strip()]

    # Opcional: envolver categorías al estilo CLIP
    if USE_DESCRIPTIVE_CATEGORIES:
        categories = [f"a photo of a {c}" for c in raw_categories]
    else:
        categories = raw_categories[:]

    #input("Presiona ENTER para continuar")
    print(f"🧠 Cargando CLIP y calculando embeddings de {len(categories)} categorías...")
    clip_model, clip_processor, device = load_clip(CLIP_MODEL_NAME)
    cat_embeddings = embed_texts(clip_model, clip_processor, device, categories)

    # Clasificar crops
    print("🖼️ Clasificando crops con CLIP...")
    results_rows = []
    for (crop_path, (x1, y1, x2, y2), yolo_conf) in tqdm(crop_paths):
        pil_img = Image.open(crop_path).convert("RGB")
        img_emb = embed_images(clip_model, clip_processor, device, [pil_img])[0]

        # similitudes con cada categoría
        sims = [cosine_similarity(img_emb, cat_emb) for cat_emb in cat_embeddings]

        # softmax con temperatura para probabilidades interpretables
        probs = softmax(sims, temperature=SOFTMAX_TEMPERATURE)
        best_idx = int(np.argmax(probs))
        best_cat = categories[best_idx]
        best_prob = float(probs[best_idx])

        # “other” si baja confianza
        #final_cat = "other" if best_prob < OTHER_THRESHOLD else best_cat
        final_cat = best_cat

        results_rows.append({
            "input_image": os.path.basename(INPUT_IMAGE),
            "boxed_image": os.path.basename(BOXED_IMAGE_PATH),
            "crop_image": os.path.basename(crop_path),
            "bbox_x1": x1, "bbox_y1": y1, "bbox_x2": x2, "bbox_y2": y2,
            "yolo_conf": round(float(yolo_conf), 4),
            "clip_category": final_cat,
            "clip_prob": round(best_prob, 4)
        })

    #input("Presiona ENTER para continuar")
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

    print(f" - Imagen con cajas: {BOXED_IMAGE_PATH}")
    print(f" - Carpeta de crops: {CROPS_DIR}")
    print(f" - CSV: {CSV_PATH}")

if __name__ == "__main__":
    main()
