# Full Roadmap — What This Is (and Is Not), Including GenAI

**Audience:** stakeholders who need a clear picture before implementation  
**Status:** Planning only — no platform build started from this doc  
**Related:** `15-product-decisions.md`, `00-executive-summary.md`, `tasks/plan.md`

---

## 1. Straight answer: Is this a “true integrated GenAI framework”?

**No — not as the primary product.**

| Question | Answer |
|----------|--------|
| Is the core a GenAI chatbot / agent that “does testing”? | **No** |
| Is GenAI the thing that decides PASS/FAIL? | **No** (forbidden) |
| Is GenAI integrated into the regression platform? | **Yes — as an assistant layer** |
| Can the platform run if GenAI is down? | **Yes — fully** |
| What is the primary product? | **Autonomous Mobile + Backend Regression & Release Validation** |

Think of it as:

```text
┌─────────────────────────────────────────────────────────────┐
│  REGRESSION ENGINE (authoritative)                          │
│  real env · real APIs · real mobile code · deterministic    │
│  asserts · evidence · CI exit codes                         │
└───────────────────────────┬─────────────────────────────────┘
                            │ on failures / on demand
┌───────────────────────────▼─────────────────────────────────┐
│  GenAI ASSISTANT LAYER (integrated, non-authoritative)      │
│  explain · classify · suggest scenarios · map git→features  │
│  never flips FAIL → PASS                                    │
└─────────────────────────────────────────────────────────────┘
```

If someone sells this as “a GenAI testing framework,” that is **misleading**.  
If someone describes it as “a regression platform **with integrated GenAI analysis and assistance**,” that is **accurate**.

---

## 2. What problem it solves

Today:
- Appium taps are slow/expensive and don’t prove domain math well  
- API tests miss mobile processing bugs  
- IR lab helps but is local, IR-heavy, and partly simulates app logic  
- Mobile keeps changing; suites don’t auto-retarget  

Target:
- Pick **any** env → `https://{env}.rebotics.net`  
- Cover **all** mobile features over time  
- Run **real** backend + **real** mobile domain code (from git), mostly without UI  
- Keep coverage current as mobile PRs land  
- Use GenAI to **speed diagnosis and discovery**, not to invent green builds  

---

## 3. Environment model (locked)

```text
--env=<name>  →  https://<name>.rebotics.net
```

Examples: `epsilon`, `delta`, `gamma`, `harr`, or any other instance slug that exists.  
Credentials = secrets only.  
Production mutate = blocked by default.

---

## 4. How GenAI helps regression (what it WILL do)

| GenAI capability | How it helps |
|------------------|--------------|
| **Failure explanation** | Turns request/response/state/diff into a readable root-cause hypothesis |
| **Failure classification assist** | Suggests BACKEND vs MOBILE vs ENV vs CONTRACT (human/engine still own the label) |
| **Impact assist** | From git diff text, suggests which FEATURE-IDs / scenarios to run |
| **Scenario suggestions** | Proposes new negative/edge cases when inventory or contracts change |
| **Report narratives** | Release summary in plain language for QA/EM |
| **Inventory drafting assist** | Helps draft feature/API inventory entries from repo structure (human reviews) |

### How GenAI does NOT help (hard rules)

| Forbidden | Why |
|-----------|-----|
| Mark FAIL as PASS because “looks fine” | Unsafe; hides regressions |
| Skip scenarios on vibes | Coverage lies |
| Reimplement business rules as “AI expected result” | Same problem as fake Python brain |
| Replace deterministic contract/state asserts | Non-repeatable CI |
| Auto-merge / auto-waive without human | Process risk |

**Deterministic assertion engine remains the only authority for PASS/FAIL.**

---

## 5. What the platform WILL cover

### 5.1 Product scope
- **All mobile features** (Android + iOS), inventory kept current from git  
- Auth, tasks, capture/upload, Intelligent Reset, OOS, planogram, shifts, search, reports, settings, deep links, etc. (phased)  
- Backend APIs those features use (`/api/v1` + `/api/v4` as needed)  
- API **contracts** (schema/type/enum/status drift)  
- **State** before/after (API + where available DB/mobile domain state)  
- Multi-env runs via `{env}.rebotics.net`  
- Headless path as primary; thin UI (Appium) only where UI is the feature  

### 5.2 Engineering outcomes
- Impacted regression (changed files → features → scenarios)  
- Full regression mode  
- Evidence packs (request, response, state, logs)  
- Failure taxonomy  
- CI-compatible exit codes  
- GenAI annotations on failures + optional discovery assist  

### 5.3 Delivery order (schedule, not scope limit)

