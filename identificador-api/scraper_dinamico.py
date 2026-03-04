from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dateutil import parser
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import re, json, time
from typing import List

from modelos import DateCandidate

ISO_DATETIME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+\-]\d{2}:?\d{2})?"
)
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
VERBOSE_DATE_RE = re.compile(r"\b\d{1,2} (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}\b", re.IGNORECASE)
GENERIC_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")

# prioridad: menor es mejor
SOURCE_PRIORITY = {
    "time": 1,
    "meta": 2,
    "ld+json": 3,
    "script-json": 4,
    "script-regex": 5,
    "visible-text": 6,
}

def _try_parse_date(text):
    try:
        d = parser.parse(text, fuzzy=False)
        return d
    except Exception:
        try:
            # menos estricto
            d = parser.parse(text, fuzzy=True)
            return d
        except Exception:
            return None

def _add_candidate(candidates, date_obj, source, raw, url):
    if date_obj is None:
        return
    candidates.append(
        DateCandidate(
            date=date_obj,
            source=source,
            raw=raw,
            extractor="dynamic",
            url=url,
        )
    )

# -------------------------
# Buscar time / meta elements
# -------------------------
def extract_from_dom(driver, url):
    candidates = []
    selectors_time = [
        'time[datetime]',
        'article time[datetime]',
        'div[role="article"] time[datetime]',
        'div[data-testid="tweet"] time',
        'a time[datetime]',
    ]
    for sel in selectors_time:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                dt = e.get_attribute("datetime") or e.get_attribute("dateTime") or e.text
                parsed = _try_parse_date(dt) if dt else None
                _add_candidate(candidates, parsed, "time", dt, url)
        except Exception:
            continue

    # metas
    meta_selectors = [
        "meta[property='article:published_time']",
        "meta[name='date']",
        "meta[name='pubdate']",
        "meta[name='publish-date']",
        "meta[name='DC.date.issued']",
        "meta[itemprop='datePublished']",
        "meta[property='og:updated_time']",
        "meta[name='twitter:label1']",
    ]
    for sel in meta_selectors:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                content = e.get_attribute("content") or e.get_attribute("value") or e.text
                parsed = _try_parse_date(content) if content else None
                _add_candidate(candidates, parsed, "meta", content, url)
        except Exception:
            continue

    return candidates

# -------------------------
# Buscar JSON/ld+json en <script>
# -------------------------
def extract_dates_from_scripts(driver, url):
    candidates = []
    soup = BeautifulSoup(driver.page_source, "html.parser")
    scripts = soup.find_all("script")
    for script in scripts:
        text = script.string if script.string is not None else script.get_text() # type: ignore
        if not text or text.strip() == "":
            continue

        # saltar scripts de cookies / trackers que contienen fechas de expiracion
        low = text.lower()
        if "document.cookie" in low or "expires=" in low or "max-age" in low or "setcookie" in low:
            continue

        # ld+json tipicos
        if script.get("type") == "application/ld+json": # type: ignore
            try:
                parsed_json = json.loads(text)
            except Exception:
                # intentar reparar arrays multiples (no critico)
                try:
                    parsed_json = json.loads("[" + text + "]")
                except Exception:
                    parsed_json = None
            if parsed_json is not None:
                # recorrer diccionario/array buscando claves con fechas
                stack = [parsed_json]
                while stack:
                    node = stack.pop()
                    if isinstance(node, dict):
                        for k, v in node.items():
                            if isinstance(v, (dict, list)):
                                stack.append(v)
                            elif isinstance(v, str):
                                # claves que habitualmente almacenan fecha
                                if k.lower() in ("datepublished", "uploaddate", "datecreated", "datepublished"):
                                    d = _try_parse_date(v)
                                    _add_candidate(candidates, d, "ld+json", v, url)
                                else:
                                    # tambien intentar si la cadena parece ISO
                                    if ISO_DATETIME_RE.search(v) or ISO_DATE_RE.search(v):
                                        d = _try_parse_date(v)
                                        _add_candidate(candidates, d, "ld+json", v, url)
                    elif isinstance(node, list):
                        for it in node:
                            if isinstance(it, (dict, list)):
                                stack.append(it)
                            elif isinstance(it, str):
                                if ISO_DATETIME_RE.search(it) or ISO_DATE_RE.search(it):
                                    d = _try_parse_date(it)
                                    _add_candidate(candidates, d, "ld+json", it, url)
            continue

        # si no es ld+json, buscar claves tipo "datePublished" dentro del texto (JSON incrustado)
        if "datePublished" in text or "created_at" in text or "dateCreated" in text:
            # primero intentar con regex para extraer valores entre comillas
            matches = re.findall(r'"(?:datePublished|uploadDate|created_at|dateCreated)"\s*:\s*"([^"]+)"', text)
            for m in matches:
                d = _try_parse_date(m)
                _add_candidate(candidates, d, "script-json", m, url)

            # tambien buscar ISO en el script si no hay matches
            iso_matches = ISO_DATETIME_RE.findall(text) + ISO_DATE_RE.findall(text)
            for m in iso_matches:
                d = _try_parse_date(m)
                _add_candidate(candidates, d, "script-regex", m, url)

    return candidates

