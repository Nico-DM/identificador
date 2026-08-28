import json
import logging
import re
import time
from datetime import timezone

from bs4 import BeautifulSoup
from dateutil import parser
from dateutil.parser import ParserError
from models import DateCandidate
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

logger = logging.getLogger(__name__)


def _to_naive_utc(dt):
    """Convert any datetime to naive UTC."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


ISO_DATETIME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+\-]\d{2}:?\d{2})?"
)
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
VERBOSE_DATE_RE = re.compile(
    r"\b\d{1,2} (?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}\b",
    re.IGNORECASE,
)
GENERIC_DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b")


def _try_parse_date(text):
    parse_errors = (ParserError, OverflowError, TypeError, ValueError)
    try:
        return parser.parse(text, fuzzy=False)
    except parse_errors:
        try:
            return parser.parse(text, fuzzy=True)
        except parse_errors:
            return None


def _add_candidate(candidates, date_obj, source, raw, url):
    if date_obj is None:
        return
    date_naive = _to_naive_utc(date_obj)
    if date_naive is None:
        return
    candidates.append(
        DateCandidate(
            date=date_naive,
            source=source,
            raw=raw,
            extractor="dynamic",
            url=url,
        )
    )


def extract_from_dom(driver, url):
    candidates = []
    selectors_time = [
        "time[datetime]",
        "article time[datetime]",
        'div[role="article"] time[datetime]',
        'div[data-testid="tweet"] time',
        "a time[datetime]",
    ]
    for sel in selectors_time:
        try:
            elems = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in elems:
                dt = (
                    e.get_attribute("datetime") or e.get_attribute("dateTime") or e.text
                )
                parsed = _try_parse_date(dt) if dt else None
                _add_candidate(candidates, parsed, "time", dt, url)
        except WebDriverException:
            logger.debug("Time selector failed %s on %s", sel, url, exc_info=True)
            continue

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
                content = (
                    e.get_attribute("content") or e.get_attribute("value") or e.text
                )
                parsed = _try_parse_date(content) if content else None
                _add_candidate(candidates, parsed, "meta", content, url)
        except WebDriverException:
            logger.debug("Meta selector failed %s on %s", sel, url, exc_info=True)
            continue

    return candidates


def extract_dates_from_scripts(driver, url):
    candidates = []
    soup = BeautifulSoup(driver.page_source, "html.parser")
    scripts = soup.find_all("script")
    for script in scripts:
        text = script.string if script.string is not None else script.get_text()  # type: ignore
        if not text or text.strip() == "":
            continue

        low = text.lower()
        if (
            "document.cookie" in low
            or "expires=" in low
            or "max-age" in low
            or "setcookie" in low
        ):
            continue

        if script.get("type") == "application/ld+json":  # type: ignore
            try:
                parsed_json = json.loads(text)
            except json.JSONDecodeError:
                try:
                    parsed_json = json.loads("[" + text + "]")
                except json.JSONDecodeError:
                    parsed_json = None
            if parsed_json is not None:
                stack = [parsed_json]
                while stack:
                    node = stack.pop()
                    if isinstance(node, dict):
                        for k, v in node.items():
                            if isinstance(v, (dict, list)):
                                stack.append(v)
                            elif isinstance(v, str) and (
                                k.lower() in (
                                    "datepublished",
                                    "uploaddate",
                                    "datecreated",
                                    "datepublished",
                                ) or ISO_DATETIME_RE.search(v) or ISO_DATE_RE.search(v)
                            ):
                                d = _try_parse_date(v)
                                _add_candidate(candidates, d, "ld+json", v, url)
                    elif isinstance(node, list):
                        for it in node:
                            if isinstance(it, (dict, list)):
                                stack.append(it)
                            elif isinstance(it, str) and (
                                ISO_DATETIME_RE.search(it) or ISO_DATE_RE.search(it)
                            ):
                                d = _try_parse_date(it)
                                _add_candidate(candidates, d, "ld+json", it, url)
            continue

        if "datePublished" in text or "created_at" in text or "dateCreated" in text:
            matches = re.findall(
                r'"(?:datePublished|uploadDate|created_at|dateCreated)"\s*:\s*"([^"]+)"',
                text,
            )
            for m in matches:
                d = _try_parse_date(m)
                _add_candidate(candidates, d, "script-json", m, url)

            iso_matches = ISO_DATETIME_RE.findall(text) + ISO_DATE_RE.findall(text)
            for m in iso_matches:
                d = _try_parse_date(m)
                _add_candidate(candidates, d, "script-regex", m, url)

    return candidates


def extract_from_visible_text(driver, url):
    candidates = []
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    visible_text = soup.get_text(separator=" ")
    for m in ISO_DATETIME_RE.findall(visible_text):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    for m in ISO_DATE_RE.findall(visible_text):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    for m in VERBOSE_DATE_RE.findall(visible_text):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    for m in GENERIC_DATE_RE.findall(visible_text):
        d = _try_parse_date(m)
        _add_candidate(candidates, d, "visible-text", m, url)
    return candidates


def fetch_dynamic_candidates(
    url, headless=True, timeout=20, wait_for=8
) -> list[DateCandidate]:
    options = Options()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("window-size=1920,1080")
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    options.add_argument(f"user-agent={ua}")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(timeout)

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
    except WebDriverException:
        logger.debug("Could not hide webdriver on %s", url, exc_info=True)

    try:
        driver.get(url)
        WebDriverWait(driver, wait_for).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        candidates = []
        candidates += extract_from_dom(driver, url)
        candidates += extract_dates_from_scripts(driver, url)
        candidates += extract_from_visible_text(driver, url)

        return candidates

    except WebDriverException:
        logger.debug("Dynamic scrape failed for %s", url, exc_info=True)
        return []
    finally:
        try:
            driver.quit()
        except WebDriverException:
            logger.debug("Could not close driver for %s", url, exc_info=True)
