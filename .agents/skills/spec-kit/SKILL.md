---
name: spec-kit
description: Official Spec-Driven Development (SDD) toolkit from GitHub (github/spec-kit). Define what to build before building it with executable specs, plan generation, dependency task breakdown, strict TDD implementation, consistency analysis, and convergence loops. Triggers on "spec-kit", "speckit", "spec-driven development", "specify", "constitution", "converge", or when building multi-step features with structured specification.
---

# 💫 Spec Kit: Spec-Driven Development (SDD)

> **"Define what to build before building it — with any AI coding agent."**
> Based on GitHub's official [github/spec-kit](https://github.com/github/spec-kit) toolkit.

---

## 1. Overview & Core Philosophy

Spec-Driven Development (SDD) flips traditional development: **specifications are executable artifacts** that directly drive architecture, task breakdown, implementation, and convergence verification.

```
CONSTITUTION ──→ SPECIFY ──→ PLAN ──→ TASKS ──→ IMPLEMENT ──→ CONVERGE
     │              │          │        │           │             │
     ▼              ▼          ▼        ▼           ▼             ▼
 Principles    User Stories  Tech &  Dependency   TDD Code      100% Spec
& Invariants   & Acceptance Architecture Ordering Execution   Verification
```

---

## 2. The Gated SDD Workflow

### Step 0: Constitution (`/speckit-constitution`)
* **Purpose**: Establish project-wide architectural invariants, non-negotiables, code standards, and boundaries once per repository.
* **Output Path**: `.specify/constitution.md` (or `docs/constitution.md`)
* **Sections**:
  1. **Core Principles** (e.g. strict null-safety, test coverage requirements, backward compatibility).
  2. **Architectural Guardrails** (permitted libraries, banned patterns, module boundaries).
  3. **Quality & Verification Standards** (linter rules, CI gates, performance budgets).

---

### Step 1: Specify (`/speckit-specify`)
* **Purpose**: Transform raw user intent into an unambiguous, testable feature specification.
* **Output Path**: `specs/<feature-name>/spec.md`
* **Key Requirements**:
  * Surface and document all assumptions before writing requirements.
  * Express every requirement as concrete, testable **Acceptance Criteria** (Given / When / Then or testable conditions).
  * Define **User Scenarios & Edge Cases**.
  * Explicitly define **Boundaries** (Always / Ask First / Never).
  * Use `templates/spec-template.md`.

---

### Step 2: Plan (`/speckit-plan`)
* **Purpose**: Design the technical architecture, data structures, module boundaries, and API contracts.
* **Output Path**: `specs/<feature-name>/plan.md`
* **Key Requirements**:
  * Technical Approach & Architecture Decisions (with rationale).
  * Data Models & Schema changes.
  * Component & Module Breakdown.
  * Risk Assessment & Mitigation strategies.
  * Research findings & documentation citations.
  * Use `templates/plan-template.md`.

---

### Step 3: Tasks (`/speckit-tasks`)
* **Purpose**: Break the technical plan into discrete, dependency-ordered, incrementally verifiable tasks.
* **Output Path**: `specs/<feature-name>/tasks.md`
* **Key Rules**:
  * Every task must have explicit **Acceptance Criteria** and a **Verification Command**.
  * Tasks are ordered by **dependency DAG** (foundations first, integrations next, polish last).
  * Group tasks into phases (Phase 1: Setup/Contracts ➔ Phase 2: Core Logic ➔ Phase 3: UI/Integration ➔ Phase 4: Verification).
  * Use `templates/tasks-template.md`.

---

### Step 4: Implement (`/speckit-implement`)
* **Purpose**: Execute the tasks one-by-one following strict Test-Driven Development (TDD).
* **Execution Protocol**:
  1. Select the next uncompleted task in `tasks.md`.
  2. Write the failing unit/integration test first (Red).
  3. Implement the minimal clean code to make the test pass (Green).
  4. Refactor and verify all project static analysis and existing tests pass.
  5. Check off the task in `tasks.md` with `- [x]`.

---

### Step 5: Converge (`/speckit-converge`)
* **Purpose**: Perform a rigorous delta audit comparing the codebase against the original `spec.md`, `plan.md`, and `tasks.md`.
* **Execution Protocol**:
  1. Inspect all modified and created files against every acceptance criterion in `spec.md`.
  2. Verify all edge cases and boundary conditions are covered with passing automated tests.
  3. If unbuilt gaps or discrepancies exist, append them to `tasks.md` and trigger `/speckit-implement`.
  4. Continue the convergence loop until **100% Converged & Verified**.

---

## 3. Extensions

### 🐞 Bug Fixing Extension (`/speckit-bug-*`)
Provides an evidence-based **Assess ➔ Fix ➔ Test** workflow for diagnosing and resolving defects:
1. **Assess (`/speckit-bug-assess`)**: Capture reproduction steps, root cause analysis, and failing test proof.
2. **Fix (`/speckit-bug-fix`)**: Apply surgical fix addressing the verified root cause.
3. **Test (`/speckit-bug-test`)**: Run regression suite and verify fix resolves the original issue without collateral breakages.

### 💡 Idea Assessment Extension (`/speckit-assess-*`)
Turns raw proposals into documented **Go / Clarify / Kill** decisions:
1. **Intake**: Problem framing & target audience.
2. **Research**: Technical feasibility, user demand, and alternatives.
3. **Define & Shape**: Goals, success metrics, and solution trade-offs.
4. **Decide**: Explicit decision with recorded justification.

---

## 4. Templates Reference

* `templates/constitution-template.md` — Project Constitution & Engineering Rules
* `templates/spec-template.md` — Feature Specification Template
* `templates/plan-template.md` — Technical Architecture & Implementation Plan Template
* `templates/tasks-template.md` — Dependency-Ordered Task List Template
* `templates/checklist-template.md` — Domain Quality & Verification Checklist Template
