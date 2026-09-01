# 17 — Converting to a GenAI-First Testing Framework

**Status:** Architecture option (planning only)  
**Relation:** Builds on `16-genai-and-full-roadmap.md` and `15-product-decisions.md`  
**Important:** GenAI-first ≠ GenAI decides PASS/FAIL.

---

## 1. What “GenAI-first” means here

### GenAI-first (recommended definition)

```text
GenAI is the primary CONTROL PLANE:
  - understands releases / diffs / features
  - proposes and expands scenarios
  - chooses what to run
  - drives triage and reporting narrative
  - suggests new coverage as mobile evolves

Deterministic engines remain the JUDGEMENT PLANE:
  - real env + real APIs + real mobile code
  - contracts + state asserts
  - only source of PASS / FAIL
```

### GenAI-first (dangerous definition — do not use)

```text
GenAI runs the app in its head and says “looks good” → PASS
```

That is not a testing framework; it is a hallucination risk.

---

## 2. Today vs GenAI-first

| Layer | Current plan (assistant) | GenAI-first |
|-------|--------------------------|-------------|
| Who picks scenarios? | Rules + impact map | **GenAI proposes**; rules validate/allowlist |
| Who writes new scenarios? | Humans (+ occasional AI draft) | **GenAI generates continuously**; humans approve high-risk |
| Who explains failures? | Optional GenAI | **Always GenAI** (required path in report) |
| Who decides PASS/FAIL? | Deterministic asserts | **Still deterministic asserts** |
| Entry UX | `./regression run --env=...` | **Chat/agent + CLI**: “Validate epsilon for PR #123” |
| Inventory updates | Manual + scripts | **GenAI drafts from git**; script merges after checks |
| Core identity | Regression platform with AI | **GenAI testing control plane over regression engines** |

---

## 3. Target architecture (GenAI-first)

```text
┌─────────────────────────────────────────────────────────────┐
│                 GenAI CONTROL PLANE                          │
│  Agent / Chat / CI “regression agent”                        │
│  - parse goal (“full”, “impacted”, “feature X”)              │
│  - read git diff + feature inventory                         │
│  - generate/select scenarios                                 │
│  - call tools (never invent HTTP results)                    │
│  - write report narrative + classification suggestions       │
└───────────────┬─────────────────────┬───────────────────────┘
                │ tool calls          │ tool calls
                ▼                     ▼
┌───────────────────────┐   ┌─────────────────────────────────┐
│ Inventory & Impact    │   │ Execution TOOLS (deterministic) │
│ feature YAML          │   │ - env resolve {env}.rebotics.net│
│ api inventory         │   │ - provisioner                   │
│ contract baselines    │   │ - API runner                    │
│ scenario library      │   │ - native mobile headless runner │
└───────────────────────┘   │ - contract diff                 │
                            │ - state assert engine           │
                            └────────────────┬────────────────┘
                                             ▼
                                   PASS / FAIL (tools only)
                                             │
                                             ▼
                            GenAI explains / prioritizes / suggests next tests
```

### Tool-calling rule (non-negotiable)

The agent **must not** fabricate API responses or mobile state.  
It may only:

1. Call tools  
2. Read tool outputs  
3. Reason about those outputs  

---

## 4. How to convert (migration path)

### Step A — Keep the judgement plane (do this first anyway)

Without real env + real mobile execution + asserts, GenAI-first is theater.

Deliver:
- `--env=X` → `https://X.rebotics.net`
- Feature inventory (all features)
- Contract baselines
- Native headless runners from android/ios git
- Evidence packs + exit codes

### Step B — Turn GenAI into the control plane

Add an **Regression Agent** with tools:

| Tool | Purpose |
|------|---------|
| `list_features` | Read inventory |
| `map_diff_to_features` | Git diff → FEATURE-IDs |
| `select_scenarios` | Choose pack |
| `generate_scenarios` | Draft YAML scenarios (saved as proposals) |
| `run_regression` | Execute deterministic suite |
| `get_evidence` | Fetch failure artifacts |
| `classify_failure` | Suggest taxonomy |
| `update_inventory_draft` | Propose inventory edits from repo scan |

### Step C — GenAI-first UX

```text
User/CI:
  “Run impacted regression on epsilon for this PR”
Agent:
  1. map_diff_to_features
  2. select_scenarios / generate_scenarios
  3. run_regression(env=epsilon)
  4. if fail → get_evidence + classify_failure
  5. return narrative + machine JSON + exit code from tools
```

### Step D — Continuous coverage (the GenAI advantage)

On every mobile PR:
1. Agent scans changed files  
2. Drafts missing FEATURE / scenario stubs  
3. Opens proposal PR or queue for approval  
4. After approval, scenarios enter the library  

