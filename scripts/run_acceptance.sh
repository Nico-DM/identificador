#!/usr/bin/env bash
# Pruebas de aceptación RF/RNF → genera docs/aceptacion.md
#
# Requisitos:
#   - SERPAPI_API_KEY real en identificador-api/.env (para RF-001/002/005/007/010 live)
#
# Uso:
#   ./scripts/run_acceptance.sh

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

PYTHON="${API_DIR}/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

echo "==> Acceptance tests (marker: acceptance)"
echo "    Informe: docs/aceptacion.md"
echo ""

set +e
"$PYTHON" -m pytest -m acceptance tests/acceptance -v --tb=short "$@"
status=$?
set -e

if [[ -f "$ROOT/docs/aceptacion.md" ]]; then
  echo ""
  echo "==> Resumen escrito en docs/aceptacion.md"
fi

exit "$status"
