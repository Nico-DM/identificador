import requests
from bs4 import BeautifulSoup
import re
import dateparser
from datetime import datetime, timezone
from typing import List

from modelos import DateCandidate

def _to_naive_utc(dt):
    """Convierte cualquier datetime a naive UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def obtener_fechas_candidatas(html):
    soup = BeautifulSoup(html, "html.parser")
    fechas = []

    # 1. Etiquetas <time>
    for time_tag in soup.find_all("time"):
        if time_tag.get("datetime"): # type: ignore
            fechas.append((time_tag["datetime"], "time-datetime")) # type: ignore
        elif time_tag.text:
            fechas.append((time_tag.text.strip(), "time-text"))

    # 2. Metadatos comunes
    metas = [
        "article:published_time", "og:published_time", "date", "dc.date",
        "dc.date.issued", "pubdate", "publish-date", "datePublished"
    ]
    for meta in soup.find_all("meta"):
        name = meta.get("name", "").lower() # type: ignore
        prop = meta.get("property", "").lower() # type: ignore
        value = meta.get("content") or meta.get("value") # type: ignore
        if value:
            if name in metas or prop in metas:
                fechas.append((value, f"meta:{name or prop}"))

    # 3. Texto plano
    texto = soup.get_text()
    patrones = re.findall(
        r"\b(\d{1,2} de \w+ de \d{4}|\w+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})\b",
        texto, re.IGNORECASE
    )
    for p in patrones:
        fechas.append((p, "texto"))

    return fechas

def seleccionar_mejor_fecha(candidates: List[DateCandidate]):
    puntuadas = []
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    for c in candidates:
        fecha = c.date
        fecha_sin_tz = _to_naive_utc(fecha)
        if fecha_sin_tz and fecha_sin_tz <= now_naive:
            puntaje = 0
            if "published" in c.source or "datePublished" in c.source:
                puntaje += 3
            if "meta" in c.source:
                puntaje += 2
            if "time" in c.source:
                puntaje += 1
            puntuadas.append((fecha_sin_tz, puntaje))

    puntuadas.sort(key=lambda x: (-x[1], x[0]))  # mayor puntaje y mas antigua
    return puntuadas[0][0] if puntuadas else None

def obtener_candidatas_estaticas(url: str) -> List[DateCandidate]:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return []
        html = r.text
        fechas_raw = obtener_fechas_candidatas(html)
        candidates: List[DateCandidate] = []
        for texto, fuente in fechas_raw:
            fecha = dateparser.parse(texto)
            if not fecha:
                continue
            fecha_naive = _to_naive_utc(fecha)
            candidates.append(
                DateCandidate(
                    date=fecha_naive,
                    source=fuente,
                    raw=texto,
                    extractor="static",
                    url=url,
                )
            )
        return candidates
    except Exception:
        return []

def obtener_fecha_estatica(url):
    candidates = obtener_candidatas_estaticas(url)
    return seleccionar_mejor_fecha(candidates)


if __name__ == "__main__":
    url = "https://www.deviantart.com/qoentari/art/Dnd-gunslinger-character-1061655719"
    fecha = obtener_fecha_estatica(url)
    print("Fecha extraída:", fecha)