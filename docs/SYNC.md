# Sync Architecture

## Overview
Single sync actor per location: the store server syncs with cloud (not N devices).

## Pull (cloud → edge)
- Delta of master data (catalog, prices, promotions, barcodes) filtered by `location_id`
- Cursor: `sync_cursor_pull` (version number on cloud entities)
- Trigger: periodic poll + on-demand

## Push (edge → cloud)
- `StockMovement` events (append-only, idempotent by UUID)
- `Sale`, `Payment`, `FiscalRecord`, `CashSession`
- Cursor: `sync_cursor_push` (last pushed event timestamp)
- Queue: persisted in edge PostgreSQL; replayed on WAN reconnect

## Stock conflict-free sync
Only movements are synced, never absolute quantities.
`current_qty = sum(movements)` on both sides → no last-write-wins conflict possible.

## Master data conflicts
Cloud wins. Versioned entities: cloud version > edge version → overwrite.

## Resilience levels
See ARCHITECTURE.md.

## Cursors (StoreServer entity)
- `sync_cursor_pull`: last pulled cloud version (int)
- `sync_cursor_push`: timestamp of last successfully pushed event
