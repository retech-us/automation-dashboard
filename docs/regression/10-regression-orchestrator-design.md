# 10 — Regression Orchestrator Design

## Command UX

```bash
./regression run --release=2.16.1
./regression run --mode=impacted --base=origin/master
./regression run --mode=full --suite=ir
./regression run --scenario=SC-IR-001 --env=epsilon
```

Exit codes: `0` pass, `1` product/contract fail, `2` env/infra fail, `3` framework fail.

## Pipeline

```text
Regression Orchestrator
  → Feature Discovery (inventory + git diff map)
  → Scenario Selection (impacted | full | suite)
  → Environment Validation (health, auth, DB/API reachability)
  → Data Provisioning
  → Backend Validation (API assertions)
  → Mobile Headless Validation (MBIT / native unit)
  → Contract Validation (baseline diff)
  → Cross-layer State Validation
  → Cleanup
  → Evidence Collection
  → AI Analysis (optional, non-authoritative)
  → Regression Report (HTML + JSON + JUnit)
```

## Components (proposed modules under automation-dashboard)

| Component | Responsibility |
|-----------|----------------|
| `regression/cli.py` | Entry |
| `regression/env_check.py` | Health |
| `regression/impact.py` | Diff → features |
| `regression/provisioner.py` | Data setup |
| `regression/runners/api.py` | Invoke API suite subset |
| `regression/runners/mbit.py` | Domain/IR |
| `regression/runners/native.py` | Gradle/xcode unit |
| `regression/contract.py` | OpenAPI baseline |
| `regression/evidence.py` | Pack artifacts |
| `regression/classify.py` | Failure taxonomy |
| `regression/report.py` | Unified report |

Reuse: `runner_server.py` pipeline pieces, MBIT core, API Maven profiles (subprocess), mobile FailureClassificationHelper concepts.

## Impacted Selection

```text
Git Diff
  → Changed files
  → Map via docs/regression/impact-map.yaml
  → Features
  → Scenarios
  → Risk score
```

Example map entries:
- `apps/tasks/**` → FEATURE-010,020,021,022
- `features/rebotics_pog_reset/**` → FEATURE-020..024
- `ActionListRetailerTarget.swift` → FEATURE-020

Always allow `--mode=full`.

## Unattended Requirements

1. Non-interactive credentials via env/secrets  
2. Deterministic seeds  
3. Timeouts + retries only for classified infra  
4. Structured JSON result for CI  
5. Artifact upload (evidence zip)

## Non-goals (v1)

- Replacing Appium/Web suites entirely  
- Production mutating runs  
- AI auto-waivers  
