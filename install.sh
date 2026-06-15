#!/usr/bin/env bash
set -e

# Griltek POS — install script
# Usage: ./install.sh [cloud|edge|cashier|dev]

MODE="${1:-help}"
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

check_deps() {
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: $cmd not found. Install it first."; exit 1; }
  done
}

case "$MODE" in

  cloud)
    echo "==> Deploying cloud backend + backoffice"
    check_deps docker
    cd "$REPO_ROOT"
    [ -f .env ] || cp .env.example .env && echo "  Created .env — edit passwords and keys before continuing." && read -p "  Press Enter when ready..."
    docker compose -f docker/docker-compose.yml --profile cloud up -d --build
    echo ""
    echo "  Backend API:  http://localhost:8000/docs"
    echo "  Backoffice:   http://localhost:5173"
    ;;

  edge)
    echo "==> Deploying edge store-server + kiosks + KDS"
    check_deps docker
    cd "$REPO_ROOT"
    [ -f .env ] || cp .env.example .env && echo "  Created .env — set CLOUD_API_URL and LOCATION_ID." && read -p "  Press Enter when ready..."
    docker compose -f docker/docker-compose.yml --profile edge up -d --build
    echo ""
    echo "  Store server:        http://localhost:8001/docs"
    echo "  Self-checkout kiosk: http://localhost:5174  (open in kiosk browser)"
    echo "  Price-check kiosk:   http://localhost:5175  (open in kiosk browser)"
    echo "  Order kiosk:         http://localhost:5176  (open in kiosk browser)"
    echo "  KDS (kitchen):       http://localhost:5177  (open in browser on KDS screen)"
    ;;

  cashier)
    echo "==> Installing cashier desktop app"
    check_deps python3 pip3
    cd "$REPO_ROOT/cashier"
    python3 -m venv .venv
    .venv/bin/pip install --quiet -r requirements.txt
    echo ""
    echo "  Run with:  cd cashier && .venv/bin/python -m cashier.main"
    echo "  Or on Linux/macOS create a launcher pointing to that command."
    ;;

  dev)
    echo "==> Starting all services in dev mode (hot-reload)"
    check_deps docker npm python3
    cd "$REPO_ROOT"
    [ -f .env ] || cp .env.example .env

    echo "  Starting cloud backend..."
    docker compose -f docker/docker-compose.yml --profile cloud up -d db redis
    sleep 3
    (cd backend && DATABASE_URL="postgresql+asyncpg://griltek:changeme@localhost:5432/griltek_pos" \
      REDIS_URL="redis://localhost:6379/0" alembic upgrade head \
      && uvicorn app.main:app --reload --port 8000) &

    echo "  Starting backoffice dev server..."
    (cd backoffice && npm install --silent && npm run dev) &

    echo "  Starting edge store-server..."
    docker compose -f docker/docker-compose.yml --profile edge up -d edge-db edge-redis
    sleep 3
    (cd store-server && EDGE_DATABASE_URL="postgresql+asyncpg://griltek_edge:changeme_edge@localhost:5432/griltek_edge" \
      EDGE_REDIS_URL="redis://localhost:6379/0" alembic upgrade head \
      && uvicorn app.main:app --reload --port 8001) &

    for APP in kiosk-selfcheckout kiosk-pricecheck kiosk-order kds; do
      (cd "$APP" && npm install --silent && npm run dev) &
    done

    echo ""
    echo "  API docs:            http://localhost:8000/docs"
    echo "  Backoffice:          http://localhost:5173"
    echo "  Self-checkout kiosk: http://localhost:5174"
    echo "  Price-check kiosk:   http://localhost:5175"
    echo "  Order kiosk:         http://localhost:5176"
    echo "  KDS:                 http://localhost:5177"
    echo "  Store server docs:   http://localhost:8001/docs"
    echo ""
    echo "  Press Ctrl+C to stop all."
    wait
    ;;

  *)
    echo "Griltek POS installer"
    echo ""
    echo "Usage:  ./install.sh <mode>"
    echo ""
    echo "  cloud    — build and start cloud backend + backoffice (Docker)"
    echo "  edge     — build and start store-server + kiosks + KDS (Docker)"
    echo "  cashier  — install cashier desktop app (Python/PyQt6)"
    echo "  dev      — start everything with hot-reload for development"
    echo ""
    echo "Requirements:"
    echo "  cloud/edge:  Docker 24+"
    echo "  cashier:     Python 3.12+, pip"
    echo "  dev:         Docker, Python 3.12+, Node 20+"
    ;;
esac
