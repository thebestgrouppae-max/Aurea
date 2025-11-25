# -*- coding: utf-8 -*-
"""
API Flask de salarios con scraping Selenium (InfoJobs) + fallback a base de datos local
MODIFICADO: Ahora devuelve salario empleado + coste empresa
Arranque: python salary_api.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import unicodedata
import urllib.parse
import time
import multiprocessing

PROVINCIA = "barcelona"
# ---------- Base de datos local ----------
SALARY_DATA = {
    "mozo" : {"min": 18000, "max": 35755, "avg": 23000},
    "desarrollador web": {"min": 25000, "max": 50000, "avg": 37500},
    "desarrollador": {"min": 25000, "max": 50000, "avg": 37500},
    "programador": {"min": 21000, "max": 40000, "avg": 30500},
    "ingeniero informático": {"min": 35000, "max": 80000, "avg": 57500},
    "ingeniero de software": {"min": 40000, "max": 100000, "avg": 70000},
    "arquitecto de software": {"min": 50000, "max": 90000, "avg": 70000},
    "experto en ciberseguridad": {"min": 50000, "max": 120000, "avg": 85000},
    "analista de datos": {"min": 35000, "max": 70000, "avg": 52500},
    "arquitecto cloud": {"min": 60000, "max": 100000, "avg": 80000},
    "full stack developer": {"min": 30000, "max": 65000, "avg": 47500},
    "médico especialista": {"min": 60000, "max": 150000, "avg": 105000},
    "médico": {"min": 45000, "max": 80000, "avg": 62500},
    "cirujano": {"min": 90000, "max": 150000, "avg": 120000},
    "cardiólogo": {"min": 90000, "max": 150000, "avg": 120000},
    "anestesista": {"min": 80000, "max": 150000, "avg": 115000},
    "dermatólogo": {"min": 80000, "max": 120000, "avg": 100000},
    "pediatra": {"min": 65000, "max": 95000, "avg": 80000},
    "enfermero": {"min": 24000, "max": 45000, "avg": 34500},
    "enfermera": {"min": 24000, "max": 45000, "avg": 34500},
    "fisioterapeuta": {"min": 22000, "max": 35000, "avg": 28500},
    "ingeniero industrial": {"min": 40000, "max": 70000, "avg": 55000},
    "ingeniero": {"min": 30000, "max": 55000, "avg": 42500},
    "ingeniero civil": {"min": 35000, "max": 60000, "avg": 47500},
    "ingeniero eléctrico": {"min": 35000, "max": 65000, "avg": 50000},
    "ingeniero químico": {"min": 35000, "max": 70000, "avg": 52500},
    "ingeniero aeroespacial": {"min": 35000, "max": 75000, "avg": 55000},
    "arquitecto": {"min": 28000, "max": 50000, "avg": 39000},
    "aparejador": {"min": 25000, "max": 45000, "avg": 35000},
    "jefe de obra": {"min": 35000, "max": 60000, "avg": 47500},
    "topógrafo": {"min": 25000, "max": 45000, "avg": 35000},
    "abogado": {"min": 28000, "max": 65000, "avg": 46500},
    "abogado corporativo": {"min": 50000, "max": 100000, "avg": 75000},
    "notario": {"min": 60000, "max": 120000, "avg": 90000},
    "procurador": {"min": 25000, "max": 50000, "avg": 37500},
    "legal counsel": {"min": 45000, "max": 90000, "avg": 67500},
    "compliance officer": {"min": 55000, "max": 85000, "avg": 70000},
    "analista financiero": {"min": 35000, "max": 70000, "avg": 52500},
    "director financiero": {"min": 80000, "max": 140000, "avg": 110000},
    "gestor de fondos": {"min": 60000, "max": 110000, "avg": 85000},
    "asesor financiero": {"min": 25000, "max": 50000, "avg": 37500},
    "controller": {"min": 40000, "max": 70000, "avg": 55000},
    "auditor": {"min": 28000, "max": 55000, "avg": 41500},
    "actuario": {"min": 55000, "max": 85000, "avg": 70000},
    "profesor": {"min": 24000, "max": 35000, "avg": 29500},
    "maestro": {"min": 22000, "max": 32000, "avg": 27000},
    "profesor universitario": {"min": 35000, "max": 80000, "avg": 57500},
    "director de colegio": {"min": 45000, "max": 70000, "avg": 57500},
    "comercial": {"min": 20000, "max": 40000, "avg": 30000},
    "director comercial": {"min": 60000, "max": 140000, "avg": 100000},
    "director de marketing": {"min": 50000, "max": 95000, "avg": 72500},
    "marketing digital": {"min": 25000, "max": 50000, "avg": 37500},
    "community manager": {"min": 18000, "max": 30000, "avg": 24000},
    "growth manager": {"min": 45000, "max": 90000, "avg": 67500},
    "técnico de recursos humanos": {"min": 22000, "max": 35000, "avg": 28500},
    "director de recursos humanos": {"min": 50000, "max": 90000, "avg": 70000},
    "hr manager": {"min": 40000, "max": 100000, "avg": 70000},
    "consultor de rrhh": {"min": 30000, "max": 55000, "avg": 42500},
    "administrativo": {"min": 18000, "max": 28000, "avg": 23000},
    "auxiliar administrativo": {"min": 16000, "max": 24000, "avg": 20000},
    "secretario": {"min": 18000, "max": 30000, "avg": 24000},
    "contable": {"min": 22000, "max": 40000, "avg": 31000},
    "técnico contable": {"min": 20000, "max": 35000, "avg": 27500},
    "diseñador gráfico": {"min": 18000, "max": 35000, "avg": 26500},
    "diseñador": {"min": 18000, "max": 38000, "avg": 28000},
    "diseñador web": {"min": 22000, "max": 40000, "avg": 31000},
    "director de arte": {"min": 30000, "max": 55000, "avg": 42500},
    "fotógrafo": {"min": 15000, "max": 35000, "avg": 25000},
    "camarero": {"min": 16000, "max": 25000, "avg": 20500},
    "cocinero": {"min": 16000, "max": 30000, "avg": 23000},
    "chef": {"min": 25000, "max": 50000, "avg": 37500},
    "recepcionista": {"min": 16000, "max": 24000, "avg": 20000},
    "guía turístico": {"min": 18000, "max": 28000, "avg": 23000},
    "conductor": {"min": 18000, "max": 28000, "avg": 23000},
    "piloto": {"min": 50000, "max": 150000, "avg": 100000},
    "controlador aéreo": {"min": 60000, "max": 120000, "avg": 90000},
    "logístico": {"min": 22000, "max": 40000, "avg": 31000},
    "vendedor": {"min": 16000, "max": 28000, "avg": 22000},
    "dependiente": {"min": 15000, "max": 22000, "avg": 18500},
    "jefe de ventas": {"min": 35000, "max": 70000, "avg": 52500},
    "retail manager": {"min": 40000, "max": 120000, "avg": 80000},
    "periodista": {"min": 20000, "max": 35000, "avg": 27500},
    "editor": {"min": 22000, "max": 40000, "avg": 31000},
    "relaciones públicas": {"min": 25000, "max": 50000, "avg": 37500},
    "social media manager": {"min": 20000, "max": 35000, "avg": 27500},
    "operario": {"min": 16000, "max": 25000, "avg": 20500},
    "técnico de mantenimiento": {"min": 20000, "max": 35000, "avg": 27500},
    "supervisor de producción": {"min": 30000, "max": 50000, "avg": 40000},
    "jefe de planta": {"min": 40000, "max": 70000, "avg": 55000},
    "trabajador social": {"min": 20000, "max": 32000, "avg": 26000},
    "psicólogo": {"min": 22000, "max": 45000, "avg": 33500},
    "educador social": {"min": 18000, "max": 30000, "avg": 24000},
    "vigilante de seguridad": {"min": 16000, "max": 24000, "avg": 20000},
    "policía": {"min": 25000, "max": 40000, "avg": 32500},
    "bombero": {"min": 28000, "max": 45000, "avg": 36500},
    "biólogo": {"min": 22000, "max": 40000, "avg": 31000},
    "químico": {"min": 25000, "max": 45000, "avg": 35000},
    "físico": {"min": 25000, "max": 50000, "avg": 37500},
    "investigador": {"min": 28000, "max": 55000, "avg": 41500},
    "farmacéutico": {"min": 30000, "max": 55000, "avg": 42500},
    "técnico farmacia": {"min": 18000, "max": 28000, "avg": 23000},
    "consultor": {"min": 35000, "max": 80000, "avg": 57500},
    "consultor estratégico": {"min": 50000, "max": 90000, "avg": 70000},
    "consultor it": {"min": 40000, "max": 75000, "avg": 57500},
    "entrenador personal": {"min": 15000, "max": 35000, "avg": 25000},
    "entrenador": {"min": 15000, "max": 35000, "avg": 25000},
    "profesor de educación física": {"min": 22000, "max": 32000, "avg": 27000},
    "electricista": {"min": 20000, "max": 35000, "avg": 27500},
    "fontanero": {"min": 18000, "max": 32000, "avg": 25000},
    "carpintero": {"min": 18000, "max": 35000, "avg": 26500},
    "mecánico": {"min": 18000, "max": 30000, "avg": 24000},
    "soldador": {"min": 20000, "max": 35000, "avg": 27500},
    "director general": {"min": 100000, "max": 250000, "avg": 175000},
    "ceo": {"min": 100000, "max": 300000, "avg": 200000},
    "cto": {"min": 70000, "max": 120000, "avg": 95000},
    "cfo": {"min": 80000, "max": 140000, "avg": 110000}
}

# ---------- Utilidades ----------
def normalize_text(s: str) -> str:
    s = s.lower().strip()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def lookup_salary(job_title: str):
    key = normalize_text(job_title)
    # Coincidencia exacta
    if key in SALARY_DATA:
        return SALARY_DATA[key]
    # Coincidencia por substring
    #for k, v in SALARY_DATA.items():
    #    k_norm = normalize_text(k)
    #    if key in k_norm or k_norm in key:
    #        return v
    # Coincidencia por palabras principales (split)
    #palabras = key.split()
    #for k, v in SALARY_DATA.items():
    #    k_norm = normalize_text(k)
    #    for palabra in palabras:
    #        if palabra in k_norm:
    #            return v
    return None


# ---------- Selenium ----------
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def create_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    driver = webdriver.Chrome(options=opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def scrape_infojobs_salary(job_title, queue):
    driver = None
    try:
        job = urllib.parse.quote(normalize_text(job_title).replace(" ", "-").replace("/", "-"))
        loc = urllib.parse.quote(normalize_text(PROVINCIA).replace(" ", "-"))
        url = f"https://salarios.infojobs.net/{job}/{loc}"
        
        driver = create_driver()
        driver.get(url)
        
        el = WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.ID, "jsGraphData")))
        min_v = el.get_attribute("data-min")
        max_v = el.get_attribute("data-max")
        avg_v = el.get_attribute("data-avg")
        
        if not (min_v and max_v and avg_v):
            return None
            
        # Los datos vienen en miles (p. ej. 19.040 => 19.040k €/año)
        min_eur = int(float(min_v) * 1000)
        max_eur = int(float(max_v) * 1000)
        avg_eur = int(float(avg_v) * 1000)
        
        queue.put({"min": min_eur, "max": max_eur, "avg": avg_eur, "source": "scraping"})
        return None
        
    except Exception:
        return None
    finally:
        if driver:
            driver.quit()

# ---------- API ----------
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["*"], "methods": ["GET","POST","OPTIONS"], "allow_headers": ["Content-Type","Authorization"]}})

def compute_cost_per_hour(salary_eur_year, factor_coste=1.30, horas_anuales=1760):
    coste_total = salary_eur_year * factor_coste
    return round(coste_total / float(horas_anuales), 2)

@app.route("/")
def home():
    return """
