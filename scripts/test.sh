#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> API tests (pytest)"
cd "$ROOT/identificador-api"
./venv/bin/python3.11 -m pytest -q

echo ""
echo "==> Web tests (vitest)"
cd "$ROOT/identificador-web"
npm test

echo ""
echo "All tests passed."
