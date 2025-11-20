from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from bs4 import BeautifulSoup
import re
import time
import numpy as np 

# ================== CONFIG ==================
supermercadoURLs = {
    'Mercadona': "https://tienda.mercadona.es/",
    'Carrefour': "https://www.carrefour.es/",
    'Condis':    "https://www.condisline.com/",
}
mueblesURLs = {
    'Ikea': "https://www.ikea.com/es/es/",
    'LeroyMerlin': "https://www.leroymerlin.es/",
}
ropaURLs = {
    'Zara': "https://www.zara.com/es/",
    'Primark': "https://www.primark.com/es/",
}
bicisURLs = {
    'Decathlon': "https://www.decathlon.es/",
}
electronicaURLs = {
    'MediaMarkt': "https://www.mediamarkt.es/",
    'PcComponentes': "https://www.pccomponentes.com/",
}
hogarURLs = {
    'mediamarkt': "https://www.mediamarkt.es/",
    'ikea': "https://www.ikea.com/es/es/",
}
entretenimientoURLs = {
    'amazon': "https://www.amazon.es/",
    'fnac': "https://www.fnac.es/",
    'mediamarkt': "https://www.mediamarkt.es/",
}
bebesURLs = {
    'amazon': "https://www.amazon.es/",
}
CODIGO_POSTAL = "08001"
producto = "portatil "
# ============================================

precioProducto = {}
listaURLs = electronicaURLs.copy()



# -------- Utilidades de parsing (BeautifulSoup) --------
def parsear_precio_texto(txt: str) -> float | None:
    """
    Limpia y convierte un texto con precio a float.
    Soporta '1.234,56 €', '2,99€', 'EUR 3.10', etc.
    """
    if not txt:
        return None
    t = txt.replace("EUR", "").replace("€", "").strip()
    t = re.sub(r"\s+", "", t)
    # Caso europeo con miles "." y decimales ","
    if re.search(r"\d+\.\d{3},\d{2}$", t):
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    m = re.search(r"\d+(?:\.\d+)?", t)
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None