# -------------------------
# Buscar en texto visible (limpiando scripts/styles)
# -------------------------
def extract_from_visible_text(driver, url):
    candidates = []
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    texto = soup.get_text(separator=" ")
    # buscar patrones
    for m in ISO_DATETIME_RE.findall(texto):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    for m in ISO_DATE_RE.findall(texto):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    for m in VERBOSE_DATE_RE.findall(texto):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    for m in GENERIC_DATE_RE.findall(texto):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    return candidates

# -------------------------
# Seleccionar mejor fecha con prioridad + distancia a hoy
# -------------------------
def seleccionar_mejor_fecha(candidates: List[DateCandidate]):
    if not candidates:
        return None

    hoy = datetime.now()
    # filtrar rango razonable
    filtered = []
    for c in candidates:
        d = c.date
        if d is None:
            continue
        if d.year < 2000:
            continue
        if d > hoy:
            # ignorar fechas futuras
            continue
        filtered.append(c)
    if not filtered:
        return None

    # ordenar por (prioridad, distancia_dias)
    for c in filtered:
        c_distance = abs((hoy - c.date).days)
        c.flags["distance_days"] = c_distance

    filtered.sort(key=lambda x: (SOURCE_PRIORITY.get(x.source, 99), x.flags.get("distance_days", 0)))
    best = filtered[0]
    return best

# -------------------------
# Función principal
# -------------------------
def obtener_candidatas_dinamicas(url, headless=True, timeout=20, wait_for=8) -> List[DateCandidate]:
    options = Options()
    if headless:
        # dependiendo de la version de Chrome, '--headless=new' puede funcionar; usar '--headless' por compatibilidad
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1920,1080")
    # establecer un UA realista
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={ua}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    # menor: aumentar timeouts si el sitio es lento
    driver.set_page_load_timeout(timeout)

    # ejecutar un pequeno script para ocultar webdriver
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
            """
            },
        )
    except Exception:
        pass

    try:
        driver.get(url)
        # esperar que el body exista
        WebDriverWait(driver, wait_for).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # dar tiempo extra para que JS renderice (scroll + sleeps)
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        candidates = []
        # 1) DOM (time/meta) - alta prioridad
        candidates += extract_from_dom(driver, url)
        # 2) scripts JSON / ld+json
        candidates += extract_dates_from_scripts(driver, url)
        # 3) texto visible
        candidates += extract_from_visible_text(driver, url)

        # removemos la informacion de zona horaria
        for c in candidates:
            if c.date.tzinfo:
                c.date = c.date.astimezone(timezone.utc).replace(tzinfo=None)

        return candidates

    except Exception:
        return []
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def obtener_fecha_dinamica(url, headless=True, timeout=20, wait_for=8):
    candidates = obtener_candidatas_dinamicas(url, headless=headless, timeout=timeout, wait_for=wait_for)
    best = seleccionar_mejor_fecha(candidates)
    return best.date if best else None


if __name__ == "__main__":
    url = "https://x.com/_Woong_Bi_/status/1940043620599603367"
    fecha = obtener_fecha_dinamica(url)
    print("Fecha extraída:", fecha)
