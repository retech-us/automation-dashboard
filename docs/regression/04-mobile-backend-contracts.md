# 04 — Mobile ↔ Backend Contracts

## Purpose

Define how we detect **contract breaks** between Management APIs and mobile consumers without launching UI.

## Sources of Truth

| Layer | Source | Authority |
|-------|--------|-----------|
| Backend producer | DRF serializers + `docs/swagger/main.yaml` + `/api/auto-docs/` | Primary for response shape |
| Android consumer | `PogResetApi`, Retrofit models, action-list mappers | Primary for Android expectations |
| iOS consumer | `rebotics_api` Targets/DTOs | Primary for iOS expectations |
| Lab consumer | MBIT Python adapters/mappers | Interim; must stay parity-locked |

## Critical Contracts (IR release)

### C1 — Action List Retailer

```text
GET /api/v1/tasks/{id}/action-list/retailer/

Mobile expects (conceptual):
  - list/paginated results
  - stable action type enums
  - position fields numeric or consistently typed
  - UPC string preserving leading zeros
  - optional image URL nullable
  - bay/shelf identifiers present for shelf actions

Break examples:
  amount: double → string          ❌ type
  action_type enum value removed   ❌ enum
  results → data rename            ❌ field
  required image becomes null-only without mobile null-safe ❌ nullability
```

### C2 — Scan Report Actions PATCH

Mobile expects idempotent progress updates and clear error schema on conflict.

### C3 — Processing Upload Spine (v4)

Mobile expects upload request → finish → poll status machine. Changing status enum strings breaks pollers.

### C4 — Auth Token Shapes

```text
Token <key>     # DRF legacy
Bearer <jwt>    # JWT
Bearer <idp> <token>  # SSO
```

Header format mismatches are auth contract breaks.

### C5 — Settings Graph

Additive keys usually OK; removing/renaming keys consumed by remote config is a break.

## Validation Strategy

```text
1. Download OpenAPI (auto-docs or swagger main.yaml)
2. Diff against versioned baseline in docs/regression/baselines/
3. Run consumer fixtures (Android mapper tests + MBIT golden payloads)
4. Optional live probe against non-prod tenant
5. Emit machine-readable contract report
```

Reuse/enhance `retech-api-automation` SchemaDownloader/SchemaValidator; **persist baselines** (currently cleared each run — known gap).

## Report Format

```text
BACKEND
API changed:
GET /api/v1/tasks/{id}/action-list/retailer/

Mobile expects:
field = position
type = number

Backend release:
field = position
type = string

RESULT:
❌ MOBILE/BACKEND CONTRACT BREAK
Features: FEATURE-020, FEATURE-021
Suggested owner: backend-tasks + mobile-pog-reset
```

## Ownership

| Contract area | Backend owner hint | Mobile owner hint |
|---------------|--------------------|-------------------|
| Action list | apps/tasks | pog_reset / TaskActionList |
| Processing upload | deprecated_api / realograms | capture/upload |
| Auth | master_data | auth modules |
| Settings | rebotics/constance | remote_config / SettingsManager |
