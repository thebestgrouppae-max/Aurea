# image_processing/main.py

import os
import json
import hashlib
from typing import Tuple, List, Optional

import torch
from PIL import Image

try:
    import open_clip
except ImportError as e:
    raise ImportError(
        "No se ha encontrado la librería 'open_clip_torch'. "
        "Instálala con: pip install open_clip_torch"
    ) from e

# Para que funque:
# pip install torch pillow open_clip_torch

# ------------------------------------------------------------
#   CONFIGURACIÓN GLOBAL DEL MODELO CLIP
# ------------------------------------------------------------

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
_MODEL = None
_PREPROCESS = None


def _load_clip_model():
    """
    Carga el modelo CLIP ViT-H-14 (LAION2B) sólo una vez.
    """
    global _MODEL, _PREPROCESS
    if _MODEL is None or _PREPROCESS is None:
        # Modelo ViT-H-14 entrenado en LAION2B (config estándar)
        _MODEL, _, _PREPROCESS = open_clip.create_model_and_transforms(
            "ViT-H-14",
            pretrained="laion2b_s32b_b79k"
        )
        _MODEL.to(_DEVICE)
        _MODEL.eval()
    return _MODEL, _PREPROCESS


# ------------------------------------------------------------
#   UTILIDADES: LECTURA DE FICHEROS
# ------------------------------------------------------------

def _read_categories(categories_path: str) -> List[str]:
    """
    Lee categorías de un fichero de texto, una por línea.
    Se eliminan líneas vacías y espacios alrededor.
    """
    if not os.path.isfile(categories_path):
        raise FileNotFoundError(f"No se encuentra el fichero de categorías: {categories_path}")

    categories: List[str] = []
    with open(categories_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                categories.append(line)

    if not categories:
        raise ValueError(f"El fichero de categorías '{categories_path}' está vacío.")

    return categories


def _read_mapping(mapping_path: str) -> dict:
    """
    Lee el JSON de mapeo: { "categoria_concreta": "categoria_superior", ... }
    """
    if not os.path.isfile(mapping_path):
        raise FileNotFoundError(f"No se encuentra el fichero de mapeo: {mapping_path}")

    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    if not isinstance(mapping, dict):
        raise ValueError(f"El fichero de mapeo '{mapping_path}' no contiene un objeto JSON válido.")

    return mapping


# ------------------------------------------------------------
#   UTILIDADES: EMBEDDINGS DE TEXTO CON CACHE (SHA256)
# ------------------------------------------------------------

def _sha256_file(path: str) -> str:
    """
    Calcula el SHA256 del contenido completo de un fichero.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_or_create_text_embeddings(
    categories_path: str,
    embeddings_dir: str
) -> Tuple[torch.Tensor, List[str]]:
    """
    Dado el fichero de categorías y un directorio de 'embeddings',
    comprueba si ya existe un fichero de embeddings asociado al SHA256
    del contenido de 'categorías.txt'.

    Si existe, se carga.
    Si no existe, se calcula, se guarda y se devuelve.

    Devuelve:
        text_features (Tensor: [num_categorias, dim])
        categories (List[str])
    """
    os.makedirs(embeddings_dir, exist_ok=True)

    # SHA256 del contenido del fichero de categorías
    file_hash = _sha256_file(categories_path)
    embeddings_path = os.path.join(embeddings_dir, f"{file_hash}.pt")

    # Leer categorías (siempre desde el fichero actual)
    categories = _read_categories(categories_path)

    if os.path.isfile(embeddings_path):
        data = torch.load(embeddings_path, map_location=_DEVICE, weights_only=True)
        text_features = data["text_features"].to(_DEVICE)
        # Opcionalmente podríamos usar data["categories"], pero leemos siempre de fichero.
        return text_features, categories

    # Si no existe, calculamos embeddings de texto
    model, _ = _load_clip_model()

    with torch.no_grad():
        # Tokenizar con open_clip
        tokens = open_clip.tokenize(categories).to(_DEVICE)
        text_features = model.encode_text(tokens)
        # Normalización L2 para usar similitud coseno
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)

    # Guardamos en disco
    torch.save(
        {"text_features": text_features.cpu(), "categories": categories},
        embeddings_path,
    )

    return text_features.to(_DEVICE), categories


# ------------------------------------------------------------
#   UTILIDADES: IMAGEN MÁS RECIENTE
# ------------------------------------------------------------

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}


def _get_latest_image_in_dir(image_dir: str) -> str:
    """
    Busca la imagen más reciente (por fecha de modificación) dentro
    de un directorio. Considera extensiones comunes de imagen.
    """
    if not os.path.isdir(image_dir):
        raise NotADirectoryError(f"La ruta proporcionada no es un directorio: {image_dir}")

    candidates = []
    for name in os.listdir(image_dir):
        full_path = os.path.join(image_dir, name)
        if os.path.isfile(full_path):
            _, ext = os.path.splitext(name)
            if ext.lower() in _IMAGE_EXTENSIONS:
                candidates.append(full_path)

    if not candidates:
        raise FileNotFoundError(f"No se han encontrado imágenes en el directorio: {image_dir}")

    # Imagen más reciente por fecha de modificación
    latest_image = max(candidates, key=os.path.getmtime)
    return latest_image


# ------------------------------------------------------------
#   FUNCIÓN PRINCIPAL: lookup_name
# ------------------------------------------------------------

def lookup_name(
    image_dir: str,
    categories_path: str = "/home/user/Integracio/image_processing/categories.txt",
    mapping_path: str = "/home/user/Integracio/image_processing/mapeo.json",
    embeddings_dir: str = "/home/user/Integracio/image_processing/embeddings",
) -> Tuple[str, Optional[str]]:
    """
    Dado un directorio con imágenes, lee la imagen más reciente,
    la clasifica con CLIP ViT-H-14 usando las categorías de 'categorías.txt',
    y devuelve una tupla (categoria_detectada, categoria_superior).

    - image_dir: ruta absoluta de la carpeta donde se guardan las imágenes.
    - categories_path: ruta al fichero 'categories.txt'.
    - mapping_path: ruta al fichero 'mapeo.json'.
    - embeddings_dir: directorio donde se guardan/leen los embeddings de texto.

    Ejemplo de retorno:
        ("manzana", "supermercadoURLs")
    """
    # 1. Cargar modelo
    model, preprocess = _load_clip_model()

    # 2. Cargar/crear embeddings de texto para las categorías
    text_features, categories = _load_or_create_text_embeddings(
        categories_path=categories_path,
        embeddings_dir=embeddings_dir,
    )

    # 3. Leer el mapeo JSON
    mapping = _read_mapping(mapping_path)

    # 4. Obtener la imagen más reciente del directorio
    latest_image_path = _get_latest_image_in_dir(image_dir)

    # 5. Preprocesar la imagen
    image = Image.open(latest_image_path).convert("RGB")
    image_tensor = preprocess(image).unsqueeze(0).to(_DEVICE)

    # 6. Extraer características de imagen y comparar con texto
    with torch.no_grad():
        image_features = model.encode_image(image_tensor)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)

        # Similitud coseno vía producto punto entre vectores normalizados
        # Resultado: [1, num_categorias]
        logits = (image_features @ text_features.T).squeeze(0)

        # Índice de la categoría más probable
        best_idx = int(torch.argmax(logits).item())

    detected_category = categories[best_idx]

    # 7. Buscar categoría superior en el mapeo
    upper_category = mapping.get(detected_category)

    # 8. Devolver tupla (categoria_detectada, categoria_superior)
    return detected_category, upper_category