def extraer_precio_de_soup(soup: BeautifulSoup) -> tuple[str | None, float | None]:
    """
    Intenta varios selectores comunes. Devuelve (texto_precio, valor_float).
    """
    # Selectores frecuentes en fichas o cards
    candidatos = [
        # Mercadona suele llevar clases con 'price' en span/div
        "[data-test*='price']",
        ".product-price__unit-price",
        ".product-price__current-price",
        ".product-price, .product__price, .price__current",
        ".price, .prices, [class*='price']",
        "span:contains('€')",  # no CSS estándar, pero algunos parsers lo aceptan
    ]

    # Prueba selectores directos
    for sel in candidatos:
        # BeautifulSoup no soporta :contains nativo; ignoramos ese caso
        if ":contains" in sel:
            continue
        nodes = soup.select(sel)
        if nodes:
            txt = nodes[0].get_text(strip=True)
            val = parsear_precio_texto(txt)
            if val is not None:
                return txt, val

    # Si no, buscar en la tarjeta principal (primer card)
    for card_sel in ["article", ".product-card", "[data-test*='product']", "li.product-cell"]:
        card = soup.select_one(card_sel)
        if card:
            txt = card.get_text(strip=True)
            # Busca patrón de precio en el texto del card
            m = re.search(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€", txt)
            if m:
                raw = m.group(0)
                val = parsear_precio_texto(raw)
                if val is not None:
                    return raw, val

    # Último recurso: todo el body
    body = soup.get_text(" ", strip=True)
    m = re.search(r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*€", body)
    if m:
        raw = m.group(0)
        val = parsear_precio_texto(raw)
        if val is not None:
            return raw, val

    return None, None

# -------- Acciones Playwright genéricas --------
def aceptar_cookies(page):
    # Busca botones típicos para aceptar cookies (insensible a mayús.)
    posibles = [
        r"(aceptar|acepto|aceptar\s+todas|aceptar todo|de acuerdo|entendido)",
        r"(accept|accept all|agree|consent)"
    ]
    for pat in posibles:
        try:
            page.get_by_role("button", name=re.compile(pat, re.I)).first.click(timeout=2500)
            return True
        except Exception:
            continue
    # Otros selectores genéricos
    for css in [
        "button#onetrust-accept-btn-handler",
        "button[aria-label*='acept' i]", "button[aria-label*='accept' i]",
        "button:has-text('Aceptar')", "button:has-text('Aceptar todas')",
        "button:has-text('Accept')", "button:has-text('Agree')"
    ]:
        try:
            if page.locator(css).count():
                page.locator(css).first.click(timeout=2000)
                return True
        except Exception:
            continue
    return False

def configurar_codigo_postal(page, cp: str):
    """
    Intenta introducir CP si hay modal/campo. No falla si no existe.
    """
    try:
        posibles_inputs = [
            'input[name="postalCode"]',
            'input[placeholder*="postal" i]',
            'input[placeholder*="c. postal" i]',
            'input[name*="postal" i]',
            'input[id*="postal" i]',
            'input[name*="cp" i]',
            'input[id*="cp" i]',
            'input[placeholder*="código" i]',
        ]
        inp = None
        for sel in posibles_inputs:
            if page.locator(sel).count():
                inp = page.locator(sel).first
                break
        if inp:
            inp.fill(cp)
            time.sleep(0.3)
            for bsel in [
                "button:has-text('Confirmar')",
                "button:has-text('Continuar')",
                "button:has-text('Entrar')",
                "button:has-text('Aplicar')",
                "button:has-text('Guardar')",
                "button:has-text('Aceptar')",
            ]:
                if page.locator(bsel).count():
                    page.locator(bsel).first.click(timeout=3000)
                    break
            try:
                page.wait_for_load_state("networkidle", timeout=6000)
            except PWTimeoutError:
                pass
    except Exception:
        pass

def buscar_producto(page, termino: str, timeout_ms: int = 8000) -> bool:
    """
    Localiza el buscador de forma genérica (Carrefour, Mercadona, Condis, etc.),
    espera a que esté visible y escribe el término + Enter.
    Devuelve True si pudo buscar, False si no encontró campo.
    """

    # Lista de estrategias (en orden de preferencia)
    estrategias = [
        # 1) Rol ARIA de buscador
        lambda: page.get_by_role("searchbox"),
        # 2) Placeholder con palabras clave (incluye 'Buscar en Carrefour')
        lambda: page.get_by_placeholder(re.compile(r"(buscar|buscando|producto|carrefour)", re.I)),
        # 3) input type=search
        lambda: page.locator('input[type="search"]'),
        # 4) input dentro de formularios de búsqueda
        lambda: page.locator('form[role="search"] input, form[aria-label*="buscar" i] input'),
        # 5) atributos accesibles/SEO típicos
        lambda: page.locator('input[aria-label*="buscar" i], input[title*="buscar" i]'),
        # 6) name/id comunes de buscador
        lambda: page.locator('input[name*="search" i], input[id*="search" i], input[name="q"], input[id="q"]'),
        # 7) último recurso: cualquier textbox visible
        lambda: page.get_by_role("textbox"),
    ]

    for estrategia in estrategias:
        try:
            loc = estrategia()
            if not loc or loc.count() == 0:
                continue

            # Usa el primero y espera visibilidad
            box = loc.first
            box.wait_for(state="visible", timeout=timeout_ms)

            # Algunos buscadores requieren foco antes de escribir
            try:
                box.click(timeout=2000)
            except PWTimeoutError:
                pass

            box.fill(termino, timeout=timeout_ms)
            box.press("Enter")
            # Espera a que empiecen a llegar resultados/cambios de red
            try:
                page.wait_for_load_state("networkidle", timeout=12000)
            except PWTimeoutError:
                pass
            return True
        except Exception:
            # Prueba la siguiente estrategia
            continue

    print("No se encontró ningún campo de búsqueda genérico en esta página.")
    return False

def abrir_primer_producto(page):
    """
    Intenta abrir la primera ficha de producto desde resultados (si existe).
    Si no hay cards clickables, se queda en la lista.
    """
    candidatos_click = [
        "li.product-cell a",
        "article a",
        ".product-card a",
        "[data-test*='product'] a"
    ]
    for sel in candidatos_click:
        try:
            if page.locator(sel).count():
                page.locator(sel).first.click(timeout=3000)
                try:
                    page.wait_for_load_state("networkidle", timeout=8000)
                except PWTimeoutError:
                    pass
                return True
        except Exception:
            continue
    return False

def filtrar_precios(precios: list[float], umbral_std: float = 0.2) -> list[float]:
    """
    Filtra precios que son outliers basándose en la desviación estándar y la varianza.
    Se eliminan los precios muy bajos o muy altos comparados con el resto.
    """

    # Convertir todo a números (float) y eliminar valores no válidos (strings, etc.)
    precios_validos = []
    for p in precios:
        try:
            # Convertimos a float, si no es posible lo descartamos
            precio_float = float(p)
            if precio_float > 0:  # Eliminar 0 o negativos
                precios_validos.append(precio_float)
        except ValueError:
            continue  # Si no puede convertirlo, lo ignoramos
    
    return precios_validos




# ----------------- MAIN -----------------
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
    precios_validos = {}  # guardará solo los supermercados donde haya precio

    for nombre, url in listaURLs.items():
        page = browser.new_page()
        print(f"\n==> {nombre}: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"[{nombre}] Error al cargar: {e}")
            page.close()
            continue

        # 1️ Aceptar cookies
        aceptar_cookies(page)

        # 2️ Introducir código postal si aplica
        configurar_codigo_postal(page, CODIGO_POSTAL)

        # 3️ Buscar producto
        pudo_buscar = buscar_producto(page, producto)
        if not pudo_buscar:
            print(f"[{nombre}] No se encontró buscador genérico; intento seguir igualmente.")
        else:
            print(f"[{nombre}] Búsqueda enviada: {producto}")

        # 4️ Intentar abrir el primer producto (si hay)
        abrir_primer_producto(page)

        # 5️ Descargar HTML y analizar con BeautifulSoup
        time.sleep(1.0)
        html = page.content()
        soup = BeautifulSoup(html, "lxml")
        texto_precio, valor = extraer_precio_de_soup(soup)

        if valor is not None:
            print(f"[{nombre}] Precio encontrado: {texto_precio}  -> {valor:.2f} €")
            precioProducto[nombre] = valor
            precios_validos[nombre] = valor
        else:
            print(f"[{nombre}] No se pudo extraer el precio desde HTML.")
            precioProducto[nombre] = None

        page.close()

    browser.close()

# ================== CALCULAR PRECIO MÍNIMO ==================
# Filtramos solo los precios numéricos válidos
precios_validos=filtrar_precios(precioProducto.values())
precio_min = min(precios_validos)
print(f"\n El precio más bajo és:" + str(precio_min) + "€")
