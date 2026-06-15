# Griltek POS

Multi-tenant, multi-location SaaS POS platform for retail and hospitality.

## What's included

| Component | Description | Port |
|---|---|---|
| **backend** | Cloud API (FastAPI + PostgreSQL) | 8000 |
| **backoffice** | Web dashboard — reports, settings | 5173 |
| **store-server** | Edge server per location (sync + local API) | 8001 |
| **kiosk-selfcheckout** | Self-checkout kiosk (Vue 3) | 5174 |
| **kiosk-pricecheck** | Price-check kiosk (Vue 3) | 5175 |
| **kiosk-order** | Order kiosk / QSR ordering (Vue 3) | 5176 |
| **kds** | Kitchen Display System (Vue 3, WebSocket) | 5177 |
| **cashier** | Cashier desktop app (Python/PyQt6) | — |

---

## Requirements

- **Cloud / edge / kiosks**: [Docker 24+](https://docs.docker.com/get-docker/)
- **Cashier desktop app**: Python 3.12+, pip
- **Development**: Docker + Python 3.12+ + Node 20+

---

## Installation

### 1 — Get the code

```bash
git clone <repo-url> griltek-pos
cd griltek-pos
```

### 2 — Configure environment

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```
SECRET_KEY=<random 32+ char string>
EDGE_SECRET_KEY=<another random 32+ char string>
LOCATION_ID=<UUID of this location — create via API after first cloud start>
CLOUD_API_URL=http://<cloud-server-ip>:8000/api/v1
```

---

## Cloud server (backend + backoffice)

Run on your central server (VPS, on-prem Linux box):

```bash
./install.sh cloud
```

Or manually:

```bash
docker compose -f docker/docker-compose.yml --profile cloud up -d --build
```

| URL | What |
|---|---|
| `http://<host>:8000/docs` | Interactive API docs (Swagger UI) |
| `http://<host>:5173` | **Backoffice** — login here |

**First-time setup via API** (`http://<host>:8000/docs`):

1. `POST /api/v1/tenants` — create your tenant
2. `POST /api/v1/auth/users` — create an admin user
3. `POST /api/v1/locations` — create a location, note the returned `id`
4. Put that `id` into `.env` as `LOCATION_ID=`

---

## Edge server + kiosks (per store)

Run on a mini-PC or NUC at each store location (Ubuntu / Debian recommended):

```bash
./install.sh edge
```

Or manually:

```bash
docker compose -f docker/docker-compose.yml --profile edge up -d --build
```

| URL | Open on |
|---|---|
| `http://localhost:8001/docs` | Store server API |
| `http://localhost:5174` | Self-checkout kiosk screen |
| `http://localhost:5175` | Price-check kiosk screen |
| `http://localhost:5176` | Order kiosk / QSR ordering |
| `http://localhost:5177` | Kitchen Display System (KDS) |

**Kiosk browser setup** (each kiosk is a touchscreen connected to this machine):

- Open the relevant URL in a full-screen Chromium window
- Use `chromium-browser --kiosk --noerrdialogs http://localhost:5174` for true kiosk mode
- Or set Chromium to start full-screen on login via autostart

---

## Cashier desktop app (Windows / Linux / macOS)

The cashier app runs on a standard PC with a receipt printer and optional card terminal.

```bash
./install.sh cashier
```

Then run it:

```bash
cd cashier
.venv/bin/python -m cashier.main      # Linux / macOS
.venv\Scripts\python -m cashier.main  # Windows
```

**Requirements for the cashier machine:**

- Python 3.12+ ([python.org](https://python.org))
- USB receipt printer (ESC/POS compatible)
- The store-server must be reachable at `STORE_SERVER_URL` in `.env`

---

## Accessing the backoffice

The backoffice is a web app — open it in any browser:

- **Local**: `http://localhost:5173`
- **Remote**: `http://<cloud-server-ip>:5173`

It connects to the backend API at port 8000. Features:

- **Dashboard** — today's revenue, transaction count, top products
- **Reports** — sales by product, payment method breakdown, VAT breakdown, stock levels (with CSV download)
- **Sync health** — see how many fiscal records are pending and stock movements unsynced

---

## Development (hot-reload)

Start everything at once with live reloading:

```bash
./install.sh dev
```

---

## Stopping services

```bash
# Cloud
docker compose -f docker/docker-compose.yml --profile cloud down

# Edge
docker compose -f docker/docker-compose.yml --profile edge down

# Both + wipe all data
docker compose -f docker/docker-compose.yml --profile cloud --profile edge down -v
```

---

## Project layout

```
griltek-pos/
├── backend/            Cloud FastAPI backend
├── store-server/       Edge FastAPI server (per-location)
├── cashier/            PyQt6 desktop cashier app
├── kiosk-selfcheckout/ Vue 3 self-checkout kiosk
├── kiosk-pricecheck/   Vue 3 price-check kiosk
├── kiosk-order/        Vue 3 QSR order kiosk
├── kds/                Vue 3 kitchen display
├── backoffice/         Vue 3 backoffice dashboard
├── shared-domain/      Shared Python models
├── docker/             docker-compose.yml
├── .env.example        Environment template
└── install.sh          Install helper script
```
