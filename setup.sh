#!/usr/bin/env bash
# Compi: one script to install, build and run.
#   ./setup.sh            install if needed, build, (re)start in the background
#   ./setup.sh install    install backend + frontend dependencies and build the canvas
#   ./setup.sh start      start in the background (http://localhost:8000)
#   ./setup.sh stop       stop the server
#   ./setup.sh restart    rebuild the canvas and restart
#   ./setup.sh logs       follow the server log
#   ./setup.sh dev        run in the foreground (Ctrl+C to stop)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8000}"
LOG="$ROOT/backend/data/server.log"
SERVE=(uv run uvicorn compi.api.app:app --port "$PORT" --env-file ../.env)

use_node() {
  # The system Node is too old; use nvm's Node 22.
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 22 >/dev/null
}

pid() { ss -ltnp 2>/dev/null | grep ":$PORT " | grep -oE 'pid=[0-9]+' | head -1 | cut -d= -f2 || true; }

install() {
  [ -f "$ROOT/.env" ] || { cp "$ROOT/.env.example" "$ROOT/.env"; echo "Created .env: add your API keys to it."; }
  (cd "$ROOT/backend" && uv sync -q)
  use_node
  (cd "$ROOT/frontend" && npm install --silent)
  build
}

build() {
  use_node
  local out
  # Quiet unless it fails (the bundler prints a harmless "use client" warning every time).
  if out="$(cd "$ROOT/frontend" && npm run build 2>&1)"; then echo "Canvas built."
  else echo "$out"; echo "Canvas build failed."; exit 1; fi
}

stop() {
  local p; p="$(pid)"
  if [ -n "$p" ]; then kill "$p" && echo "Stopped (pid $p)."; sleep 1; else echo "Not running."; fi
}

start() {
  [ -n "$(pid)" ] && { echo "Already running on http://localhost:$PORT"; return; }
  mkdir -p "$(dirname "$LOG")"
  (cd "$ROOT/backend" && setsid nohup "${SERVE[@]}" >"$LOG" 2>&1 &)
  for _ in $(seq 20); do [ -n "$(pid)" ] && break; sleep 0.5; done
  if [ -n "$(pid)" ]; then echo "Compi running: http://localhost:$PORT   (log: ./setup.sh logs)"
  else echo "Did not start. Last log lines:"; tail -20 "$LOG"; exit 1; fi
}

case "${1:-}" in
  install) install ;;
  start) start ;;
  stop) stop ;;
  restart) build; stop; start ;;
  logs) tail -f "$LOG" ;;
  dev) stop; cd "$ROOT/backend" && exec "${SERVE[@]}" ;;
  "")
    [ -d "$ROOT/backend/.venv" ] && [ -d "$ROOT/frontend/node_modules" ] || install
    build; stop; start ;;
  *) sed -n '2,10p' "$0"; exit 1 ;;
esac
