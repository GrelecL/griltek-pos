# FURS Fiscal Integration

⚠️ **WARNING**: This module requires a real FURS certificate and legal review before production use.

## Overview
Slovenian fiscal requirement per ZDavPR (Zakon o davčnem potrjevanju računov).

## Components (Step 5)
- ZOI calculation: RSA signature + MD5 of invoice fields
- EOR retrieval: SOAP/REST call to FURS endpoint
- Business premise registration
- Device registration
- Offline scenario: issue receipt with ZOI, defer EOR confirmation

## Endpoints
- Test: https://blagajna-test.fu.gov.si/
- Production: https://blagajna.fu.gov.si/

## Per-device fiscal counters
Counters live on the store server (durable PostgreSQL), not on individual devices.
Format: `{PoslovniProstor}-{Naprava}-{ZaporednaŠt}` (gapless sequence).

## Enabling/Disabling FURS

FURS fiscalization is **optional per location**, controlled by `LocationConfig.furs_enabled` (default `True`).

### Disabling fiscalization

Set `furs_enabled = false` on a `LocationConfig` to skip fiscalization entirely for that location.
When disabled, `FiscalRecord.status` is set to `"skipped"` and no ZOI or EOR is generated.
The receipt shows neither ZOI nor EOR.

**Use cases for disabling:**
- Locations outside Slovenia (not subject to ZDavPR)
- Test/staging environments where you want sales to work without FURS setup
- Merchants not yet registered with FURS

### Required fields when furs_enabled = true

- `Location.furs_tax_number` — merchant's davčna številka (e.g. `"12345678"`). Used in ZOI computation.
- `Location.furs_business_premise_id` — FURS-registered premise code (poslovni prostor), e.g. `"PP001"`.

Both fields must be set before fiscalizing sales at the location. If missing, defaults (`"00000000"` and `"PP001"`) are used.

### FURS_ENV setting

Set the `FURS_ENV` environment variable to control which adapter is used:

| Value        | Adapter           | Notes                                        |
|--------------|-------------------|----------------------------------------------|
| `mock`       | MockFursAdapter   | Default. No network calls. Fake EOR.         |
| `test`       | MockFursAdapter   | Points at FURS beta in concept; still mocked.|
| `production` | RealFursAdapter   | Requires `FURS_CERT_PATH` + real certificate.|

`FURS_ENV=mock` is the default so all tests and dev environments work without any FURS setup.

## TODO (Step 5)
- [ ] Obtain FURS test certificate
- [ ] Implement ZOI (RSA-SHA256 → MD5)
- [ ] Implement SOAP client for EOR
- [ ] Implement offline queue + deferred confirmation
- [ ] Print ZOI + EOR + QR on receipt
- [ ] Legal review of offline window duration
