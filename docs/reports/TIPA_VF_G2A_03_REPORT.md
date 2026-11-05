# TIPA-VF-G2A-03 — Coordinator ↔ Material Ledger committed-fact bridge

**Issue:** [#151](https://github.com/hieudovn/virtual-factory/issues/151)

**Task contract:** `.ai-harness/tasks/TIPA-VF-G2A-03.json`

**Requested gate:** `ready_for_sa_review`

**Branch:** `feature/tipa-g2a-material-bridge`

**Expected base:** `baa30099c0772686236c9b64390e27097bf48585`

**Implementation commit:** `3ebe703d6bc107df6b64c08153edf39b3661c590`

**Mode:** supervised single-Issue implementation; no merge, deploy or next Issue.

## 1. Status

```text
NOT READY — INSUFFICIENT REMOTE EVIDENCE (PR CREATION BLOCKED)
```

The implementation, focused bridge tests, factory partition and exact-head
VF-DM CI on the implementation push pass. The bounded full regression
partitions are complete; one partition-B test is a local token-visibility
artifact and passes with CI-equivalent token visibility, while the CI full
suite is 1985/1985 PASS. The GitHub credential available to this supervised run
can push commits but is **not authorized to create pull requests**:

```text
gh pr create ... -> GraphQL: Resource not accessible by personal access token
POST /repos/hieudovn/virtual-factory/pulls -> HTTP 403
"Resource not accessible by personal access token"
```

No PR exists (`gh pr list --head feature/tipa-g2a-material-bridge` is empty),
so the P01–P24 `ready_for_sa_review` gate cannot complete its PR-dependent
steps. This report does not claim SA review, merge authorization, deployment,
production readiness or the next Issue. The branch and exact-head CI are
available for review through the compare URL in section 9.

## 2. Baseline and bootstrap

| Step | Result |
|---|---|
| Repository | `hieudovn/virtual-factory` |
| `git fetch origin main` | PASS |
| Fetched `origin/main` | `baa30099c0772686236c9b64390e27097bf48585` |
| GitHub remote `main` | `baa30099c0772686236c9b64390e27097bf48585` |
| Target remote branch before bootstrap | absent |
| New branch | `feature/tipa-g2a-material-bridge` from the exact base |
| Task-only bootstrap commit | `ab161a5` (task JSON only) |
| Preflight after bootstrap | PASS (`PRECHECK PASSED`, exit 0) |
| Implementation commit | `3ebe703d6bc107df6b64c08153edf39b3661c590` |

The preflight evidence recorded a clean worktree, branch
`feature/tipa-g2a-material-bridge`, local head `ab161a5b9d7ec2fea28b274b5deda9fc5c6ee509`,
remote main `baa30099…`, and `baseline_match: true`. No existing #127/#128
worktree was reset, stashed, rebased, overwritten, force-pushed or deleted.

## 3. Deliverables

| File | Purpose |
|---|---|
| `src/virtual_factory/factory/integration/__init__.py` | Public integration surface |
| `src/virtual_factory/factory/integration/contracts.py` | Immutable identity, policy, intent, outcome, projection-status and checkpoint contracts |
| `src/virtual_factory/factory/integration/outbox_projection.py` | Source-only `ISimulationModule` projection of committed ledger outbox |
| `src/virtual_factory/factory/integration/material_bridge.py` | Durable-first commit, reconciliation, checkpoint and rebuild surface |
| `src/virtual_factory/factory/integration/checkpoint.py` | Additive checkpoint construction and strict live-ledger validation |
| `tests/factory/test_material_bridge_contract.py` | Identity, generation, clock, policy, idempotency, wait and error oracles |
| `tests/factory/test_material_bridge_projection.py` | Source-only projection, event ordering, side-effect-free propose and clock oracles |
| `tests/factory/test_material_bridge_recovery.py` | Projection interruption, restart rebuild, checkpoint restore and corrupt-journal oracles |
| `tests/factory/test_material_bridge_contention.py` | Same-tick deterministic contention, duplicate replay and canonical replay equality |
| `docs/reports/TIPA_VF_G2A_03_REPORT.md` | This report |
| `.ai-harness/tasks/TIPA-VF-G2A-03.json` | Authorized task contract bootstrap |

Only the 11 allowlisted paths were changed. No coordinator, event-ledger,
run-context, module-contract or material-package source was edited.

## 4. Contract and protocol summary

- `MaterialBridge` requires an explicit `FactoryRunContext` generation `>= 1`
  and an explicitly supplied material `definition_digest`. It retains
  `workspace_digest` and `definition_digest` as separate values, together with
  `config_digest`, `model_revision`, `seed`, UTC `epoch_utc`, `run_id` and
  `generation`. It validates the material journal header against those values
  instead of comparing workspace and definition digests.
- `MaterialIntent` carries the complete `vf-material-transaction-v0.1` payload
  plus run/generation, tick, origin module, local sequence, transaction id,
  idempotency key and pinned ledger expected version. Construction and
  `validate_intent` are strict and side-effect-free.
- `commit_material_intent` validates first, then calls
  `MaterialFlowLedger.apply_transaction(tx, expected_version)`. Material facts
  are durable before any event projection. It never advances the coordinator
  clock, never retries at a new version and never mutates projection state.
- `OutboxProjectionModule` implements `ISimulationModule` with stable module id
  `vf.material.outbox-projection`. It reads the ledger-owned outbox only,
  proposes `EventProposal` values with source `event_id`, source `tick_us`,
  stable source index and canonical source-outbox digest, and advances its own
  cursor only in `apply_committed`.
- Projected `source_kind` and `definition_provenance` come from the immutable
  `BridgePolicy` (G1A enum values), never from the outbox event type or a
  caller string. The material transaction must agree with that policy.
- `reconcile_committed_outbox` verifies every projected event against exactly
  one committed source outbox row and digest. It returns `PENDING` for
  not-yet-projected source rows, `RECOVERY_REQUIRED` for source rows older than
  the coordinator clock and `INCOMPATIBLE` for any projection/source mismatch.
- `checkpoint` is additive to the existing coordinator checkpoint. It is only
  available at a quiescent `PAUSED` boundary with no unprojected outbox and
  contains pinned identity/header digests, material journal version/state
  digest, source outbox ids/digests/order, projection trace/digest and module
  snapshot identity.
- `restore_or_rebuild` restores a fully validated checkpoint or rebuilds a
  fresh `FactoryRunContext`/`SerialFactoryCoordinator` and replays the source
  outbox. If the old coordinator contains non-material events that cannot be
  reproduced from the material journal, it returns `RECOVERY_REQUIRED` and does
  not claim a full-factory replay.

## 5. Test evidence

### 5.1 Focused `done_when`

```text
.venv/bin/python -m pytest -q \
  tests/factory/test_material_bridge_contract.py \
  tests/factory/test_material_bridge_projection.py \
  tests/factory/test_material_bridge_recovery.py \
  tests/factory/test_material_bridge_contention.py
35 passed
```

### 5.2 Factory partition

```text
.venv/bin/python -m pytest -q tests/factory/
103 passed
```

### 5.3 Full regression

A single full-suite invocation was killed by the local runtime without a final
summary. The contract permits bounded exhaustive partitions in that case. The
three disjoint partitions cover every collected test exactly once
(`pytest --collect-only -q`: 1985 tests):

| Partition | Scope | Result |
|---|---|---|
| A | All tests except DDAY-B4/B5/B6/B7/FR1/UAT/UI-deploy | **1838 passed** |
| B | DDAY-B5/B6/B7/FR1/UAT/UI-deploy | **116 passed, 1 environment-only failure** |
| C | DDAY-B4 bottled-water factory | **30 passed** |

The partition-B failure is
`test_c01_06_plantos_compatibility_records_exact_gap`. It is not caused by this
change: the local GitHub token can see `hieudovn/PlantOS`, so
`compatibility_status(live_probe=True)` returns one PlantOS-named repo, while
the test asserts the CI-visible empty list. Re-running that exact test with the
CI-equivalent token visibility (`GH_TOKEN=definitely-invalid`) passes:

```text
GH_TOKEN=definitely-invalid .venv/bin/python -m pytest -q \
  tests/test_dday_b6_c01_contract_fidelity.py::test_c01_06_plantos_compatibility_records_exact_gap
1 passed
```

The authoritative full-suite run is the exact-head CI run below:
**1985 passed, 1 warning in 439.98s (0:07:19)**.

### 5.4 Exact-head CI

| Field | Value |
|---|---|
| Workflow | `VF-DM CI` |
| Event | `push` |
| Run id | `41972630444` |
| Head SHA | `3ebe703d6bc107df6b64c08153edf39b3661c590` |
| Conclusion | **success** |
| Test step | `1985 passed, 1 warning in 439.98s` |

This run is on the implementation commit, not on the report-only commit that
adds this file. The final report commit is a docs-only follow-up whose
exact-head CI is the SHA reported in the PM final evidence; it is not claimed
here before that run exists.

### 5.5 Failure-matrix oracles

| Boundary | Result | Test oracle |
|---|---|---|
| Invalid generation/clock/identity before material apply | `REJECTED_CONTRACT`, no journal/event mutation | `test_material_bridge_contract.py` |
| Two contenders for one material at same tick | Stable winner, loser `WAITING_FOR_MATERIAL`, one reservation | `test_material_bridge_contention.py` |
| Post durable material commit / pre-projection crash | Receipt and outbox remain; rebuild projects exactly once | `test_material_bridge_recovery.py` |
| Mid-projection exception | Material state unchanged; no duplicate outbox/genealogy; retry converges | `test_material_bridge_recovery.py` |
| Post event projection / pre-ack interruption | Duplicate intent returns original receipt; event id validated once | `test_material_bridge_contention.py` |
| Stale material expected version | `REJECTED_VERSION`, no implicit retry or version jump | `test_material_bridge_contract.py` |
| Foreign run/generation/header, stale checkpoint, corrupted journal | Fail closed before new stock/event | `test_material_bridge_contract.py`, `test_material_bridge_recovery.py` |
| Future outbox while coordinator clock earlier | Runs to exact event time; deterministic trace | `test_material_bridge_projection.py` |
| Source outbox event older than coordinator clock | `RECOVERY_REQUIRED`; no event appended | `test_material_bridge_projection.py` |

## 6. Acceptance matrix

| ID | Result | Evidence |
|---|---|---|
| P01 Focused bridge tests pass | **PASS** | 35 passed, exit 0 |
| P02 Zero required regression failures | **PASS** | CI exact head 1985 passed; local partitions A/B/C with the documented token-only live-probe exception rerun as PASS |
| P03 Exact-head CI succeeds | **PASS (implementation commit)** | `VF-DM CI` run `41972630444` success at `3ebe703d6bc1…`; docs-only report head re-checked in final evidence |
| F01 Bridge report committed | **PASS** | This file in the report-only commit |
| F02 Task JSON committed | **PASS** | Bootstrap `ab161a5` plus this branch |
| F03 No forbidden actions | **PASS** | Allowlist-only changes; no merge, deploy, OS install, credential modification or next Issue |
| F04 All canonical gate steps executed | **UNKNOWN** | P01–P24 gate not run: no PR exists, so P08/P09 cannot pass |
| F05 All required gate steps pass | **UNKNOWN** | Depends on F04 |
| F06 Review HEAD exists remotely | **UNKNOWN** | Branch head exists remotely; no PR review head exists because PR creation is blocked |

`ready_for_sa_review` is deliberately **not** claimed. Any required gate item
that is UNKNOWN prevents that status under the PM execution contract.

## 7. Blockers

The only unresolved blocker is remote PR creation:

```text
gh pr create --base main --head feature/tipa-g2a-material-bridge ...
GraphQL: Resource not accessible by personal access token (createPullRequest)

gh api repos/hieudovn/virtual-factory/pulls -X POST ...
HTTP 403 Resource not accessible by personal access token
```

The credential successfully pushed
`feature/tipa-g2a-material-bridge` and the read-only CI/PR APIs work. The
fine-grained token therefore lacks the `Pull requests: Read and write`
permission needed to open the authorized non-draft PR. Granting that permission
(or having an authorized human open the PR) is required before the P01–P24
`ready_for_sa_review` gate and F04/F05/F06 can be completed. No merge, deploy or
next Issue is authorized or attempted.

## 8. Limitations

- The material journal is the sole durable material authority. The event ledger
  remains an in-memory, rebuildable projection. There is no two-journal
  distributed atomicity, shared transaction, durable coordinator state or
  event-ledger persistence claim.
- A successful material commit followed by projection failure does not roll
  back stock. It returns `PENDING`/recovery-required and preserves the receipt,
  outbox and genealogy. Recovery projects once; it never issues compensating
  material production.
- Restart policy is source-journal rebuild, not full-factory replay. If the old
  coordinator had non-material events that cannot be reproduced from the
  material journal, the bridge returns `RECOVERY_REQUIRED` and stops.
- Durability relies on local `fsync`, directory `fsync` and POSIX `flock`
  single-writer scope. It is not a distributed lease, network-filesystem
  guarantee or power-loss proof for every storage device.
- The projection module is synthetic and internal. No MES/QMS/PlantOS ingress,
  external publisher, broker, database, worker concurrency or live endpoint is
  used.
- No ASSY, Water Bottle, discrete, Facility, SSO2/RSO2 adapter, real T01/T02
  runtime, real line capacity or production readiness is claimed. Existing G2A
  cores and old simulation sources are untouched.
- The bridge checkpoint is additive. `SerialFactoryCoordinator.checkpoint` is
  not altered or extended.
- The report-only commit is not the implementation commit; the exact final
  branch/PR/CI SHA equality is reported in the PM final evidence and the PR
  checks, not fabricated inside a self-referential commit.

## 9. Remote pointers

- Branch: <https://github.com/hieudovn/virtual-factory/tree/feature/tipa-g2a-material-bridge>
- Implementation commit: <https://github.com/hieudovn/virtual-factory/commit/3ebe703d6bc107df6b64c08153edf39b3661c590>
- Compare view (no PR could be created): <https://github.com/hieudovn/virtual-factory/compare/main...feature/tipa-g2a-material-bridge>
- Exact-head CI: <https://github.com/hieudovn/virtual-factory/actions/runs/41972630444>
- Pull request: **none** — creation blocked by token permission
