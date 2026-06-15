# Deployment guide

## Prerequisites

- A Linux server (Ubuntu 22.04+ / Debian 12 recommended) with Docker 24+ installed
- A DNS name or static IP for the cloud server
- Open ports: `8000` (API), `5173` (backoffice), `8001` (edge, internal only)

---

## 1 — Clone the repo

```bash
git clone https://github.com/GrelecL/griltek-pos.git
cd griltek-pos
```

---

## 2 — Configure environment

```bash
cp .env.example .env
nano .env   # or vim .env
```

Minimum required changes:

```
SECRET_KEY=<generate: python3 -c "import secrets; print(secrets.token_hex(32))">
EDGE_SECRET_KEY=<generate same way>
POSTGRES_PASSWORD=<strong password>
EDGE_POSTGRES_PASSWORD=<strong password>
LOCATION_ID=<fill in after first cloud start — see step 4>
CLOUD_API_URL=http://<your-server-ip-or-domain>:8000/api/v1
```

---

## 3 — Start cloud backend + backoffice

```bash
docker compose -f docker/docker-compose.yml --profile cloud up -d --build
```

Check it's running:
```bash
docker compose -f docker/docker-compose.yml --profile cloud ps
curl http://localhost:8000/api/v1/health
```

Access:
- API docs: `http://<server>:8000/docs`
- Backoffice: `http://<server>:5173`

---

## 4 — First-time data setup

Open `http://<server>:8000/docs` and run in order:

1. **Create tenant**
   ```
   POST /api/v1/tenants
   { "name": "My Business", "slug": "my-business" }
   ```

2. **Create admin user**
   ```
   POST /api/v1/auth/users
   { "tenant_id": "<tenant_id>", "username": "admin", "display_name": "Admin", "pin": "1234" }
   ```

3. **Create location**
   ```
   POST /api/v1/locations
   { "tenant_id": "<tenant_id>", "name": "Main Store", "address": "...", "business_type": "retail", "timezone": "Europe/Ljubljana" }
   ```
   Copy the `id` from the response.

4. **Put the location id into `.env`**
   ```
   LOCATION_ID=<id from step 3>
   ```

---

## 5 — Start edge server + kiosks (at each store location)

On the store PC / NUC (same machine that runs the kiosk screens):

```bash
# Copy .env from cloud server (or create a new one with LOCATION_ID set)
docker compose -f docker/docker-compose.yml --profile edge up -d --build
```

Services started:

| URL | Purpose |
|---|---|
| `http://localhost:8001` | Store server API |
| `http://localhost:5174` | Self-checkout kiosk |
| `http://localhost:5175` | Price-check kiosk |
| `http://localhost:5176` | Order / QSR kiosk |
| `http://localhost:5177` | KDS (kitchen display) |

### Kiosk browser (touchscreen)

Launch Chromium in full-screen kiosk mode:

```bash
chromium-browser --kiosk --noerrdialogs --disable-translate \
  --disable-features=TranslateUI http://localhost:5174
```

To auto-start on boot (systemd example):

```ini
# /etc/systemd/system/kiosk-selfcheckout.service
[Unit]
Description=Self-checkout kiosk
After=docker.service network.target

[Service]
User=kiosk
Environment=DISPLAY=:0
ExecStart=chromium-browser --kiosk --noerrdialogs http://localhost:5174
Restart=always

[Install]
WantedBy=graphical.target
```

---

## 6 — Cashier desktop app

On any Windows / Linux / macOS cashier workstation:

```bash
# Requires Python 3.12+
cd cashier
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m cashier.main
```

Windows shortcut: create `cashier.bat`:
```bat
@echo off
cd /d "%~dp0"
.venv\Scripts\python -m cashier.main
```

---

## 7 — Accessing the backoffice

Open in any browser: `http://<server>:5173`

To expose over HTTPS (recommended for remote access), put nginx in front:

```nginx
server {
    listen 443 ssl;
    server_name pos.yourdomain.com;

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://localhost:5173;
    }
}
```

---

## 8 — Updates

```bash
git pull
docker compose -f docker/docker-compose.yml --profile cloud up -d --build
docker compose -f docker/docker-compose.yml --profile edge up -d --build
```

Migrations run automatically on container start (`alembic upgrade head`).

---

## Stopping / resetting

```bash
# Stop without losing data
docker compose -f docker/docker-compose.yml --profile cloud down
docker compose -f docker/docker-compose.yml --profile edge down

# Full reset (DELETES ALL DATA)
docker compose -f docker/docker-compose.yml --profile cloud --profile edge down -v
```
