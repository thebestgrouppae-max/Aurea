from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
# with sync_playwright() as p:
#    browser = p.chromium.launch(headless=True)
#   page = browser.new_page()
#   page.goto("https://ca.wikipedia.org/wiki/Lionel_Andr%C3%A9s_Messi")
#   html = page.content()
#   browser.close()

#soup = BeautifulSoup(html, "lxml")
#print("Título de la página:", soup.title.string)
urls = {
        'Mercadona':  "https://tienda.mercadona.es/",  
        'Caprabo': "https://www.capraboacasa.com/",
        'Dia': "https://www.dia.es/"
}

CODIGO_POSTAL = "08001"  # 👉 pon aquí el que quieras


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=True = invisible, False = visible
    page = browser.new_page()
    page.goto(URL1, wait_until="networkidle")

    # Espera a que aparezca el cuadro del código postal
    try:
        page.wait_for_selector("input[name='postalCode']", timeout=5000)
        print("Se encontró el campo del código postal.")
        page.fill("input[name='postalCode']", CODIGO_POSTAL)
        time.sleep(0.5)
        # Botón de confirmar o continuar
        page.click("button:has-text('Continuar')")  # o 'Confirmar' / 'Aceptar' según el texto
        print("Código postal introducido y confirmado.")
        page.wait_for_selector("input[placeholder='Buscar productos']")
        page.fill("input[placeholder='Buscar productos']", "queso de burgos")  # 🔍 Cambia por el nombre que quieras
        page.keyboard.press("Enter")
        # Espera a que carguen los resultados
        page.wait_for_selector("li.product-cell", timeout=10000)
        # Haz clic en el primer resultado de la búsqueda
        page.click("li.product-cell a")  # Abre el producto

    except Exception:
        print("No se encontró el cuadro del código postal (quizás ya estaba guardado).")

    # Espera unos segundos para que cargue el producto
    page.wait_for_timeout(3000)
    html = page.content()
    browser.close()

# Analizamos el HTML con BeautifulSoup
soup = BeautifulSoup(html, "lxml")
precio = soup.find("p", class_="product-price__unit-price")

if precio:
    print("Precio del producto:", precio.get_text(strip=True))
else:
    print("No se encontró el precio en la página.")
