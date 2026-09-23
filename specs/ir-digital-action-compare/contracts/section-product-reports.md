# Contract: R07 section-product-reports

## Endpoint

```
GET {base_url}/api/v1/reporting/R07/section-product-reports/?scan_id={scan_id}
Authorization: Token {same token as GET /api/v4/tasks/{task_id}/}
Accept: application/json
```

`base_url` = `https://{env}.rebotics.net` (example env `harr`).

Dashboard SPA (not scraped):  
`https://{env}.rebotics.net/reporting/dashboard?store={store}&category={category}&planogram={pog}&date={YYYY-MM-DD}`

## Normalized item (Item list)

| UI column | JSON field (preferred) | Example |
|-----------|------------------------|---------|
| Product name | `product_name` | `NATURES TRUTH ESS OIL DIFFUSER 1 CT` |
| Section | `section` | `1` |
| POG Position | `pog_position` | `7:1` |
| ROG Position | `rog_position` | `7:1` |
| UPC | `upc` | `840093104403` |
| Action type | `action_type` | `ok` |
| Action taken | `action_taken` | `-` |
| (query) | `scan_id` | from query and/or row |

Client must also accept camelCase aliases if present (`actionType`, `actionTaken`, `productName`, `pogPosition`, `rogPosition`, `scanId`).

Envelope: either a JSON array of items or `{ "results": [ ... ] }` / `{ "items": [ ... ] }`.

Empty `action_taken`: `"-"`, `""`, or `null` → store as `"-"`.
