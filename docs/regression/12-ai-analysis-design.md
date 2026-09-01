# 12 — AI Analysis Design

## Role of AI

AI is for **analysis, classification assistance, prioritization, explanation, and test-generation suggestions**.

AI is **NOT** allowed to:
- Mark a failed deterministic assertion as PASS
- Skip scenarios because it “believes” behavior is acceptable
- Mutate expected baselines silently

## Inputs

```text
Feature, Scenario, Git changes,
API request/response, DB snapshot, Mobile state,
Logs, Stack trace, Expected vs Actual,
Historical failures, Contract diff
```

## Outputs

```text
Suggested classification
Root cause hypothesis
Confidence (0-1)
Affected component
Potential regression blast radius
Recommended investigation steps
Optional new scenario suggestions
```

## Integration Point

```text
Deterministic engine → FAIL/PASS (authoritative)
        ↓ (on FAIL only)
AI analysis layer → annotation on report
```

## Existing Project Hooks

- Dashboard AI usage tab / Allure AI keys (observability)
- Mobile GenAI self-healing locators (UI ring only; observe mode preferred)
- Do not reuse locator-healing to alter IR domain assertions

## Safety

1. Store AI output separately under `evidence/ai_analysis.json`  
2. Report shows `assertion_result` vs `ai_suggestion` distinctly  
3. Prompt includes explicit instruction: never override assertions  
4. Human review required for any waiver  

## When AI Unavailable

Orchestrator still runs fully; analysis section shows `AI_UNAVAILABLE`.
