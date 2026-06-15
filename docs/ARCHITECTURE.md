# Architecture

Griltek POS is a multi-tenant, multi-location SaaS POS platform covering both retail and hospitality in a single codebase. Business behaviour is controlled by `Location.business_type` (retail | hospitality | mixed) and `LocationConfig` (feature matrix), not by forking code.

## Components

| Component | Tech | Role |
|---|---|---|
| `backend/` | FastAPI + PostgreSQL (cloud) | Master data, billing, reporting authority |
| `store-server/` | FastAPI + PostgreSQL + Redis (edge) | Live store state authority (inventory, orders, KDS, CashSession) |
| `cashier/` | PyQt6 | Staff POS terminal, offline-resilient |
| `backoffice/` | Vue 3 | Admin UI |
| `kiosk-selfcheckout/` | Vue 3 | Self-checkout |
| `kiosk-pricecheck/` | Vue 3 | Price-check |
| `kiosk-order/` | Vue 3 | Order kiosk (hospitality) |
| `kds/` | Vue 3 | Kitchen Display System (hosted on edge) |
| `shared-domain/` | Python package | Shared Pydantic schemas + sync types |

## Resilience levels

1. Normal: device → store-server (LAN) → cloud (WAN)
2. WAN down: store-server operates standalone; sync queued
3. Store-server down: device falls back to local SQLite cache + queue (degraded, no inter-device coherence)

## Hardware provisioning

See `docker/docker-compose.yml` for development profiles. Production edge runs docker-compose on a fanless mini PC/NUC with UPS.