This is how GenAI-first **keeps up with mobile enhancements** without humans hand-writing everything.

### Step E — Policy gates (so GenAI stays safe)

| Policy | Rule |
|--------|------|
| Verdict | Only tool assert results set PASS/FAIL |
| New scenarios | Auto-add only for low-risk templates; P0 needs human approve |
| Waivers | Human only |
| Production | Mutate blocked |
| Model outage | CLI deterministic path still works |

---

## 5. What GenAI-first covers (extra vs assistant mode)

| Capability | Assistant plan | GenAI-first |
|------------|----------------|-------------|
| Natural-language test requests | No | **Yes** |
| Auto scenario expansion from diffs | Limited | **Core loop** |
| Always-on failure narratives | Optional | **Required** |
| Inventory maintenance assist | Manual-first | **Agent-first drafts** |
| Multi-feature prioritization | Static risk scores | **Agent + scores** |
| Chat in dashboard / IDE | Not primary | **Primary UX** |

Still covers (same as before):
- All mobile features over time  
- Real backend + real mobile code  
- Contracts + state  
- Any `{env}.rebotics.net`  
- CI exit codes  

Still does **not** cover:
- GenAI inventing green results  
- Pixel-perfect UI as main oracle  
- No-assert “AI QA”  
- Production mutate by default  

---

## 6. GenAI-first roadmap (adjusted waves)

| Wave | Deliverable | GenAI role |
|------|-------------|------------|
| G0 | Judgement plane foundations (env, inventory, contracts, native seams) | None required |
| G1 | Tool APIs around runners (stable JSON I/O) | None |
| G2 | Regression Agent MVP (select + run + explain) | **Control plane MVP** |
| G3 | `generate_scenarios` + proposal workflow | Generation |
| G4 | PR bot: impacted run + narrative comment | CI agent |
| G5 | Inventory auto-draft from android/ios git | Continuous update |
| G6 | Dashboard “Ask Regression” chat bound to tools | Product UX |
| G7 | Multi-feature packs at scale; retire Python fake brains | Scale |

**Critical sequencing:** G0–G1 before G2.  
A GenAI agent without real tools becomes a chatbot that guesses.

---

## 7. Example: one release in GenAI-first mode

```text
Developer merges Android action-list mapper change
        ↓
CI starts Regression Agent
        ↓
Agent: map_diff → FEATURE-020, FEATURE-021, FEATURE-024
        ↓
Agent: select/generate scenarios for those features
        ↓
Agent tool: run_regression --env=epsilon --mode=impacted
        ↓
Deterministic engines execute real API + real mobile code
        ↓
FAIL on conservation invariant
        ↓
Agent reads evidence → “MOBILE_BUG likely in mapper merge; confidence 0.81”
        ↓
CI fails (exit code from tools) + PR comment with narrative
        ↓
Agent proposes new edge scenario SC-IR-011 for duplicate UPC refresh
        ↓
Human approves scenario → library grows
```

---

## 8. Cost / risk of going GenAI-first

| Upside | Downside |
|--------|----------|
| Faster coverage growth as mobile changes | Prompt injection / bad tool use if unconstrained |
| Better triage UX | Token cost on every PR |
| NL interface for QA/EM | Needs strong tool sandboxing |
| Feels like a “GenAI framework” product | Easy to accidentally weaken asserts if policies slip |

Mitigations: allowlisted tools, schema-validated tool args, separate `ai_suggestion` vs `assertion_result`, human approval for P0 scenario promotion.

---

## 9. Recommendation (locked default)

**Choose GenAI-first control plane** (agent drives; asserts judge).

**First surface order (best path if unsure):**

| Order | Surface | Why |
|-------|---------|-----|
| 1st | **CI PR bot** | Highest regression value: runs on every PR, no new habit, comments with PASS/FAIL + AI narrative |
| Built-with | **CLI tools** (not chat-first) | Same tools the bot calls; needed for local debug and CI |
| 2nd | **CLI agent** (NL on top of CLI tools) | Power users / local “run impacted on epsilon” |
| 3rd | **Dashboard chat** | Nicest UX, but weakest until tools + CI prove value |

So: **not** “pick only one forever” — sequence is **CI PR bot first (product)**, powered by **CLI tool APIs**, then optional chat UIs.

Do **not** start with Dashboard chat alone (pretty but empty without judgement tools).

---

## 10. Proceed defaults

Unless overridden:

1. **GenAI-first control plane** — yes  
2. **First surface** — CI PR bot (+ CLI tool spine)  
3. **Env** — `--env=X` → `https://X.rebotics.net`  
4. **Images** — planogram/category/bay/stage catalog match; never one global scan JPG for all tasks  

