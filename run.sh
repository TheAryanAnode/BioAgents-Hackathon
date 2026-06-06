#!/usr/bin/env bash
# Start SynthesisOS backend (FastAPI) + frontend (Vite). Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo "Stopping SynthesisOS..."
  if [[ -n "${FRONTEND_PID}" ]] && kill -0 "${FRONTEND_PID}" 2>/dev/null; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo "Servers stopped."
}
trap cleanup EXIT INT TERM

port_in_use() {
  lsof -ti "tcp:$1" >/dev/null 2>&1
}

ensure_backend() {
  if [[ ! -d "$BACKEND/.venv" ]]; then
    echo "→ Creating backend virtualenv..."
    if command -v uv >/dev/null 2>&1; then
      (cd "$BACKEND" && uv venv --python 3.12)
    elif command -v python3.12 >/dev/null 2>&1; then
      python3.12 -m venv "$BACKEND/.venv"
    else
      python3 -m venv "$BACKEND/.venv"
    fi
  fi

  if ! "$BACKEND/.venv/bin/python" -c "import fastapi" 2>/dev/null; then
    echo "→ Installing backend dependencies..."
    if command -v uv >/dev/null 2>&1; then
      (cd "$BACKEND" && uv pip install -r requirements.txt)
    else
      "$BACKEND/.venv/bin/pip" install -r "$BACKEND/requirements.txt"
    fi
  fi

  if [[ ! -f "$BACKEND/.env" ]] && [[ -f "$BACKEND/.env.example" ]]; then
    cp "$BACKEND/.env.example" "$BACKEND/.env"
    echo "→ Created backend/.env from .env.example (add GOOGLE_API_KEY if you have one)"
  fi
}

ensure_frontend() {
  if [[ ! -d "$FRONTEND/node_modules" ]] || [[ ! -f "$FRONTEND/node_modules/vite/package.json" ]]; then
    echo "→ Installing frontend dependencies..."
    (cd "$FRONTEND" && npm install --include=dev)
  fi
}

echo "SynthesisOS — starting servers"
echo "================================"

if port_in_use "$BACKEND_PORT"; then
  echo "Error: port $BACKEND_PORT is already in use (backend)."
  echo "Stop the other process or run: BACKEND_PORT=8001 ./run.sh"
  exit 1
fi
if port_in_use "$FRONTEND_PORT"; then
  echo "Error: port $FRONTEND_PORT is already in use (frontend)."
  echo "Stop the other process or run: FRONTEND_PORT=5174 ./run.sh"
  exit 1
fi

ensure_backend
ensure_frontend

echo "→ Backend  http://localhost:${BACKEND_PORT}  (API docs: /docs)"
echo "→ Frontend http://localhost:${FRONTEND_PORT}"
echo ""
echo "Press Ctrl+C to stop both."
echo ""

(
  cd "$BACKEND"
  exec "$BACKEND/.venv/bin/uvicorn" app.main:app \
    --host 127.0.0.1 \
    --port "$BACKEND_PORT" \
    --reload
) &
BACKEND_PID=$!

(
  cd "$FRONTEND"
  exec npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

wait -n "${BACKEND_PID}" "${FRONTEND_PID}" 2>/dev/null || wait
