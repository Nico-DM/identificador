import argparse
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Smoke test para el API de identificador")
    parser.add_argument("--image-url", required=True, help="URL publica de imagen")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL del backend")
    args = parser.parse_args()

    resp = requests.post(
        f"{args.base_url}/api/search",
        json={"image_url": args.image_url},
        timeout=30,
    )

    logger.info(f"POST /api/search: {resp.status_code} - {resp.text}")
    resp.raise_for_status()
    data = resp.json()
    search_id = data.get("search_id")

    if not search_id:
        raise SystemExit("No se obtuvo search_id")

    for attempt in range(60):
        time.sleep(2)
        res = requests.get(f"{args.base_url}/api/results/{search_id}", timeout=30)
        elapsed = (attempt + 1) * 2
        res.raise_for_status()
        payload = res.json()
        status = payload.get("status")
        result_count = len(payload.get("results") or [])
        logger.info(f"GET /api/results ({elapsed}s): {res.status_code} - status={status}, results={result_count}")
        if status in {"done", "error"}:
            logger.info(f"Procesamiento completado con status: {status}")
            return

    raise SystemExit("Timeout esperando resultados (120s)")


if __name__ == "__main__":
    main()
