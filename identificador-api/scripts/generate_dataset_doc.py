#!/usr/bin/env python3
"""Genera docs/dataset-prueba.md a partir de manifest.json y results.json."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "identificador-api" / "dataset" / "manifest.json"
RESULTS = ROOT / "identificador-api" / "dataset" / "results.json"
OUTPUT = ROOT / "docs" / "dataset-prueba.md"

CATEGORY_LABELS = {
    "fotografia_historica": "Fotografía histórica",
    "arte_tradicional_digitalizado": "Arte tradicional digitalizado",
    "meme": "Meme",
    "stock": "Fotografía de stock",
    "arte_digital": "Arte digital",
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def verdict_label(row: dict) -> str:
    if (row.get("evaluation") or {}).get("correct"):
        return "Correcto"
    return "Incorrecto"


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def format_expected(expected: dict) -> str:
    artist = expected.get("artist") or "—"
    date = expected.get("date") or "—"
    urls = ", ".join(expected.get("url_contains") or [])
    return f"Artista: {artist}; Fecha: {date}; Dominios esperados: {urls}"


def format_source_link(obtained: dict | None) -> str:
    if not obtained:
        return "—"
    url = obtained.get("url")
    if not url:
        return "—"
    label = obtained.get("site_name") or url
    return f"[{escape_cell(label)}]({url})"


def observation_for_row(row: dict) -> str:
    evaluation = row.get("evaluation") or {}
    reason = evaluation.get("reason")

    if reason == "exception":
        return evaluation.get("detail") or row.get("error") or "Error durante la ejecución."
    if reason == "error":
        return evaluation.get("detail") or row.get("error") or "Error de API."
    if reason == "sin_resultados":
        return evaluation.get("detail") or "Sin candidatos."
    if reason == "fuera_del_top":
        window = evaluation.get("evaluation_window", results_window())
        count = row.get("result_count", 0)
        return f"Sin coincidencia en el top {window} ({count} candidatos)."
    if reason == "ok":
        rank = evaluation.get("match_rank")
        deep = "sí" if row.get("deep_search_used") else "no"
        note = f"Coincidencia en posición {rank}; búsqueda profunda: {deep}."
        if row.get("status") == "error":
            note += " La búsqueda terminó con error pero conservó resultados evaluables."
        return note
    return evaluation.get("detail") or "—"


def results_window() -> int:
    return 10


def summarize_rows(rows: list[dict], results: dict) -> dict:
    verdicts = Counter(verdict_label(row) for row in rows)
    evaluation_reasons = Counter(
        (row.get("evaluation") or {}).get("reason", "unknown") for row in rows
    )
    with_results = sum(1 for row in rows if row.get("result_count", 0) > 0)
    deep_used = sum(1 for row in rows if row.get("deep_search_used"))
    ranks = [
        (row.get("evaluation") or {}).get("match_rank")
        for row in rows
        if (row.get("evaluation") or {}).get("correct")
    ]
    response_times = [
        row["response_time_seconds"]
        for row in rows
        if row.get("response_time_seconds") is not None
    ]

    return {
        "verdicts": verdicts,
        "evaluation_reasons": evaluation_reasons,
        "with_results": with_results,
        "without_results": len(rows) - with_results,
        "deep_used": deep_used,
        "evaluation_window": results.get("evaluation_window", results_window()),
        "match_ranks": [rank for rank in ranks if rank is not None],
        "min_response_time": min(response_times) if response_times else None,
        "max_response_time": max(response_times) if response_times else None,
    }


def main() -> None:
    manifest = load_json(MANIFEST)
    results = load_json(RESULTS)
    rows = results["rows"]
    summary = summarize_rows(rows, results)
    window = summary["evaluation_window"]

    lines: list[str] = [
        "# Dataset de prueba — Identificador de Artistas",
        "",
        "## 1. Descripción general",
        "",
        f"Dataset de regresión ejecutado con el motor `{results.get('search_engine', '—')}` sobre URLs públicas definidas en el manifest. Cada caso corre fase estática y, si está disponible, búsqueda profunda.",
        "",
        f"- **Fecha de ejecución:** {results['generated_at']}",
        f"- **Backend evaluado:** `{results['base_url']}`",
        f"- **Total de imágenes:** {results['total_images']}",
        f"- **Ventana de evaluación:** top {window}",
        f"- **Búsqueda profunda ejecutada:** {summary['deep_used']}/{results['total_images']}",
        f"- **Categorías cubiertas:** {', '.join(CATEGORY_LABELS[c] for c in manifest['categories'])}",
        "",
        "Archivos relacionados:",
        "",
        "- `identificador-api/dataset/manifest.json` — definición de casos y expectativas",
        "- `identificador-api/dataset/results.json` — salida cruda de la última corrida",
        "- `identificador-api/scripts/run_dataset.py` — ejecutor de regresión",
        "",
        "## 2. Criterio de evaluación",
        "",
        "| Veredicto | Criterio |",
        "|-----------|----------|",
        f"| **Correcto** | Al menos un resultado del top {window} (tras búsqueda profunda si aplica) coincide con un dominio esperado. |",
        f"| **Incorrecto** | Sin resultados, error de API, o ninguna fuente esperada en el top {window}. |",
        "",
        "**Precisión** = casos Correctos / total.",
        "",
        "## 3. Resultados por imagen",
        "",
        "| ID | Categoría | Imagen | Resultado esperado | Coincidencia | Posición | Fecha detectada | URL fuente | Veredicto | Observaciones |",
        "|----|-----------|--------|--------------------|--------------|----------|-----------------|------------|-----------|---------------|",
    ]

    correct = 0
    for row in rows:
        verdict = verdict_label(row)
        if verdict == "Correcto":
            correct += 1
        obtained = row.get("obtained") or {}
        evaluation = row.get("evaluation") or {}
        match_label = obtained.get("site_name") or "—"
        if not evaluation.get("correct"):
            match_label = "—"
        lines.append(
            "| {id} | {category} | [{title}]({image_url}) | {expected} | {match} | {rank} | {date} | {url} | {verdict} | {notes} |".format(
                id=row["id"],
                category=CATEGORY_LABELS.get(row["category"], row["category"]),
                title=escape_cell(row["title"]),
                image_url=row["image_url"],
                expected=escape_cell(format_expected(row["expected"])),
                match=escape_cell(match_label),
                rank=evaluation.get("match_rank") or "—",
                date=obtained.get("date") or "—",
                url=format_source_link(obtained if evaluation.get("correct") else None),
                verdict=verdict,
                notes=escape_cell(observation_for_row(row)),
            )
        )

    precision = correct / results["total_images"] if results["total_images"] else 0
    incorrect = summary["verdicts"].get("Incorrecto", 0)

    lines.extend(
        [
            "",
            "## 4. Métricas finales",
            "",
            "| Métrica | Valor |",
            "|---------|-------|",
            f"| Precisión (Correcto / total) | **{precision * 100:.1f}%** ({correct}/{results['total_images']}) |",
            f"| Casos correctos | {correct} |",
            f"| Casos incorrectos | {incorrect} |",
            f"| Búsqueda profunda ejecutada | {summary['deep_used']}/{results['total_images']} |",
            f"| Imágenes con candidatos | {summary['with_results']} |",
            f"| Imágenes sin candidatos | {summary['without_results']} |",
            f"| Tiempo promedio de respuesta | {results['avg_response_time_seconds']} s |",
        ]
    )

    if summary["min_response_time"] is not None:
        lines.append(
            f"| Tiempo mínimo / máximo | {summary['min_response_time']} s / {summary['max_response_time']} s |"
        )

    if summary["match_ranks"]:
        ranks = ", ".join(str(rank) for rank in summary["match_ranks"])
        lines.append(f"| Posiciones de acierto | {ranks} |")

    lines.append(
        f"| Tasa de error (fallas de API/excepción) | {results['error_rate'] * 100:.1f}% |"
    )

    lines.extend(
        [
            "",
            "### Desglose por veredicto",
            "",
            "| Veredicto | Cantidad |",
            "|-----------|----------|",
        ]
    )
    for verdict in ("Correcto", "Incorrecto"):
        count = summary["verdicts"].get(verdict, 0)
        if count:
            lines.append(f"| {verdict} | {count} |")

    lines.extend(
        [
            "",
            "### Motivos de evaluación",
            "",
            "| Motivo | Cantidad |",
            "|--------|----------|",
        ]
    )
    reason_labels = {
        "ok": "Coincide en el top N",
        "sin_resultados": "Sin resultados",
        "fuera_del_top": "Fuera del top N",
        "exception": "Excepción",
        "error": "Error de API",
    }
    for reason, count in sorted(summary["evaluation_reasons"].items()):
        label = reason_labels.get(reason, reason)
        lines.append(f"| {label} | {count} |")

    lines.extend(
        [
            "",
            "### Desglose por categoría",
            "",
            "| Categoría | Total | Correctos |",
            "|-----------|-------|-----------|",
        ]
    )

    for category, stats in sorted(results.get("by_category", {}).items()):
        lines.append(
            f"| {CATEGORY_LABELS.get(category, category)} | {stats['total']} | {stats['correct']} |"
        )

    lines.append("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Documento generado en {OUTPUT}")


if __name__ == "__main__":
    main()
