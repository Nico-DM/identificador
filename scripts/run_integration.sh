#!/usr/bin/env bash
# Pruebas de integración: frontend → backend → SerpAPI (API externa).
#
# Requisitos:
#   - SERPAPI_API_KEY válida en identificador-api/.env
#   - Backend en INTEGRATION_API_URL (default http://127.0.0.1:8000)
#   - Frontend en INTEGRATION_WEB_URL (default http://127.0.0.1:3000)
#     para el test de proxy; sin frontend solo corren los tests de backend.
#
# Uso típico:
#   ./scripts/dev.sh          # otra terminal
#   ./scripts/run_integration.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/identificador-api"

cd "$API_DIR"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${SERPAPI_API_KEY:-}" || "$SERPAPI_API_KEY" == "tu_clave_serpapi" ]]; then
  echo "ERROR: configurá SERPAPI_API_KEY real en identificador-api/.env" >&2
  exit 1
fi

PYTHON="${API_DIR}/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

export INTEGRATION_API_URL="${INTEGRATION_API_URL:-http://127.0.0.1:8000}"
export INTEGRATION_WEB_URL="${INTEGRATION_WEB_URL:-http://127.0.0.1:3000}"
export INTEGRATION_TIMEOUT_SECONDS="${INTEGRATION_TIMEOUT_SECONDS:-600}"

echo "==> Integration tests (marker: integration)"
echo "    API: $INTEGRATION_API_URL"
echo "    WEB: $INTEGRATION_WEB_URL"
echo ""

"$PYTHON" -m pytest -m integration tests/integration -v --tb=short "$@"
