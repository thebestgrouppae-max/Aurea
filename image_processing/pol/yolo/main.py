#POL:  ANTES DE RUNNEAR --> pip install -r requirements.txt
import os
import cv2
import numpy as np
from PIL import Image
import torch
import logging
import glob
import warnings
import json
import subprocess # <--- Nueva librería necesaria

# --- SILENCIADORES ---
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3" 
logging.getLogger("ultralytics").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
from transformers import CLIPProcessor, CLIPModel, logging as hf_logging
hf_logging.set_verbosity_error() 

# IMPORTACIONES
from ultralytics import YOLO

# ==========================
# CONFIGURACIÓN
# ==========================

# YA NO NECESITAMOS PONER EL USUARIO MANUALMENTE
# Lo calcularemos automáticamente en la función detectar_ruta_descargas()

# Modelos YOLO
YOLO_MODEL_MAIN = "yolov8x.pt"        
YOLO_MODEL_FALLBACK = "yolov8n-oiv7.pt" 

CATEGORIES_FILE = "categories_food.txt"

OUTPUT_DIR = "demo_outputs"
BOXED_IMAGE_PATH = os.path.join(OUTPUT_DIR, "image_with_boxes.jpg")
CROPS_DIR = os.path.join(OUTPUT_DIR, "crops")
RESULT_JSON_PATH = os.path.join(OUTPUT_DIR, "resultado.json")

# Configuración CLIP
CLIP_MODEL_NAME = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"
YOLO_CONF_THRES = 0.25                        
SOFTMAX_TEMPERATURE = 0.05                    
USE_DESCRIPTIVE_CATEGORIES = True

# ==========================
# UTILIDADES
# ==========================

