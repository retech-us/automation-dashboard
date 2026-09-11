<!--
Sync Impact Report
==================
- Version change: Initial Draft → v1.0.0
- Added Sections:
  * Core Principles (I. Code Quality & Type Safety, II. Test-First Verification, III. User Experience Consistency, IV. Performance & Low Latency, V. Backward Compatibility & State Preservation)
  * Quality Gates & Verification Standards
  * Operational & Performance Requirements
  * Development Workflow & SDD Gating
  * Governance & Evolution Rules
- Follow-up TODOs: None (Fully ratified initial baseline)
-->

# Automation Dashboard & Mobile Integration Constitution

## Core Principles

### I. Code Quality, Modularity & Type Safety
- **Single Responsibility & Pure Mappers**: Every module, class, and utility must have a single, unambiguous purpose. Business and domain logic (such as action classification and coordinates calculation) must remain strictly decoupled from transport, rendering, or UI presentation layers.
- **Strict Typing & Null-Safety**: Dynamic typing and implicit fallback guessing are prohibited for core domain entities. All data models must use explicit types (dataclasses/Pydantic in Python, strict null-safe types in Dart/Kotlin/Swift) with validated boundaries and fallbacks.
- **Clean Architecture & Zero Bloat**: Reject speculative abstractions and unused code. Standard library utilities must be preferred before introducing external dependencies. Dead code, orphaned actions, and unused endpoints must be purged proactively.

### II. Test-First Standards & Automated Verification (NON-NEGOTIABLE)
- **TDD Mandatory (Red-Green-Refactor)**: No production logic or mapper change may be written without a prior or paired failing test. Code cannot be declared complete until verified against automated unit and integration suites.
- **100% Gated Static Analysis**: Immediate static analysis (`flutter analyze`, Python linters, or compiler checks) must execute cleanly with zero errors before handing code back or merging.
- **Edge Case & Failure Simulation**: Every workflow must be tested against simulated edge cases: interrupted sessions, mid-task app reloads, network dropouts (HTTP 401, 500, timeouts), and duplicate/multi-facing items.
- **Deterministic & Flake-Free Execution**: Tests must not rely on fragile wall-clock sleeps or non-deterministic shared global state. Test runs must be 100% reproducible and isolated.

### III. User Experience & Visual Consistency
- **Design Excellence & Premium Aesthetics**: Interfaces must feel polished, responsive, and alive. Use curated, modern color palettes, crisp typography (e.g. Inter, JetBrains Mono), smooth micro-interactions, and accessible contrast ratios (WCAG 2.2 AA).
- **Explicit Status & Zero Silent Failures**: The user must never be left wondering what happened. Every action, network transaction, or state change must provide immediate visual feedback (loading spinners, distinct banners, clear badge pills, or actionable error banners).
- **Responsive & Overflow-Resistant**: UI elements inside containers, rows, and cards must be wrapped with overflow protection (`Flexible`, `Expanded`, text ellipses) to guarantee clean rendering across desktop browsers, tablets, and handheld devices.
- **Theme & Mode Fidelity**: All visual components must cleanly support dynamic theme switching (Dark Mode and Light Mode) without hardcoded clashing colors.

### IV. Performance, Latency & Resource Efficiency
- **Sub-100ms In-Memory Processing**: Local action list transformations, deduplication, sorting, and domain mapping across multi-bay planograms (500+ items) must complete in under 100ms without blocking UI frames.
- **Fast Dynamic Reports & Cache Invalidation**: Dynamic validation reports and diagnostic APIs must generate and stream in under 1 second. Diagnostic endpoints must enforce `no-store, no-cache, max-age=0` to guarantee fresh data.
- **Minimal Payload & Network Optimization**: Network payloads must be compressed and structured efficiently. Redundant polling must be replaced with reactive event triggers or targeted health checks.
- **Memory Leak & Resource Lifecycle Guarding**: All background daemons, network streams, and temporary file handles must be cleanly closed and disposed of to prevent memory leaks and zombie processes.

### V. State Preservation & Backward Compatibility Invariants
- **Multi-Tenant & Multi-Retailer Isolation**: Domain logic, scan parsers, and API adapters must seamlessly handle multi-tenant environments (e.g. Harris Teeter, Epsilon, KRCS) with zero cross-instance credential or state contamination.
- **Sub-Action State Preservation**: Cross-bay movements and multi-step actions (Pick ➔ Place) must maintain hierarchical sub-action states (`current_position.state` and `expected_position.state`). Under no circumstances may mid-task app reloads, crashes, or session handoffs drop pending placement instructions.
- **Mathematical Conservation**: The total number of raw backend detections must equal the physical actionable cards in local memory. Actions cannot disappear or multiply spuriously on task reload.

---

## Quality Gates & Verification Standards

1. **Pre-Implementation Verification**:
   - Trace affected files, schema contracts, and UI states.
   - Confirm compatibility with both mobile (Android/iOS) and dashboard runners.
2. **Post-Implementation Verification**:
   - Execute full test suite (`python3 -m unittest` / `flutter test`). All suites must achieve 100% pass rate.
   - Verify generated reports (e.g. `IR_Backward_Compatibility_Test_Report_*.html` and `IR_Task_*_State_Transition_And_Validation_Report.html`).
   - Validate HTTP status and cache headers on all local web endpoints.
3. **Zero Regression Policy**:
   - Any commit or pull request that introduces regressions in action count, causes dropped cards on reload, or breaks existing integration benchmarks is rejected immediately.

---

## Development Workflow & SDD Gating

All non-trivial changes, new features, and major refactors must follow the Gated Spec-Driven Development workflow:

```
CONSTITUTION ──→ SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT ──→ CONVERGE
```

1. **Specify**: Formulate unambiguous requirements and acceptance criteria before coding.
2. **Plan**: Design architectural components, contracts, and schema changes.
3. **Tasks**: Break implementation into dependency-ordered, individually verifiable units.
4. **Implement**: Execute tasks iteratively under strict TDD.
5. **Converge**: Audit delta between implementation and specification until 100% compliant.

---

## Governance

- **Supremacy**: This Constitution represents the highest-priority engineering standard for the codebase. All pair-programming workflows, agent tasks, and human pull requests must comply with these principles.
- **Amendments**: Amendments to this document require documented rationale, impact analysis, and a semantic version increment:
  - **MAJOR (X.0.0)**: Removal or fundamental redefinition of core principles/invariants.
  - **MINOR (1.X.0)**: Addition of new principles, quality gates, or expanded domain standards.
  - **PATCH (1.0.X)**: Wording refinements, clarifications, and non-semantic corrections.

---

**Version**: 1.0.0 | **Ratified**: 2026-08-26 | **Last Amended**: 2026-08-26
