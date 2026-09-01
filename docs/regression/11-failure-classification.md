# 11 — Failure Classification

## Rule

Do not report only `TEST FAILED`. Every failure gets a class, evidence refs, and suggested owner.

## Taxonomy

| Class | Meaning |
|-------|---------|
| PRODUCT_BUG | Incorrect product behavior under valid scenario |
| BACKEND_BUG | Backend logic/API/DB wrong |
| MOBILE_BUG | Mobile domain/processing wrong (parity-proven) |
| API_CONTRACT_BREAK | Schema/status/enum incompatibility |
| DATA_PROBLEM | Bad/missing precondition data |
| ENVIRONMENT_PROBLEM | Auth throttle, DNS, tenant down, queue lag beyond SLO |
| TEST_FRAMEWORK_PROBLEM | Harness bug, wrong assertion, flaky driver |
| EXTERNAL_DEPENDENCY | Core/IdP/S3 outage |
| FLAKY_TEST | Non-deterministic; needs quarantine |
| UNKNOWN | Insufficient evidence |

Align with `retech-mobile-automation` `FailureClassificationHelper` and extend for contract/state classes.

## Required Failure Record Fields

```yaml
feature_id: FEATURE-021
scenario_id: SC-IR-004
step: reload_action_list
expected: pending_count == 12
actual: pending_count == 9
request: ...
response: ...
database_state_ref: evidence/db.json
mobile_state_ref: evidence/mobile.json
error: ...
stack_trace: ...
likely_root_cause: dropped cards on merge
confidence: 0.72
affected_release: 2.16.1
affected_components: [android ActionListPresenter, mbit ui_mapper]
suggested_owner: mobile-pog-reset
classification: MOBILE_BUG
```

## Classification Heuristics (deterministic first)

1. Env health check failed → ENVIRONMENT_PROBLEM  
2. Contract baseline diff → API_CONTRACT_BREAK  
3. Provisioning assert failed before actions → DATA_PROBLEM  
4. HTTP 5xx from Core with retries exhausted → EXTERNAL_DEPENDENCY or BACKEND_BUG  
5. API response violates business rule but matches schema → BACKEND_BUG  
6. API OK; Android unit canonical fails; Python matches Android → MOBILE_BUG  
7. API OK; Android unit passes; Python fails → TEST_FRAMEWORK_PROBLEM (parity drift)  
8. Pass on retry without code change → FLAKY_TEST  

AI may **suggest** class; deterministic engine records final class unless human overrides.
