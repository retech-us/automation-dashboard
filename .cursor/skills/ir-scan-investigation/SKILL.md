---
name: ir-scan-investigation
description: Investigate a KRCS scan problem. Use when the user gives a reporting scan URL and asks why an action was generated, why an OK product is asked to move, why a set-aside repeats the same slot, or what the root cause is.
---

# IR scan investigation

Use `mobile-backend-integration-tests/core/scan_issue_investigator.py`. Do not re-derive shelf positions from raw planogram facing indexes.

1. Read the scan URL with `parse_scan_url`.
2. Load `GET /api/v4/processing/actions/{scan_id}/` with the saved instance token. Do not print the token or signed URLs.
3. When the URL has store, planogram, and date, load the other sections from that visit, including post-photo scans.
4. Load `GET /api/v1/planograms/{id}/items/` and UPC from `GET /api/v4/products/{product_id}/`. Collapse horizontal facings into one product-order slot.
5. Call `investigate_issue` and answer in this order: what happened, the problem, the root cause, how to solve it.

Lead with the defect the user described. Still report the other two when their counts are non-zero: OK on the wrong slot, a move whose source and destination are the same slot, and a post-photo that repeats that move.
