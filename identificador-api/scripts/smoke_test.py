import argparse
import logging
import time

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"done", "error"}
STATIC_TERMINAL_STATUSES = {"static_done", "done", "error"}


def poll_results(
    base_url: str, search_id: str, *, until_statuses: set[str], label: str
) -> dict:
    for attempt in range(60):
        time.sleep(2)
        res = requests.get(f"{base_url}/api/results/{search_id}", timeout=30)
        elapsed = (attempt + 1) * 2
        res.raise_for_status()
        payload = res.json()
        status = payload.get("status")
        result_count = len(payload.get("results") or [])
        deep = payload.get("deep_search") or {}
        logger.info(
            f"GET /api/results ({label}, {elapsed}s): status={status}, "
            f"results={result_count}, deep_available={deep.get('available')}"
        )
        if status in until_statuses:
            logger.info("%s completed with status: %s", label, status)
            return payload

    raise SystemExit(f"Timeout waiting for results ({label}, 120s)")


def main():
    parser = argparse.ArgumentParser(
        description="Smoke test for the identificador API",
    )
    parser.add_argument("--image-url", required=True, help="URL publica de imagen")
    parser.add_argument(
        "--base-url", default="http://localhost:8000", help="Base URL del backend"
    )
    parser.add_argument(
        "--expect-status",
        type=int,
        default=None,
        help="Si se indica (p. ej. 400), solo se comprueba el codigo HTTP y no se hace polling",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Tras la fase estatica, lanzar busqueda profunda si esta disponible",
    )
    args = parser.parse_args()

    resp = requests.post(
        f"{args.base_url}/api/search",
        json={"image_url": args.image_url},
        timeout=30,
    )

    logger.info(f"POST /api/search: {resp.status_code} - {resp.text}")

    if args.expect_status is not None:
        if resp.status_code != args.expect_status:
            raise SystemExit(
                f"Se esperaba HTTP {args.expect_status}, se obtuvo {resp.status_code}"
            )
        if resp.status_code >= 400:
            data = resp.json() if resp.text else {}
            detail = data.get("detail")
            if not detail:
                raise SystemExit("Respuesta de error sin campo detail")
            logger.info("Rechazo esperado confirmado: %s", detail)
        return

    resp.raise_for_status()
    data = resp.json()
    search_id = data.get("search_id")

    if not search_id:
        raise SystemExit("No se obtuvo search_id")

    static_payload = poll_results(
        args.base_url,
        search_id,
        until_statuses=STATIC_TERMINAL_STATUSES,
        label="fase estatica",
    )

    if args.deep and static_payload.get("status") == "static_done":
        deep_info = static_payload.get("deep_search") or {}
        if not deep_info.get("available"):
            logger.info("Deep search not available; skipping --deep")
            return

        deep_resp = requests.post(
            f"{args.base_url}/api/search/{search_id}/deep",
            timeout=30,
        )
        logger.info(f"POST /api/search/{search_id}/deep: {deep_resp.status_code}")
        deep_resp.raise_for_status()

        poll_results(
            args.base_url,
            search_id,
            until_statuses=TERMINAL_STATUSES,
            label="busqueda profunda",
        )


if __name__ == "__main__":
    main()
