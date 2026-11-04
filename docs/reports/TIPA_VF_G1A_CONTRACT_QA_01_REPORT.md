# TIPA-VF-G1A-CONTRACT-QA-01 — Executable schema / fixture QA report (resume)

**Issue:** [#133](https://github.com/hieudovn/virtual-factory/issues/133)  
**Task contract:** `.ai-harness/tasks/TIPA-VF-G1A-CONTRACT-QA-01.json`  
**Branch / PR:** `test/tipa-g1a-contract-qa` / [#146](https://github.com/hieudovn/virtual-factory/pull/146)  
**Mode:** Tier A supervised, single issue; resume of the existing branch/PR.

## 1. Status

```text
PM RESUME EVIDENCE — FOCUSED AND FULL REGRESSION PASS
Exact-head CI and P01–P24 gate: recorded in the PR/issue comment after push.
```

This report supersedes the earlier blocker report. The earlier red CI on
`11e35fa99dbfd2b3a9d37d2d25ccbc7471cdd263` is retained as pre-correction
evidence. The blocker was accepted by SA, corrected by Issue #147 / PR #148, and
merged to `main@d7d7aee1a226613dafc8d4db02e559634ccecd70`.

## 2. Resume protocol performed

| Step | Result |
|---|---|
| Clean worktree and exact remote branch head verified | PASS (`11e35fa99dbfd2b3a9d37d2d25ccbc7471cdd263` before resume) |
| Existing PR #146 ownership/state verified | OPEN, non-draft, base `main` |
| New main fetched | `d7d7aee1a226613dafc8d4db02e559634ccecd70` |
| Task JSON `expected_base_sha` reconciled | `2d876fd…` → `d7d7aee…` |
| Non-rewriting merge of `origin/main` | PASS; no conflicts; no rebase/reset/amend/force-push |
| New PR | NOT created |
| Merge/deploy/next Issue | NOT performed |

Ordered history on the resumed branch:

1. `11e35fa` — original tests/report (pre-correction evidence).
2. `a5b26cc` — baseline-reconciliation edit to the task JSON.
3. `5c49ff1` — non-rewriting merge of corrected `origin/main` (T01/T02 capacity strings).

## 3. Baseline, environment and preflight

| Field | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Required/current branch | `test/tipa-g1a-contract-qa` |
| Expected baseline | `d7d7aee1a226613dafc8d4db02e559634ccecd70` |
| `origin/main` at preflight | `d7d7aee1a226613dafc8d4db02e559634ccecd70` |
| Python | 3.12.3 |
| Environment | repo-local `.venv`; `pip install -e '.[dev]'`; no OS packages |
| `jsonschema` | 4.26.0 (Draft 2020-12) |
| `pytest` | 9.2.0 |
| Network schema fetch | none; in-memory `referencing.Registry` |
| Preflight | PASS |

## 4. Design inputs (read-only)

- `docs/design/tipa-g1/factory-run-v0.1.schema.json`
- `docs/design/tipa-g1/module-manifest-v0.1.schema.json`
- `docs/design/tipa-g1/factory-event-v0.1.schema.json`
- `docs/design/tipa-g1/material-transaction-v0.1.schema.json`
- `docs/design/tipa-g1/factory-scenario-fixture-v0.1.schema.json`
- `docs/design/tipa-g1/fixtures/T01_TWO_PRODUCERS_JOIN.json`
- `docs/design/tipa-g1/fixtures/T02_UPSTREAM_STARVATION.json`
- `docs/design/tipa-g1/G1A_SCHEMA_AND_FIXTURE_REGISTER_v0_1.md`
- `docs/design/tipa-g1/G1A_CORE_DETAILED_DESIGN_DECISION_DD01.md`

The SA correction changed only ten T01/T02 port capacities from numeric `20` to
decimal string `"20"` (Issue #147 / PR #148). No schema, test, DD-01 or runtime
change was made by this PM task.

## 5. Deliverables

| File | Purpose |
|---|---|
| `.ai-harness/tasks/TIPA-VF-G1A-CONTRACT-QA-01.json` | VF-native task contract, baseline reconciled to `d7d7aee` |
| `tests/contracts/test_tipa_g1a_schemas.py` | 5 meta-schema checks, local `$ref` resolution, T01/T02 validation, design-oracle structure |
| `tests/contracts/test_tipa_g1a_semantics.py` | Cross-record semantic negative tests |
| `tests/contracts/fixtures/tipa_g1a_invalid_cases.json` | Deterministic negative-case matrix |
| `docs/reports/TIPA_VF_G1A_CONTRACT_QA_01_REPORT.md` | This report |

No file outside the Issue #133 allowlist was modified by the PM. `.venv/` is
gitignored and is not a deliverable.

## 6. Executable results

### 6.1 Focused contract QA

```text
.venv/bin/python -m pytest -q tests/contracts/
# 42 passed
# exit 0
```

Includes:

- five Draft 2020-12 meta-schemas validate;
- scenario `$ref`s resolve through an in-memory registry with no network;
- T01 and T02 validate after the SA capacity correction;
- T01/T02 structural oracle checks (design expectation only);
- 29 data-driven invalid cases plus direct idempotency/EA/T02 checks.

### 6.2 Full regression

```text
.venv/bin/python -m pytest -q
# 1882 passed, 1 warning in 888.15s
# exit 0
```

No legacy ASSY, Bottled Water, discrete, MES bridge, UI or other regression. The
full suite was run with `gh` authentication neutralised to match CI visibility;
this is not a multi-repo compatibility claim (Issue #137).

## 7. Acceptance matrix

| Issue criterion | Result | Evidence |
|---|---|---|
| A01 Five Draft 2020-12 meta-schemas validate | **PASS** | 5/5 `check_schema` |
| A01 Local `$ref` resolves without network | **PASS** | in-memory `referencing.Registry` |
| A01 T01/T02 specifications validate | **PASS** | capacity correction merged from `d7d7aee` |
| A02 Negative semantic cases reject bad input | **PASS** | 42 passed focused tests |
| A03 Schema PASS separated from runtime oracle | **PASS** | oracle structure only; engine status `NOT_EXECUTED` |
| A04 Focused tests exit 0 | **PASS** | 42 passed |
| A04 Full regression exit 0 | **PASS** | 1882 passed |
| A04 Allowed paths only | **PASS** | task/tests/report only vs `d7d7aee` |
| A04 Exact-head CI success | **PENDING AT REPORT COMMIT** | recorded in PR/issue comment |
| A04 Remote SHA equality | **PENDING AT REPORT COMMIT** | recorded in PR/issue comment |

## 8. Negative semantic coverage (A02)

`tests/contracts/fixtures/tipa_g1a_invalid_cases.json` covers:

- absent identity (`factory_run_id`, `event_id`);
- bad contract version, generation, digest;
- numeric capacity, exponent, signed negative, leading-zero and bad-unit
  decimals;
- nonpositive and fractional `EA` quantity/capacity;
- invalid port direction and incompatible shared-buffer material types;
- duplicate `module_id`, duplicate `port_id`, duplicate event signature,
  duplicate parent consumption;
- source-kind vs definition-provenance confusion;
- wrong/naive/non-UTC time and epoch+tick mismatch;
- transaction idempotency: same key/same payload = no-op, same key/different
  payload = conflict, same transaction/different key = conflict;
- `TRANSFORM` requires parent and child refs;
- KG decimal quantity allowed while EA fractional quantity rejected;
- T02 has no phantom RSO2 `PRODUCE` event.

## 9. Design oracles — NOT EXECUTED

| Fixture | Intended design oracle | Engine status |
|---|---|---|
| T01 | Two parents received → one AP04 join → one Motor; `join_input_parent_count=2`, `join_output_motor_count=1`; no phantom material | **NOT_EXECUTED** — no G1A factory engine |
| T02 | RSO2 outage → AP04 `WAITING_FOR_MATERIAL`; zero join during starvation; zero local ASSY RSO2 replenish; no phantom WIP | **NOT_EXECUTED** — no G1A factory engine |

These are specification expectations, not engine PASS.

## 10. Remote evidence

| Field | Value |
|---|---|
| Pre-correction evidence | `11e35fa…`; VF-DM CI `41756813688` FAILURE (2 failed, 1880 passed) |
| Baseline-reconciliation commit | `a5b26cc…` |
| Non-rewriting merge commit | `5c49ff1…` (`origin/main@d7d7aee`) |
| Final branch HEAD / PR head / CI head | recorded in PR/issue comment after push |
| Exact-head VF-DM CI | recorded in PR/issue comment |
| P01–P24 gate | recorded in issue comment / `.ai-harness/traces/TIPA-VF-G1A-CONTRACT-QA-01/` |
| Merge/deploy | **NOT PERFORMED** |
| New PR | **NOT CREATED** |
| Next Issue | **NOT STARTED** |

## 11. Final status

```text
PM RESUME EVIDENCE — LOCAL FOCUSED/FULL PASS — EXACT-HEAD CI/GATE PENDING AT REPORT COMMIT
```

The PR/issue comment is authoritative for the final SHA, CI conclusion and the
P01–P24 gate result. PM does not self-certify COMPLETE/CLOSED, merge, deploy or
start the next Issue.
