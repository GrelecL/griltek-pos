# Assumptions & Open Questions

## Confirmed
- Single codebase for retail + hospitality; behaviour controlled by `Location.business_type` + `LocationConfig`.
- Currency: EUR. Retail prices include VAT.
- Stock sync: only `StockMovement` events synced (append-only); absolute quantities never synced.
- One store server per location (HA/redundancy is a future phase).
- Fiscal counters are durable on the store server (gapless per business premise + device).

## Requires legal/business confirmation
- **Rounding**: amounts to 2 decimal places (cent). Cash rounding configurable per-tenant (default off). ⚠️ Verify with accountant.
- **FURS offline window**: assumed 2 business days for deferred EOR confirmation. ⚠️ Verify current ZDavPR regulation.
- **FURS test environment**: development uses FURS beta/test endpoint. Real cert required for production. ⚠️ Obtain from FURS.
- **VAT rates**: 22% (standard), 9.5% (reduced), 5% (special, e.g. books). ⚠️ Verify current SI rates.
- **GDPR**: Customer/loyalty data minimisation required; right to erasure to be implemented. ⚠️ Legal review needed.

## Technical decisions
- Alembic migrations are separate for cloud (`backend/alembic/`) and edge (`store-server/alembic/`).
- `shared-domain/` is a pip-installable package imported by both Python services.
- All hardware integrations have mock implementations; real implementations marked `# TODO: real impl`.
