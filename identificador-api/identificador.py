from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from typing import Dict, List

from scraper_estatico import obtener_candidatas_estaticas
from scraper_dinamico import obtener_candidatas_dinamicas
from modelos import DateCandidate

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "igshid",
    "ref",
    "src",
    "spm",
    "mkt_tok",
    "mc_cid",
    "mc_eid",
}

SOURCE_SCORE = {
    "ld+json": 0.5,
    "meta": 0.4,
    "time": 0.3,
    "script-json": 0.25,
    "script-regex": 0.15,
    "visible-text": 0.1,
    "time-datetime": 0.3,
    "time-text": 0.2,
    "texto": 0.1,
}

EXTRACTOR_SCORE = {
    "static": 0.1,
    "dynamic": 0.2,
}

def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in TRACKING_PARAMS]
    clean = parsed._replace(query=urlencode(query), fragment="")
    return urlunparse(clean)


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if "instagram.com" in host:
        return "instagram"
    if "reddit.com" in host:
        return "reddit"
    if "deviantart.com" in host:
        return "deviantart"
    if "x.com" in host or "twitter.com" in host:
        return "x"
    if "tiktok.com" in host:
        return "tiktok"
    if "facebook.com" in host:
        return "facebook"
    return "unknown"


def classify_context(url: str, platform: str) -> Dict[str, bool]:
    path = urlparse(url).path.lower()
    flags = {
        "is_comment": False,
        "is_reply": False,
        "is_embed": False,
        "is_share": False,
        "is_profile": False,
    }

    if "embed" in path:
        flags["is_embed"] = True
    if any(token in path for token in ("/replies", "/reply")):
        flags["is_reply"] = True
    if "comment" in path and platform != "reddit":
        flags["is_comment"] = True
    if any(token in path for token in ("/share", "/repost", "/retweet", "/shares")):
        flags["is_share"] = True

    # heuristica simple de perfil: path corto sin segmentos conocidos
    segments = [s for s in path.split("/") if s]
    if len(segments) == 1 and platform in {"instagram", "x", "tiktok"}:
        flags["is_profile"] = True

    return flags


def score_candidate(candidate: DateCandidate, platform: str, flags: Dict[str, bool]) -> float:
    score = 0.0
    score += SOURCE_SCORE.get(candidate.source, 0.05)
    score += EXTRACTOR_SCORE.get(candidate.extractor, 0.0)

    if platform in {"youtube", "reddit", "deviantart"} and candidate.source in {"ld+json", "meta"}:
        score += 0.2

    if flags.get("is_comment"):
        score -= 0.5
    if flags.get("is_reply"):
        score -= 0.4
    if flags.get("is_share"):
        score -= 0.3
    if flags.get("is_embed"):
        score -= 0.2
    if flags.get("is_profile"):
        score -= 0.2

    return max(score, 0.0)


def select_best_candidate(candidates: List[DateCandidate], threshold: float = 0.45):
    if not candidates:
        return None

    filtered = [c for c in candidates if c.score >= threshold]
    if not filtered:
        filtered = candidates

    filtered.sort(key=lambda c: (c.date, -c.score))
    return filtered[0]


def get_sorted_dates(results):
    publicaciones = []
    seen_urls = set()
    i = 0
    for result in results:
        i += 1
        print(f"----- {i}/{len(results)} -----")
        url = normalize_url(result["link"])
        if url in seen_urls:
            print("URL duplicada; ignorando")
            continue
        seen_urls.add(url)

        platform = detect_platform(url)
        print(f"Source: {result['source']}")
        print(f"Link: {url}")

        candidates = obtener_candidatas_estaticas(url)
        flags = classify_context(url, platform)
        for c in candidates:
            c.flags.update(flags)
            c.score = score_candidate(c, platform, flags)

        best_static = select_best_candidate(candidates)
        if not best_static or best_static.score < 0.55:
            print("Fecha estatica poco confiable; buscando dinamica...")
            dynamic = obtener_candidatas_dinamicas(url)
            for c in dynamic:
                c.flags.update(flags)
                c.score = score_candidate(c, platform, flags)
            candidates += dynamic

        best = select_best_candidate(candidates)
        if best:
            result["created_utc"] = best.date
            result["score"] = best.score
            result["link"] = url
            result["platform"] = platform
            publicaciones.append(result)
            print(f"Fecha y hora: {best.date} (score={best.score:.2f})")
        else:
            print("No se encontro fecha; ignorando resultado")

    publicaciones.sort(key=lambda x: x["created_utc"])

    return publicaciones