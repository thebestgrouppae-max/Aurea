from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time

listaURLs = {
       'Mercadona': "https://tienda.mercadona.es/",
       'Condis':  "https://www.condisline.com/",  
       #'Caprabo': "https://www.capraboacasa.com/",
       # 'Dia': "https://www.dia.es/"
}

precioProducto = {
    'Condis': "1,99 €",
}

CODIGO_POSTAL = "08001"  
producto = "arroz "
def codigoPostal(page, codigo_postal: str):
    try:
        page.wait_for_selector("input[name='postalCode']", timeout=5000)
        print("Se encontró el campo del código postal.")
        page.fill("input[name='postalCode']", CODIGO_POSTAL)
        time.sleep(0.5)
        # Botón de confirmar o continuar
        page.click("button:has-text('Continuar')")  # o 'Confirmar' / 'Aceptar' según el texto
        print("Código postal introducido y confirmado.")
    except: print("No se encontró el campo del código postal.")

def buscar_producto(page, producto: str):

    #  Intenta inputs tipo "search"
    if page.locator('input[type="search"]').count() > 0:
        buscador = page.locator('input[type="search"]').first

    #  Busca placeholders que contengan palabras comunes
    elif page.locator('input[placeholder*="Buscar Producto" i]').count() > 0:
        buscador = page.locator('input[placeholder*="buscar" i]').first

    elif page.locator('input[placeholder*="buscando" i]').count() > 0:
        buscador = page.locator('input[placeholder*="buscando" i]').first

    elif page.locator('input[placeholder*="producto" i]').count() > 0:
        buscador = page.locator('input[placeholder*="producto" i]').first

    # Si hay un input visible sin placeholder (vacío)
    elif page.locator('input:not([placeholder])').count() > 0:
        buscador = page.locator('input:not([placeholder])').first

    # 4Último recurso: cualquier textbox visible
    elif page.get_by_role("textbox").count() > 0:
        buscador = page.get_by_role("textbox").first

    else:
        print("No se encontró ningún campo de búsqueda en esta página.")
        return

    #  Escribir el producto y enviar
    buscador.fill(producto)
    buscador.press("Enter")

    #  Esperar un poco para que carguen los resultados
    page.wait_for_timeout(3000)
    print(f"Se buscó '{producto}' correctamente.")



with sync_playwright() as p:

    for nombre, url in listaURLs.items():
        browser = p.chromium.launch(headless=False)  # headless=True = invisible, False = visible
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        try: 
            codigoPostal(page, CODIGO_POSTAL)
            #buscar_producto(page, producto)
            page.wait_for_selector("input[placeholder='Buscar productos']")
            page.fill("input[placeholder='Buscar productos']", "queso de burgos")  # 🔍 Cambia por el nombre que quieras
            page.keyboard.press("Enter")
            # Espera a que carguen los resultados
            page.wait_for_selector("li.product-cell", timeout=10000)
            # Haz clic en el primer resultado de la búsqueda
            page.click("li.product-cell a")  # Abre el producto
        except Exception:
            print("")
        
        page.wait_for_timeout(3000)
        html = page.content()
        browser.close()
        
        # Analizamos el HTML con BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        precio = soup.find("p", class_="product-price__unit-price")
        print("EL precio del producto en", nombre, "es", precio.get_text(strip=True))
        precioProducto[nombre] = precio.get_text(strip=True) 
        #if precio:
        #    print("Precio del producto en", nombre, "es", precio.get_text(strip=True))
        #else:
        #    print("BBB")

#print("El precio más barato es de", min(precioProducto.values()))