| Wave | Focus |
|------|--------|
| Wave 0 | Docs / inventory / multi-env / honesty (no fake “GenAI does testing”) |
| Wave 1 | Foundations: inventory all features, env resolver, impact map, contract baselines |
| Wave 2 | Native headless seams from **android-rebotics / ios-rebotics git** (start with easiest UI-free APIs/repos) |
| Wave 3 | First vertical: Intelligent Reset on real mobile layers + real backend |
| Wave 4 | Capture, tasks, auth pack on same pattern |
| Wave 5 | OOS, planogram, shifts, search, reports, … until inventory covered |
| Wave 6 | Orchestrator CLI + evidence + classification |
| Wave 7 | GenAI assistant layer wired (analyze/suggest only) |
| Wave 8 | CI gates (PR fast / nightly live / release full) |
| Wave 9 | Autonomy: impacted selection + release PASS/FAIL report |
| Wave 10 | Retire interim Python business-logic clones feature-by-feature |

---

## 6. What it will NOT cover

| Out of scope / not promised | Notes |
|-----------------------------|-------|
| GenAI as the test oracle | Never |
| Fully autonomous “AI writes and greenlights releases” with no asserts | Never |
| Replacing all Appium/UI forever on day one | Thin UI ring remains for camera/visual widgets |
| Running production mutate by default | Blocked |
| Guaranteeing 100% of UI pixels / animations | Not the goal |
| Duplicating the entire app in Python/Java for “all features” | Explicitly rejected |
| Instant Option C (full app process headless) | Not near-term |
| Trading repos (intellitrade, etc.) | Unrelated |
| Fixing product bugs automatically | Reports + classification only |
| Offline magic without a reachable `{env}.rebotics.net` for real mode | Need network + credentials |
| Perfect iOS/Android parity on day one | Extracted feature-by-feature from git |

---

## 7. Full roadmap (phases)

### Phase 0 — Align (done / in progress)
- Discovery docs, product decisions  
- Clarify: regression platform + GenAI assistant (not GenAI-first)  

### Phase 1 — Inventory & multi-env
- Full feature inventory (all modules)  
- `--env` → `https://{env}.rebotics.net`  
- Impact map (git paths → features)  
- Honest docs (no overclaim)  

**Helps regression:** know *what* exists and *where* to run.

### Phase 2 — Contract & evidence spine
- OpenAPI baselines + drift gate  
- Evidence pack format  
- Failure taxonomy  

**Helps regression:** catch backend/mobile contract breaks early; diagnosable fails.

### Phase 3 — Native headless extraction (from git)
- From `android-rebotics` / `ios-rebotics`: identify UI-free API/repo/mapper entry points  
- Add thin façades via PRs in those repos when needed  
- Wire runners to call **real** mobile code  

**Helps regression:** tests prove the app, not a copy of the app.

### Phase 4 — Vertical slices (feature packs)
- IR pack → Capture → Tasks/Auth → OOS → …  
- Each pack: provision on chosen env, execute, assert state, evidence  

**Helps regression:** real release confidence feature-by-feature.

### Phase 5 — Orchestrator
- `./regression run --env=... --mode=impacted|full`  
- Scenario selection, cleanup, JUnit/JSON/HTML  

**Helps regression:** one command, CI-ready.

### Phase 6 — GenAI integration (assistant)
- Failure analysis annotations  
- Diff → feature suggestions  
- Scenario draft suggestions  
- Release narrative  

**Helps regression:** faster triage and upkeep — **not** greener builds.

### Phase 7 — CI / release autonomy
- PR gate (fast), nightly live, release full  
- Dashboard consumption of results  

**Helps regression:** every merge/release gets a machine verdict + human-readable AI notes.

---

## 8. One-page “GenAI vs Regression Engine”

```text
                    ┌──────────────────┐
   Mobile git ─────►│ Feature inventory│◄──── GenAI may draft
   Backend git ────►│ Impact map       │◄──── GenAI may suggest
                    └────────┬─────────┘
                             ▼
   --env=name ─────► https://name.rebotics.net
                             ▼
                    ┌──────────────────┐
                    │ Provision data   │
                    │ Run real APIs    │
                    │ Run real mobile  │────── GenAI does NOT execute asserts
                    │ Domain headless  │
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ Deterministic    │────── ONLY source of PASS/FAIL
                    │ asserts + state  │
                    └────────┬─────────┘
                             ▼
                      FAIL? ──yes──► GenAI explains / classifies / suggests
                        │
                       no
                        ▼
                      PASS + report
```

---

## 9. Success metrics (how we’ll know it helped)

| Metric | Meaning |
|--------|---------|
| Critical features with ≥1 headless real-mobile scenario | Coverage depth |
| Contract drift catches before app release | Early break detection |
| Time to triage a failure (with vs without GenAI notes) | GenAI value |
| % IR/release signoff without full Appium run | Manual effort down |
| Zero incidents of AI overriding FAIL→PASS | Safety |
| Inventory updated within 1 sprint of major mobile feature | Keeps current |

---

## 10. Decision required before coding

Please confirm explicitly:

1. **Accept this framing:** primary product = regression platform; GenAI = integrated assistant only?  
2. **Env rule OK:** `--env=X` → `https://X.rebotics.net`?  
3. **Extraction OK:** headless seams taken from android/ios git (PRs there as needed)?  

Until (1)–(3) are confirmed, implementation of the roadmap should not start.
