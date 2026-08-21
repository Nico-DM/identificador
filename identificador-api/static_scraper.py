import json
import logging
import re
from datetime import timezone

import dateparser
import requests
from bs4 import BeautifulSoup
from models import DateCandidate

logger = logging.getLogger(__name__)


def _to_naive_utc(dt):
    """Convert any datetime to naive UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _extract_ld_json_dates(soup):
    dates = []
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
                        dates.append((value, "ld+json"))
            elif isinstance(node, list):
                for item in node:
                    if isinstance(item, (dict, list)):
                        stack.append(item)
    return dates


def extract_candidate_dates(html):
    soup = BeautifulSoup(html, "html.parser")
    dates = []

    dates.extend(_extract_ld_json_dates(soup))

    # 1. <time> tags
    for time_tag in soup.find_all("time"):
        if time_tag.get("datetime"):  # type: ignore
            dates.append((time_tag["datetime"], "time"))  # type: ignore
        elif time_tag.text:
            dates.append((time_tag.text.strip(), "time"))

    # 2. Common metadata
    meta_names = [
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
        if value and (name in meta_names or prop in meta_names):
            dates.append((value, "meta"))

    # 3. Plain text
    visible_text = soup.get_text()
    patterns = re.findall(
        r"\b(\d{1,2} de \w+ de \d{4}|\w+ \d{1,2}, \d{4}|\d{4}-\d{2}-\d{2})\b",
        visible_text,
        re.IGNORECASE,
    )
    for match in patterns:
        dates.append((match, "plain-text"))

    return dates


def fetch_static_candidates(url: str) -> list[DateCandidate]:
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if r.status_code != 200:
            return []
        html = r.text
        raw_dates = extract_candidate_dates(html)
        candidates: list[DateCandidate] = []
        for text, source in raw_dates:
            parsed_date = dateparser.parse(text)
            if not parsed_date:
                continue
            naive_date = _to_naive_utc(parsed_date)
            if naive_date is None:
                continue
            candidates.append(
                DateCandidate(
                    date=naive_date,
                    source=source,
                    raw=text,
                    extractor="static",
                    url=url,
                )
            )
        return candidates
    except requests.RequestException:
        logger.debug("Static scrape failed for %s", url, exc_info=True)
        return []