def detectar_ruta_descargas():
    """
    Detecta automáticamente la carpeta de Descargas, 
    ya sea en WSL (Windows) o en Linux/Mac nativo.
    """
    # INTENTO 1: Detección para WSL (Windows Subsystem for Linux)
    try:
        # Ejecutamos cmd.exe para preguntar por la variable %USERPROFILE% de Windows
        # Esto devuelve algo como C:\Users\polfe
        result = subprocess.run(
            ["cmd.exe", "/c", "echo %USERPROFILE%"], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            win_path = result.stdout.strip()
            # Convertimos la ruta de Windows a formato WSL
            # C:\Users\polfe -> /mnt/c/Users/polfe
            wsl_path = win_path.replace("\\", "/").replace("C:", "/mnt/c")
            downloads_path = os.path.join(wsl_path, "Downloads")
            
            if os.path.exists(downloads_path):
                return downloads_path
    except Exception:
        pass # Si falla (porque no estamos en WSL), pasamos al plan B

    # INTENTO 2: Detección estándar para Linux/Mac
    # Busca en ~/Downloads
    linux_path = os.path.expanduser("~/Downloads")
    if os.path.exists(linux_path):
        return linux_path

    # Si todo falla
    return None

def get_latest_image_from_downloads():
    # Llamamos a la nueva función inteligente
    path_downloads = detectar_ruta_descargas()
    
    if path_downloads is None:
        return None, "No se pudo detectar la carpeta de Descargas ni en Windows ni en Linux."

    image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"]
    files = []
    for ext in image_extensions:
        found = glob.glob(os.path.join(path_downloads, ext))
        found += glob.glob(os.path.join(path_downloads, ext.upper()))
        files.extend(found)

    if not files:
        return None, f"No hay imágenes en: {path_downloads}"

    latest_file = max(files, key=os.path.getmtime)
    return latest_file, None

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

def run_yolo_detection(model_name, image_path):
    try:
        model = YOLO(model_name)
        results = model.predict(source=image_path, conf=YOLO_CONF_THRES, verbose=False, save=False)
        r = results[0]
        
        boxes = []
        if r.boxes is not None and len(r.boxes) > 0:
            img_shape = cv2.imread(image_path).shape[:2]
            H, W = img_shape
            xyxy = r.boxes.xyxy.cpu().numpy()
            confs = r.boxes.conf.cpu().numpy()
            for i in range(xyxy.shape[0]):
                x1, y1, x2, y2 = xyxy[i].tolist()
                conf = float(confs[i])
                x1, y1, x2, y2 = clamp_bbox(x1, y1, x2, y2, W, H)
                boxes.append((x1, y1, x2, y2, conf))
        
        return boxes, r
    except Exception:
        return [], None

# ==========================
# CARGA DE MODELOS CLIP
# ==========================

def load_clip(model_name):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(model_name).to(device)
    processor = CLIPProcessor.from_pretrained(model_name, use_fast=True)
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
# PIPELINE PRINCIPAL
# ==========================

def main():
    ensure_dirs()

    # 1. OBTENER IMAGEN
    input_image_path, error_msg = get_latest_image_from_downloads()
    if input_image_path is None:
        # Error mejorado para saber por qué falla
        error_data = {"status": "error", "message": "no_image_found", "details": error_msg}
        print(json.dumps(error_data))
        return

    img_bgr = cv2.imread(input_image_path)
    if img_bgr is None:
        error_data = {"status": "error", "message": "cannot_read_image"}
        print(json.dumps(error_data))
        return

    # --- FASE DE DETECCIÓN ---
    boxes, yolo_result = run_yolo_detection(YOLO_MODEL_MAIN, input_image_path)
    used_method = "yolo_main"
    
    if len(boxes) == 0:
        boxes, yolo_result = run_yolo_detection(YOLO_MODEL_FALLBACK, input_image_path)
        used_method = "yolo_fallback"

    
    # --- PREPARAR CLIP ---
    if not os.path.exists(CATEGORIES_FILE):
        error_data = {"status": "error", "message": "missing_categories_file"}
        print(json.dumps(error_data))
        return

    with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
        raw_categories = [line.strip() for line in f if line.strip()]

    if USE_DESCRIPTIVE_CATEGORIES:
        categories_prompt = [f"a photo of a {c}" for c in raw_categories]
    else:
        categories_prompt = raw_categories[:]

    clip_model, clip_processor, device = load_clip(CLIP_MODEL_NAME)
    cat_embeddings = embed_texts(clip_model, clip_processor, device, categories_prompt)
    
    detected_classes = []

    # --- CLASIFICACIÓN ---

    if len(boxes) > 0:
        annotated = yolo_result.plot()
        cv2.imwrite(BOXED_IMAGE_PATH, annotated) 

        for idx, (x1, y1, x2, y2, conf) in enumerate(boxes):
            crop = img_bgr[y1:y2, x1:x2]
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(crop_rgb)
            
            crop_name = f"crop_{idx:03d}.jpg"
            out_path = os.path.join(CROPS_DIR, crop_name)
            pil_img.save(out_path)

            img_emb = embed_images(clip_model, clip_processor, device, [pil_img])[0]
            sims = [cosine_similarity(img_emb, cat_emb) for cat_emb in cat_embeddings]
            probs = softmax(sims, temperature=SOFTMAX_TEMPERATURE)
            best_idx = int(np.argmax(probs))
            detected_classes.append(raw_categories[best_idx])

    else:
        used_method = "clip_direct"
        pil_img = Image.open(input_image_path).convert("RGB")
        
        img_emb = embed_images(clip_model, clip_processor, device, [pil_img])[0]
        sims = [cosine_similarity(img_emb, cat_emb) for cat_emb in cat_embeddings]
        probs = softmax(sims, temperature=SOFTMAX_TEMPERATURE)
        best_idx = int(np.argmax(probs))
        
        detected_classes.append(raw_categories[best_idx])

    # --- 4. RESULTADO FINAL ---
    
    unique_detected_classes = list(set(detected_classes))
    unique_detected_classes.sort() 

    resultado_final = {
        "status": "success",
        "imagen_procesada": os.path.basename(input_image_path),
        "metodo_usado": used_method,
        "total_productos_unicos": len(unique_detected_classes),
        "productos": unique_detected_classes
    }

    json_output = json.dumps(resultado_final, indent=4)
    print(json_output)

    with open(RESULT_JSON_PATH, "w", encoding="utf-8") as f:
        f.write(json_output)

if __name__ == "__main__":
    main()
