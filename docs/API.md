# API Reference

Base URL (cloud): `https://pos.griltek.com/api/v1`
Base URL (edge): `http://{store-server-ip}:8001/api/v1`

## Error format
```json
{"code": "ERROR_CODE", "message": "Human readable", "details": {}}
```

## Authentication
- Cloud: JWT Bearer (access + refresh rotation)
- Edge: JWT Bearer (issued by cloud, validated locally)
- PIN (cashier): short numeric PIN, rate-limited, lockout after N failures

## Endpoints (Step 0 — skeleton)
- `GET /health` — service health check (DB + Redis)

Further endpoints documented per step in implementation.