<h2>🚀 API de Salarios MODIFICADA - Empleado + Empresa</h2>
<p>GET /api/salary?job_title=jardinero&location=barcelona&factor_coste=1.3&horas_anuales=1760</p>
"""

@app.route("/api/salary", methods=["GET","POST","OPTIONS"])
def api_salary():
    if request.method == "OPTIONS":
        return "", 204
    
    if request.method == "POST":
        data = request.get_json() or {}
        job_title = (data.get("job_title") or "").strip()
        factor_coste = float(data.get("factor_coste", 1.30))
        horas_anuales = int(data.get("horas_anuales", 1760))
    else:
        job_title = (request.args.get("job_title") or "").strip()
        factor_coste = float(request.args.get("factor_coste", 1.30))
        horas_anuales = int(request.args.get("horas_anuales", 1760))
    
    if not job_title:
        return jsonify({"success": False, "error": "job_title es obligatorio"}), 400

    # 1) Scraping
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=scrape_infojobs_salary, args=(job_title, queue))
    p.start()
    p.join(10)
    if p.is_alive():
        p.terminate()
        p.join()
        scraped = None
    else:
        scraped = queue.get()
    #time.sleep(0.3)
    #scraped = scrape_infojobs_salary(job_title, location)
    
    # 2) Fallback a base local si no hay scraping
    if not scraped:
        local = lookup_salary(job_title)
        if not local:
            return jsonify({
                "success": False,
                "error": "No hay datos (ni en internet ni en base local)",
                "job_title": job_title,
                "location": PROVINCIA
            }), 404
        
        source = "base_local"
        salary_pack = {"min": local["min"], "max": local["max"], "avg": local["avg"]}
    else:
        source = "scraping_infojobs"
        salary_pack = {"min": scraped["min"], "max": scraped["max"], "avg": scraped["avg"]}

    # MODIFICACIÓN: Calcular salario empleado + coste empresa
    # Salario empleado (original)
    salary_employee = {
        "annual_min": salary_pack["min"],
        "annual_avg": salary_pack["avg"],
        "annual_max": salary_pack["max"],
        "hour_min": round(salary_pack["min"] / horas_anuales, 2),
        "hour_avg": round(salary_pack["avg"] / horas_anuales, 2),
        "hour_max": round(salary_pack["max"] / horas_anuales, 2),
        "currency": "EUR"
    }

    # Coste para la empresa (con factor de coste aplicado)
    coste_hora_min = compute_cost_per_hour(salary_pack["min"], factor_coste, horas_anuales)
    coste_hora_avg = compute_cost_per_hour(salary_pack["avg"], factor_coste, horas_anuales)
    coste_hora_max = compute_cost_per_hour(salary_pack["max"], factor_coste, horas_anuales)
    
    return jsonify({
        "success": True,
        "job_title": job_title,
        "location": normalize_text(PROVINCIA),
        
        # NUEVO: Salario del empleado (sin factor coste)
        "salary_employee": salary_employee,
        
        # EXISTENTE: Datos compatibles con frontend anterior (coste empresa)
        "salary_data": {
            "minimum": coste_hora_min,
            "average": coste_hora_avg,
            "maximum": coste_hora_max,
            "currency": "EUR",
            "period": "annual"
        },
        "company_cost": {
            "factor_coste": factor_coste,
            "horas_anuales": horas_anuales,
            "coste_hora_min": coste_hora_min,
            "coste_hora_avg": coste_hora_avg,
            "coste_hora_max": coste_hora_max
        },
        "source": source,
        "api_version": "4.0-employee-company-split"
    })

@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "message": "API OK - Employee + Company", "cors_enabled": True})

if __name__ == "__main__":
    print("URL test: http://localhost:5000/api/salary?job_title=programador&location=barcelona")
    app.run(host="localhost", port=5000, debug=True)
