# Build slices — **7 total** (execute in order; verify before next)

| # | Slice | Status |
|---|--------|--------|
| 1 | Foundations (env + image catalog + CLI) | ✅ VERIFIED |
| 2 | Auth smoke (login + `/me`) | ✅ VERIFIED |
| 3 | Provisioner skeleton (task + catalog images) | ✅ VERIFIED |
| 4 | Action-list fetch + contract assert | ✅ VERIFIED |
| 5 | Mobile domain assert (count parity) | ✅ VERIFIED |
| 6 | Regression agent tools JSON API | ✅ VERIFIED |
| 7 | CI PR bot (GenAI-first surface) | ✅ VERIFIED |

---

## Slice 1 — Foundations ✅ VERIFIED
## Slice 2 — Auth smoke ✅ VERIFIED

## Slice 3 — Provisioner skeleton ✅ VERIFIED
- [x] Plan provision with catalog-matched images only
- [x] Fail if category has no images (no wrong JPG fallback)
- [x] Dry-run by default (no backend mutate)
- [x] `--execute` path for create/select + upload (requires store/pog/task args)
- [x] Tests green (Slice 1–3 = **25/25**)

**Verified:**
```bash
python3 -m unittest regression.tests.test_slice1_env_and_images \
  regression.tests.test_slice2_auth_smoke \
  regression.tests.test_slice3_provisioner -v

python3 regression/cli.py provision --env=epsilon --category=pasta --bays=1,2
# pharmacy → exit 2

# Live mutate (optional — needs real IDs):
# python3 regression/cli.py provision --env=epsilon --category=pasta --bays=1 \
#   --store-id=... --pog-id=... --task-id=... --execute
```

## Slice 4 — Action-list fetch + contract assert ✅ VERIFIED
- [x] Contract baseline `docs/regression/baselines/action_list_retailer_contract.yaml`
- [x] Fetch `GET /api/v1/tasks/{id}/action-list/retailer/` (+ v4 fallback)
- [x] Deterministic schema/type/required/UPC/action-token asserts
- [x] CLI `action-list` with `--fixture` offline path
- [x] Tests green (Slice 1–4 = **44/44**)
- [x] Live epsilon: valid task returns JSON + contract ok; missing task → exit 1 (no HTML false-positive)

**Verified:**
```bash
python3 -m unittest regression.tests.test_slice1_env_and_images \
  regression.tests.test_slice2_auth_smoke \
  regression.tests.test_slice3_provisioner \
  regression.tests.test_slice4_action_list -v

python3 regression/cli.py action-list --env=epsilon --task-id=999 \
  --fixture=regression/tests/fixtures/action_list_retailer_sample.json

# Live (needs creds + real task):
python3 regression/cli.py action-list --env=epsilon --task-id=<id>
```

## Slice 5 — Mobile domain assert (count parity) ✅ VERIFIED
- [x] Android CAT1-T5 locked baseline `docs/regression/baselines/domain_count_parity.yaml`
- [x] Interim MBIT mapper wired via `regression/domain_parity.py` (explicit interim debt)
- [x] Parity-lock mapper: `fix_position_move_to_bay` → 1 SetAside; restock not FixInBay; add_to_bay → 2 cards
- [x] CLI `domain-parity` (baseline case / fixture assert; live = report counts)
- [x] Tests green (Slice 1–5 = **50/50**)

**Verified:**
```bash
python3 -m unittest regression.tests.test_slice1_env_and_images \
  regression.tests.test_slice2_auth_smoke \
  regression.tests.test_slice3_provisioner \
  regression.tests.test_slice4_action_list \
  regression.tests.test_slice5_domain_parity -v

python3 regression/cli.py domain-parity --env=epsilon --case=cat1_t5_mixed
# → domain_card_count=6 matching Android CAT1-T5

# Live report (no CAT1 assert on arbitrary tasks):
# python3 regression/cli.py domain-parity --env=epsilon --task-id=<id>
```

## Slice 6 — Regression agent tools JSON API ✅ VERIFIED
- [x] Tool registry `regression/tools.py` wrapping slices 1–5 (stable JSON I/O)
- [x] Verdict policy embedded: PASS/FAIL only from tool `ok`/`exit_code`
- [x] CLI: `tools list` / `tools call` / `tools serve`
- [x] HTTP: `GET /v1/tools`, `GET /v1/health`, `POST /v1/tools/{name}`, `POST /v1/tools/call`
- [x] Tests green (Slice 1–6 = **65/65**)

**Verified:**
```bash
python3 -m unittest regression.tests.test_slice1_env_and_images \
  regression.tests.test_slice2_auth_smoke \
  regression.tests.test_slice3_provisioner \
  regression.tests.test_slice4_action_list \
  regression.tests.test_slice5_domain_parity \
  regression.tests.test_slice6_tools_api -v

python3 regression/cli.py tools list
python3 regression/cli.py tools call resolve_env --args-json '{"env":"epsilon"}'
python3 regression/cli.py tools call domain_parity --args-json '{"env":"epsilon","case":"cat1_t5_mixed"}'

# Optional HTTP:
# python3 regression/cli.py tools serve --port=8765
# curl -s http://127.0.0.1:8765/v1/tools | jq .
# curl -s -X POST http://127.0.0.1:8765/v1/tools/resolve_env \
#   -H 'Content-Type: application/json' -d '{"env":"epsilon"}'
```

## Slice 7 — CI PR bot (GenAI-first surface) ✅ VERIFIED
- [x] Impact map `docs/regression/impact-map.yaml` + `regression/impact.py`
- [x] PR bot runner `regression/pr_bot.py` (tool pack → JSON report + markdown comment)
- [x] Narrative is template/control-plane text only — **never overrides** tool verdict
- [x] CLI `pr-bot run` (`--mode=smoke|impacted|full`, `--comment-out`, `--post-comment`)
- [x] GitHub Actions `.github/workflows/regression-pr-bot.yml` (unittest + Gate A pack + PR comment)
- [x] Tests green (Slice 1–7 = **73/73**)

**Verified:**
```bash
python3 -m unittest \
  regression.tests.test_slice1_env_and_images \
  regression.tests.test_slice2_auth_smoke \
  regression.tests.test_slice3_provisioner \
  regression.tests.test_slice4_action_list \
  regression.tests.test_slice5_domain_parity \
  regression.tests.test_slice6_tools_api \
  regression.tests.test_slice7_pr_bot -v

python3 regression/cli.py pr-bot run --env=epsilon --mode=smoke \
  --json-out=/tmp/reg-pr.json --comment-out=/tmp/reg-pr.md
# Verdict PASS from tools; narrative source=template
```
