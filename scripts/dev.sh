#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT/identificador-api"
WEB_DIR="$ROOT/identificador-web"

API_PID=""
WEB_PID=""

cleanup() {
  trap - SIGINT SIGTERM EXIT
  if [[ -n "$WEB_PID" ]]; then
    kill "$WEB_PID" 2>/dev/null || true
  fi
  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM EXIT

if [[ ! -f "$API_DIR/.env" ]]; then
  echo "warning: $API_DIR/.env not found (copy from .env.example and set SERPAPI_API_KEY)"
fi

if [[ ! -f "$WEB_DIR/.env.local" ]]; then
  echo "warning: $WEB_DIR/.env.local not found (copy from .env.example)"
fi

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "error: run 'npm install' in identificador-web first"
  exit 1
fi

PYTHON="$API_DIR/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

if [[ "${DEV_USE_DATABASE:-}" == "1" ]]; then
  echo "Persistence: Supabase/Postgres (DATABASE_URL from .env)"
else
  export DISABLE_DATABASE=1
  echo "Persistence: in-memory (set DEV_USE_DATABASE=1 to use DATABASE_URL from .env)"
fi

echo "Starting backend on http://localhost:8000"
(
  cd "$API_DIR"
  exec "$PYTHON" main.py
) &
API_PID=$!

echo "Starting frontend on http://localhost:3000"
(
  cd "$WEB_DIR"
  exec npm run dev
) &
WEB_PID=$!

echo "Press Ctrl+C to stop both servers."
wait
