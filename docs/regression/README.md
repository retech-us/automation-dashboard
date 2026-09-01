# Regression Platform Discovery Pack

**Status:** Discovery complete — awaiting human approval before implementation.  
**Do not start coding** until `tasks/todo.md` Phase 0 human gate is checked.

| Doc | Description |
|-----|-------------|
| [00-executive-summary.md](./00-executive-summary.md) | Gaps, feasibility, recommendation, top risks/tasks |
| [01-system-architecture.md](./01-system-architecture.md) | As-is / to-be + options A–D |
| [02-feature-inventory.yaml](./02-feature-inventory.yaml) | Machine-readable features |
| [03-api-inventory.yaml](./03-api-inventory.yaml) | Critical APIs |
| [04-mobile-backend-contracts.md](./04-mobile-backend-contracts.md) | Contract break strategy |
| [05-workflow-map.md](./05-workflow-map.md) | E2E traces |
| [06-test-coverage-matrix.yaml](./06-test-coverage-matrix.yaml) | Coverage honesty |
| [07-headless-mobile-strategy.md](./07-headless-mobile-strategy.md) | Headless approach |
| [08-release-data-strategy.md](./08-release-data-strategy.md) | Data provisioning |
| [09-scenario-model.md](./09-scenario-model.md) | Scenario schema |
| [10-regression-orchestrator-design.md](./10-regression-orchestrator-design.md) | Orchestrator |
| [11-failure-classification.md](./11-failure-classification.md) | Failure taxonomy |
| [12-ai-analysis-design.md](./12-ai-analysis-design.md) | AI (non-authoritative) |
| [13-ci-cd-integration.md](./13-ci-cd-integration.md) | CI gates sketch |
| [GATES.md](./GATES.md) | Gate A/B/C how-to + status |
| [14-implementation-roadmap.md](./14-implementation-roadmap.md) | Phases 0–10 |
| [15-product-decisions.md](./15-product-decisions.md) | Locked product decisions |
| [16-genai-and-full-roadmap.md](./16-genai-and-full-roadmap.md) | GenAI as assistant + cover/not-cover |
| [17-genai-first-conversion.md](./17-genai-first-conversion.md) | How to become GenAI-first (control plane) |
| [BUILD_SLICES.md](./BUILD_SLICES.md) | **Incremental build + verify checklist** |
| [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md) | Explicit limits |

**Plans:** [`../../tasks/plan.md`](../../tasks/plan.md) · [`../../tasks/todo.md`](../../tasks/todo.md)

**What this is:** Autonomous regression platform (all mobile features, selectable `{env}.rebotics.net`) with an **integrated GenAI assistant** — not a GenAI-first test framework.  
**PASS/FAIL** comes only from deterministic asserts on real backend + real mobile code.
