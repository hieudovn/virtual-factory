# TIPA-VF-G1A-CONTRACT-QA-01 — Executable schema / fixture QA report

**Issue:** [#133](https://github.com/hieudovn/virtual-factory/issues/133)  
**Task contract:** `.ai-harness/tasks/TIPA-VF-G1A-CONTRACT-QA-01.json`  
**Governance:** `.ai-harness/PM-EXECUTION-CONTRACT.md`, VF OpenCode/VPS authoring addendum  
**Mode:** Tier A supervised, single issue. Read-only against published G1A designs.

## 1. Status

```text
BLOCKED — SCHEMA/FIXTURE CONTRADICTION
Focused contract QA: FAIL (2 failed, 40 passed)
Full regression: FAIL (2 failed, 1880 passed)
```

The failure is **not** a runtime regression. The published T01/T02 fixtures use
numeric `capacity: 20`, while the published module-manifest schema (after the
DD-01 decimal-string clarification) accepts only a decimal **string** or `null`
for `capacity`. The QA tests fail exactly on that contradiction. This report does
not edit either published file.

Per Issue #133 stop conditions, PM stops here: no schema/fixture rewrite, no
runtime implementation, no merge/deploy, no next Issue.

## 2. Baseline and environment

| Field | Value |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| Required branch | `test/tipa-g1a-contract-qa` |
| Expected baseline | `2d876fd4bb9ce060dd72cc5b2db0dd959b09ef9e` |
| Actual `origin/main` at preflight | `2d876fd4bb9ce060dd72cc5b2db0dd959b09ef9e` |
| Remote work branch before start | absent |
| Working tree before mutation | clean |
| Preflight | **PASS** (`preflight.py --task .ai-harness/tasks/TIPA-VF-G1A-CONTRACT-QA-01.json`) |
| Python | 3.12.3 |
| Test environment | repo-local `.venv` (`python -m venv .venv` + `pip install -e '.[dev]'`); no OS packages installed |
| `jsonschema` | 4.26.0 (Draft 2020-12) |
| `pytest` | 9.2.0 |
| GitHub CLI/token | authenticated; read-only design inspection |
| Network schema fetch | none; in-memory `referencing.Registry` only |

Task JSON was the only file committed before preflight, as the explicitly
permitted bootstrap.

## 3. Design inputs inspected (read-only)

- `docs/design/tipa-g1/factory-run-v0.1.schema.json`
- `docs/design/tipa-g1/module-manifest-v0.1.schema.json`
- `docs/design/tipa-g1/factory-event-v0.1.schema.json`
- `docs/design/tipa-g1/material-transaction-v0.1.schema.json`
- `docs/design/tipa-g1/factory-scenario-fixture-v0.1.schema.json`
- `docs/design/tipa-g1/fixtures/T01_TWO_PRODUCERS_JOIN.json`
- `docs/design/tipa-g1/fixtures/T02_UPSTREAM_STARVATION.json`
- `docs/design/tipa-g1/G1A_SCHEMA_AND_FIXTURE_REGISTER_v0_1.md`
- `docs/design/tipa-g1/G1A_CORE_DETAILED_DESIGN_DECISION_DD01.md`
- PR #132 design source / merged documentation baseline

## 4. Deliverables

| File | Purpose |
|---|---|
| `.ai-harness/tasks/TIPA-VF-G1A-CONTRACT-QA-01.json` | VF-native task contract |
| `tests/contracts/test_tipa_g1a_schemas.py` | 5 meta-schema checks, local `$ref` resolution, T01/T02 validation, design-oracle structure |
| `tests/contracts/test_tipa_g1a_semantics.py` | Cross-record semantic negative tests |
| `tests/contracts/fixtures/tipa_g1a_invalid_cases.json` | Deterministic negative-case matrix |
| `docs/reports/TIPA_VF_G1A_CONTRACT_QA_01_REPORT.md` | This report |

No file outside the Issue #133 allowlist was modified. `.venv/` is gitignored and
is not a deliverable.

## 5. Executable results

### 5.1 Focused contract QA

```text
.venv/bin/python -m pytest -q tests/contracts/
# 2 failed, 40 passed, 1 warning
# exit 1
```

Only these two tests fail:

- `tests/contracts/test_tipa_g1a_schemas.py::test_published_t01_t02_fixtures_validate[T01_TWO_PRODUCERS_JOIN.json]`
- `tests/contracts/test_tipa_g1a_schemas.py::test_published_t01_t02_fixtures_validate[T02_UPSTREAM_STARVATION.json]`

Each fixture produces 5 identical-capacity errors (one per port):

```text
['modules', 0, 'ports', 0, 'capacity']: 20 is not valid under any of the given schemas
['modules', 1, 'ports', 0, 'capacity']: 20 is not valid under any of the given schemas
['modules', 2, 'ports', 0, 'capacity']: 20 is not valid under any of the given schemas
['modules', 2, 'ports', 1, 'capacity']: 20 is not valid under any of the given schemas
['modules', 2, 'ports', 2, 'capacity']: 20 is not valid under any of the given schemas
```

### 5.2 Full regression

```text
.venv/bin/python -m pytest -q
# 2 failed, 1880 passed, 1 warning in 932.53s
# exit 1
```

The two failures are the same published-fixture capacity cases. No legacy ASSY,
Bottled Water, discrete, MES bridge, UI or other test regressed. The full suite
was run with `gh` authentication neutralised to match the CI visibility baseline;
this is **not** a multi-repo compatibility claim (see Issue #137). It is only
used to keep the unrelated PlantOS-visibility test deterministic.

## 6. Contradiction analysis

### 6.1 Schema side

`docs/design/tipa-g1/module-manifest-v0.1.schema.json:132-145` defines port
`capacity` as:

```json
"anyOf": [
  {
    "type": "string",
    "pattern": "^(?:0|[1-9][0-9]*)(?:\\.[0-9]+)?$"
  },
  { "type": "null" }
]
```

The description says: decimal quantity in port unit, never floating point;
non-negative decimal string; nonzero/UOM precision checked semantically.

DD-01 §2 reinforces: authoritative material quantities **and buffer capacities**
are base-10 decimal strings, parse as `Decimal`, reject exponent/NaN/signed
negative, and `EA` is integral.

### 6.2 Fixture side

T01 and T02 each declare five module ports with numeric capacity:

```json
"capacity": 20
```

Examples:

- `docs/design/tipa-g1/fixtures/T01_TWO_PRODUCERS_JOIN.json:51,80,111,122,133`
- `docs/design/tipa-g1/fixtures/T02_UPSTREAM_STARVATION.json:51,80,111,122,133`

JSON Schema Draft 2020-12 does not coerce `20` into `"20"`. Therefore the
fixtures fail the published schema; the failure is reproduced with
`jsonschema==4.26.0` and an in-memory local registry (no network).

### 6.3 Impact

- A01 cannot pass: the five meta-schemas and local `$ref`s are valid, but T01/T02
  do not validate.
- Any downstream G2A implementation that consumes the published fixtures would
  receive invalid capacities unless it silently coerces numbers to strings.
  Silent coercion is not authorized: DD-01 requires explicit Decimal strings and
  semantic validation, not float/JSON-number normalization.
- The contradiction is confined to published design artifacts; no production
  code is implicated.

### 6.4 Required SA decision

SA must resolve one of:

1. republish T01/T02 with `"capacity": "20"` (and any other decimal strings), or
2. revise the schema if numeric capacity is intentionally allowed (contradicts
   DD-01 as written).

PM must not choose either. This task is forbidden from editing `docs/design/`.

## 7. Acceptance matrix

| Issue criterion | Result | Evidence |
|---|---|---|
| A01 Five Draft 2020-12 meta-schemas validate | **PASS** | 5/5 `check_schema`; local registry |
| A01 Local `$ref` resolves without network | **PASS** | `referencing.Registry`; no HTTP |
| A01 T01/T02 specifications validate | **FAIL** | 10 capacity errors (5 per fixture) |
| A02 Negative semantic cases reject bad input | **PASS** | 40 passed contract tests; matrix below |
| A03 Schema PASS separated from runtime oracle | **PASS** | T01/T02 oracle tests assert structure only; engine status `NOT_EXECUTED` |
| A04 Focused tests exit 0 | **FAIL** | 2 failed, 40 passed |
| A04 Full regression exit 0 | **FAIL** | 2 failed, 1880 passed (only fixture contradiction) |
| A04 Allowed paths only | **PASS** | Git diff restricted to task/tests/report |
| A04 Exact-head CI success | **FAIL / PENDING at authoring** | CI must be red because committed QA tests reproduce the blocker |
| A04 Remote SHA equality | **PENDING at authoring** | Recorded from PR/CI after push |

## 8. Negative semantic coverage (A02)

`tests/contracts/fixtures/tipa_g1a_invalid_cases.json` contains deterministic
cases for:

- absent identity (`factory_run_id`, `event_id`);
- bad contract version;
- bad generation / bad digest;
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
- TRANSFORM requires parent and child refs;
- KG decimal quantity allowed while EA fractional quantity rejected;
- T02 has no phantom RSO2 `PRODUCE` event.

All of these pass. Only the published-fixture validation fails.

## 9. Design oracles — NOT EXECUTED

| Fixture | Intended design oracle | Engine status |
|---|---|---|
| T01 | Two parents received → one AP04 join → one Motor; `join_input_parent_count=2`, `join_output_motor_count=1`; no phantom material | **NOT_EXECUTED** — no G1A factory engine |
| T02 | RSO2 outage → AP04 `WAITING_FOR_MATERIAL`; zero join during starvation; zero local ASSY RSO2 replenish; no phantom WIP | **NOT_EXECUTED** — no G1A factory engine |

These are specification expectations, not engine PASS. No runtime implementation
was added by this task.

## 10. Remote evidence

| Field | Value |
|---|---|
| Task/bootstrap commit | `4958262c24f3b5be19cf7531ffe93463fb4042f1` |
| Final branch HEAD | recorded in PR/issue comment after push |
| PR | recorded in issue comment |
| Exact-head CI | expected **FAILED** because the committed contract tests reproduce the blocker; the run id/SHA are recorded in the issue comment |
| Merge/deploy | **NOT PERFORMED** |
| Next Issue | **NOT STARTED** |

## 11. Final status

```text
BLOCKED — SCHEMA/FIXTURE CONTRADICTION
```

The QA tests are committed as executable evidence. They must remain red until SA
either republishes the fixtures with decimal-string capacities or changes the
schema/DD-01 policy. PM does not self-certify, merge, deploy or proceed.
