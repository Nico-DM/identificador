import json
import logging
import re
from datetime import timezone

import dateparser
import requests
from bs4 import BeautifulSoup
from modelos import DateCandidate

logger = logging.getLogger(__name__)


def _to_naive_utc(dt):
    """Convierte cualquier datetime a naive UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _extract_ld_json_dates(soup):
    fechas = []
    for script in soup.find_all("script", type="application/ld+json"):
        text = script.string if script.string is not None else script.get_text()
        if not text or not text.strip():
            continue
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            try:
                parsed = json.loads("[" + text + "]")
            except json.JSONDecodeError:
                continue
        stack = [parsed]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        stack.append(value)
                    elif isinstance(value, str) and key.lower() in (
                        "datepublished",
                        "uploaddate",
                        "datecreated",
                    ):
                        fechas.append((value, "ld+json"))
            elif isinstance(node, list):
                for item in node:
                    if isinstance(item, (dict, list)):
                        stack.append(item)
    return fechas


def obtener_fechas_candidatas(html):
    soup = BeautifulSoup(html, "html.parser")
    fechas = []

    fechas.extend(_extract_ld_json_dates(soup))

    # 1. Etiquetas <time>
    for time_tag in soup.find_all("time"):
        if time_tag.get("datetime"):  # type: ignore
            fechas.append((time_tag["datetime"], "time"))  # type: ignore
        elif time_tag.text:
            fechas.append((time_tag.text.strip(), "time"))

    # 2. Metadatos comunes
    metas = [
        "article:published_time",
        "og:published_time",
        "date",
        "dc.date",
        "dc.date.issued",
        "pubdate",
        "publish-date",
        "datePublished",
    ]
    for meta in soup.find_all("meta"):
        name = meta.get("name", "").lower()  # type: ignore
        prop = meta.get("property", "").lower()  # type: ignore
        value = meta.get("content") or meta.get("value")  # type: ignore
        if value and (name in metas or prop in metas):
            fechas.append((value, "meta"))

    # 3. Texto plano
    texto = soup.get_text()
    patrones = re.findall(
        r"\b(\d{1,2} de \w+ de \d{4}|\w+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})\b",
        texto,
        re.IGNORECASE,
    )
    for p in patrones:
        fechas.append((p, "texto"))

    return fechas


def obtener_candidatas_estaticas(url: str) -> list[DateCandidate]:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return []
        html = r.text
        fechas_raw = obtener_fechas_candidatas(html)
        candidates: list[DateCandidate] = []
        for texto, fuente in fechas_raw:
            fecha = dateparser.parse(texto)
            if not fecha:
                continue
            fecha_naive = _to_naive_utc(fecha)
            if fecha_naive is None:
                continue
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
    except requests.RequestException:
        logger.debug("Scrape estatico fallido para %s", url, exc_info=True)
        return []
