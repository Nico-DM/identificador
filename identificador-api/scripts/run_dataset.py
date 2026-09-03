#!/usr/bin/env python3
"""Ejecuta el dataset de regresión y genera resultados en JSON."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

DATASET_DIR = Path(__file__).resolve().parent.parent / "dataset"
MANIFEST_PATH = DATASET_DIR / "manifest.json"
RESULTS_PATH = DATASET_DIR / "results.json"

STATIC_TERMINAL = {"static_done", "done", "error"}
TERMINAL = {"done", "error"}
POLL_INTERVAL = 2
POLL_MAX_ATTEMPTS = 120
DEFAULT_TOP_N = 10


def load_manifest() -> dict:
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def poll_results(
    base_url: str,
    search_id: str,
    *,
    until_statuses: set[str],
) -> tuple[dict, float]:
    start = time.monotonic()
    for _ in range(POLL_MAX_ATTEMPTS):
        time.sleep(POLL_INTERVAL)
        res = requests.get(f"{base_url}/api/results/{search_id}", timeout=30)
        res.raise_for_status()
        payload = res.json()
        if payload.get("status") in until_statuses:
            return payload, time.monotonic() - start
    raise TimeoutError(f"Timeout esperando resultados para {search_id}")


def url_matches(url: str | None, fragments: list[str]) -> bool:
    if not url:
        return False
    lowered = url.lower()
    return any(fragment.lower() in lowered for fragment in fragments)


def result_snapshot(item: dict | None) -> dict | None:
    if not item:
        return None
    return {
        "url": item.get("url"),
        "date": item.get("date"),
        "platform": item.get("platform"),
        "site_name": item.get("site_name"),
        "score": item.get("score"),
        "confidence": item.get("confidence"),
    }


def find_match_in_top(
    results: list[dict],
    fragments: list[str],
    *,
    limit: int,
) -> tuple[dict | None, int | None]:
    for index, item in enumerate(results[:limit], start=1):
        if url_matches(item.get("url"), fragments):
            return item, index
    return None, None


def evaluate_case(item: dict, payload: dict, results: list[dict], *, top_n: int) -> dict:
    expected = item["expected"]
    status = payload.get("status")
    error = payload.get("error")
    fragments = expected.get("url_contains") or []

    if status == "error" and not results:
        return {
            "correct": False,
            "reason": "error",
            "detail": error,
            "match_rank": None,
            "evaluation_window": top_n,
        }

    if not results:
        return {
            "correct": False,
            "reason": "sin_resultados",
            "detail": "La búsqueda no devolvió candidatos",
            "match_rank": None,
            "evaluation_window": top_n,
        }

    matched, rank = find_match_in_top(results, fragments, limit=top_n)
    if matched:
        matched_date = matched.get("date")
        expected_date = expected.get("date")
        date_ok = True
        if expected_date and matched_date:
            date_ok = expected_date in str(matched_date)
        return {
            "correct": True,
            "reason": "ok",
            "match_rank": rank,
            "evaluation_window": top_n,
            "url_match": True,
            "date_match": date_ok,
        }

    return {
        "correct": False,
        "reason": "fuera_del_top",
        "detail": f"Ninguna fuente esperada en el top {top_n}",
        "match_rank": None,
        "evaluation_window": top_n,
        "url_match": False,
        "date_match": False,
    }


def run_deep_search(base_url: str, search_id: str) -> tuple[dict, float]:
    deep_resp = requests.post(f"{base_url}/api/search/{search_id}/deep", timeout=30)
    deep_resp.raise_for_status()
    return poll_results(base_url, search_id, until_statuses=TERMINAL)


def run_case(base_url: str, item: dict, *, top_n: int) -> dict:
    started = time.monotonic()
    row: dict = {
        "id": item["id"],
        "category": item["category"],
        "title": item["title"],
        "image_url": item["image_url"],
        "expected": item["expected"],
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        resp = requests.post(
            f"{base_url}/api/search",
            json={"image_url": item["image_url"], "safe_search": True},
            timeout=30,
        )
        resp.raise_for_status()
        search_id = resp.json().get("search_id")
        if not search_id:
            raise RuntimeError("Respuesta sin search_id")

        static_payload, static_poll_seconds = poll_results(
            base_url, search_id, until_statuses=STATIC_TERMINAL
        )
        payload = static_payload
        deep_search_used = False
        deep_poll_seconds = 0.0

        deep_info = static_payload.get("deep_search") or {}
        if static_payload.get("status") == "static_done" and deep_info.get("available"):
            payload, deep_poll_seconds = run_deep_search(base_url, search_id)
            deep_search_used = True

        results = payload.get("results") or []
        evaluation = evaluate_case(item, payload, results, top_n=top_n)
        matched, _rank = find_match_in_top(
            results,
            item["expected"].get("url_contains") or [],
            limit=top_n,
        )
        top = results[0] if results else None
        display = matched or top

        row.update(
            {
                "search_id": search_id,
                "status": payload.get("status"),
                "response_time_seconds": round(time.monotonic() - started, 2),
                "static_poll_seconds": round(static_poll_seconds, 2),
                "deep_poll_seconds": round(deep_poll_seconds, 2),
                "deep_search_used": deep_search_used,
                "deep_search_available": bool(deep_info.get("available")),
                "result_count": len(results),
                "top_results": [result_snapshot(item) for item in results[:top_n]],
                "obtained": result_snapshot(display),
                "evaluation": evaluation,
                "error": payload.get("error"),
            }
        )
    except Exception as exc:  # noqa: BLE001 - report all failures in dataset output
        row.update(
            {
                "status": "error",
                "response_time_seconds": round(time.monotonic() - started, 2),
                "deep_search_used": False,
                "obtained": None,
                "evaluation": {
                    "correct": False,
                    "reason": "exception",
                    "detail": str(exc),
                    "match_rank": None,
                    "evaluation_window": top_n,
                },
                "error": str(exc),
            }
        )

    return row


def summarize(rows: list[dict], engine: str, base_url: str, *, top_n: int) -> dict:
    total = len(rows)
    errors = sum(
        1
        for row in rows
        if row["evaluation"]["reason"] in {"exception", "error"}
        or (row.get("status") == "error" and row.get("result_count", 0) == 0)
    )
    correct = sum(1 for row in rows if row["evaluation"].get("correct"))
    times = [row["response_time_seconds"] for row in rows if row.get("response_time_seconds") is not None]
    deep_used = sum(1 for row in rows if row.get("deep_search_used"))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "search_engine": engine,
        "evaluation_window": top_n,
        "deep_search_used_count": deep_used,
        "total_images": total,
        "correct": correct,
        "precision": round(correct / total, 4) if total else 0.0,
        "error_rate": round(errors / total, 4) if total else 0.0,
        "avg_response_time_seconds": round(sum(times) / len(times), 2) if times else 0.0,
        "by_category": {
            category: {
                "total": sum(1 for row in rows if row["category"] == category),
                "correct": sum(
                    1 for row in rows if row["category"] == category and row["evaluation"].get("correct")
                ),
            }
            for category in sorted({row["category"] for row in rows})
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta el dataset de regresión documentado")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--search-engine", default=None, help="Solo informativo en el reporte")
    parser.add_argument("--ids", nargs="*", help="Ejecutar solo estos IDs del manifest")
    parser.add_argument("--output", default=str(RESULTS_PATH))
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Ventana de evaluación (default: 10)")
    args = parser.parse_args()
    top_n = max(1, args.top_n)

    manifest = load_manifest()
    items = manifest["images"]
    if args.ids:
        wanted = set(args.ids)
        items = [item for item in items if item["id"] in wanted]
        if not items:
            print("No se encontraron IDs solicitados", file=sys.stderr)
            return 1

    rows = []
    for index, item in enumerate(items, start=1):
        print(f"[{index}/{len(items)}] {item['id']} — {item['title']}")
        rows.append(run_case(args.base_url, item, top_n=top_n))

    report = summarize(rows, args.search_engine or "unknown", args.base_url, top_n=top_n)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print()
    print(f"Precisión (top {top_n} + deep): {report['precision'] * 100:.1f}% ({report['correct']}/{report['total_images']})")
    print(f"Búsqueda profunda usada: {report['deep_search_used_count']}/{report['total_images']}")
    print(f"Tiempo promedio: {report['avg_response_time_seconds']} s")
    print(f"Tasa de error: {report['error_rate'] * 100:.1f}%")
    print(f"Resultados guardados en {output_path}")

    doc_script = Path(__file__).resolve().parent / "generate_dataset_doc.py"
    if doc_script.exists():
        import subprocess

        subprocess.run([sys.executable, str(doc_script)], check=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
