# Product Decisions (locked from stakeholder)

**Date:** 2026-09-01  
**Status:** Accepted — supersedes “IR-only / single-tenant” framing in earlier discovery notes where they conflict.

---

## Decision 1 — Scope = ALL mobile features

The platform is **not** an Intelligent Reset-only tool.

- Inventory, scenarios, impact selection, and coverage must cover **every mobile feature** (auth, tasks, capture, IR, OOS, planogram, shifts, search, reports, push, deep links, etc.).
- Intelligent Reset may be the **first delivery slice** (because risk is highest and partial tooling exists), but it is **not the ceiling**.
- As mobile ships enhancements, the platform must **discover and update** coverage continuously (git diff → affected features → scenarios), not rely on a frozen IR-only suite.

## Decision 2 — Do NOT reimplement mobile business logic in tests

Tests must verify that **mobile code works as expected**, not that a Python/Java copy of the rules matches a guess.

| Allowed | Not allowed (as the long-term design) |
|---------|----------------------------------------|
| Call real backend | Rewrite action-list / domain rules inside the test framework and treat that as “the app” |
| Run real Android/iOS domain / repository / API layers headlessly | Maintain a second “fake app brain” as source of truth |
| Assert against independent expected **state/contracts** (API schema, DB state, documented business outcomes) | Duplicate calculations so tests pass even if the app is wrong |

**Implication:** The current MBIT Python domain mapper is an **interim bridge only**. The target is **Option B** — headless execution of production mobile modules. Python simulation must shrink over time, not expand to all features.

## Decision 3 — Environment is selectable

Do **not** hard-lock automation to one tenant.

### Resolution rule

```text
--env=<name>  →  https://<name>.rebotics.net
```

Examples: `epsilon`, `delta`, `gamma`, `harr`, or any reachable instance slug.  
Optional `--base-url=` override for exceptions.  
Admin gateways (`r3dev-admin` / `r3us-admin`) stay separate for discovery/builds.  
Credentials from secrets only. Production mutate blocked by default.

## Decision 4 — Headless entry points from git

Extract UI-free domain/API seams from `android-rebotics` and `ios-rebotics` git repos (open PRs there when a façade is needed). Do not block on a named “mobile owner” assignment.

## Decision 5 — GenAI role

**GenAI-first control plane** (agent drives; asserts judge).  
**First surface:** CI PR bot, powered by CLI tool APIs; then CLI agent; Dashboard chat later.  
See `16-genai-and-full-roadmap.md` and `17-genai-first-conversion.md`.

## Decision 6 — Scan images are planogram-aware

Never use one global `bay_1_scan.jpg` for every task.  
Provisioner selects images by **planogram category + bay + stage** (catalog match); fail if no match.  
See `08-release-data-strategy.md`.

---

## Architecture north star (updated)

```text
Choose ENV → https://{env}.rebotics.net
   ↓
Feature inventory (ALL mobile features, kept current from git)
   ↓
Select scenarios (impacted or full)  [GenAI may suggest]
   ↓
Provision data on THAT env
   ↓
REAL backend + REAL mobile domain code from git (headless)
   ↓
Deterministic asserts (PASS/FAIL authority)
   ↓
On FAIL: GenAI explains / classifies (never overrides)
   ↓
Evidence + report
```

## Delivery order (still phased)

1. Inventory all features + `{env}.rebotics.net` resolver  
2. Extract/call real mobile layers from git, feature-by-feature  
3. Retire duplicate test-side business logic as native drivers land  
4. IR first slice → capture → tasks → OOS → …  
5. Wire GenAI **control plane** (CI PR bot first) after judgement tools exist  

IR-first = **schedule**, not **scope limit**.  
GenAI = **control plane** (drives work); asserts = **oracle** (judge results).  
Scan images = **planogram/category matched**, never one global JPG.
