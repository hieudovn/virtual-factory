# TIPA-VF-G2A-01 — Factory Coordinator report

**Issue:** [#127](https://github.com/hieudovn/virtual-factory/issues/127)

**Task contract:** `.ai-harness/tasks/TIPA-VF-G2A-01.json`

**Requested gate:** `ready_for_sa_review`

**Branch:** `feature/tipa-g2a-factory-coordinator`

**Expected base:** `6ac764948d3e2e2e5fad11cf46aced5d16d67bb8`

**Mode:** Tier A supervised, single Issue; no merge, deploy or next Issue.

## 1. Status

```text
PM IMPLEMENTED — DRAFT PR OPEN — LOCAL TESTS PASS — EXACT-HEAD CI/GATE NOT MONITORED
```

The final exact branch HEAD and PR link are recorded in the PM run report after
push. This document is committed at the same report/PR head and does not claim
CI success, SA approval, merge or production readiness.

## 2. Baseline and bootstrap

| Step | Result |
|---|---|
| Remote repository | `hieudovn/virtual-factory` |
| Existing #133 checkout | `test/tipa-g1a-contract-qa` left untouched |
| `git fetch origin main` | PASS |
| Fetched `origin/main` | `6ac764948d3e2e2e5fad11cf46aced5d16d67bb8` |
| GitHub remote `main` | `6ac764948d3e2e2e5fad11cf46aced5d16d67bb8` |
| Target remote branch before bootstrap | absent |
| New task branch | `feature/tipa-g2a-factory-coordinator` from the exact base |
| Task-only bootstrap commit | `db61fa809176ea313104ff224e6ca7e7cc19f760` |
| Preflight | PASS on the clean post-bootstrap worktree |

The preflight evidence recorded a clean tree, the required branch, baseline
match and no remote task branch. No #133 branch state was reset, stashed,
rebased, overwritten, force-pushed or deleted.

## 3. Deliverables

| File | Purpose |
|---|---|
| `src/virtual_factory/factory/run_context.py` | Frozen header, lifecycle, generation reset, pinned microsecond clock and A/B/C shifts |
| `src/virtual_factory/factory/module_contract.py` | `SimTick`, ports, manifests, capabilities, proposals and module protocol |
| `src/virtual_factory/factory/event_ledger.py` | Append-only committed events, canonical JSON and SHA-256 digest |
| `src/virtual_factory/factory/scheduler_adapter.py` | Serial coordinator, causal commit ordering and checkpoint/replay |
| `src/virtual_factory/factory/__init__.py` | Public factory package exports |
| `tests/factory/test_factory_run_context.py` | Lifecycle, immutable header/mode, clock and shifts |
| `tests/factory/test_factory_scheduler.py` | Registration-order determinism, causality, negative scheduler oracles |
| `tests/factory/test_module_isolation.py` | Proposal purity, exception isolation, checkpoint/restore proof |
| `docs/reports/TIPA_VF_G2A_01_REPORT.md` | This report |
| `.ai-harness/tasks/TIPA-VF-G2A-01.json` | Authorized task contract bootstrap |

No file outside the Issue allowlist was modified. The old
`discrete.FutureEventScheduler` was read as a reference only; it was not edited,
monkey-patched or bridged to a floating clock. ASSY, Water Bottle, observation,
config, deploy, simulator and workflow files were untouched.

## 4. Implementation summary

- `FactoryRunContext` pins an aware UTC epoch and exposes nonnegative integer
  microsecond ticks. It enforces `CREATED→VALIDATED→INITIALIZED→READY→RUNNING↔PAUSED→STOPPED`,
  bounded `FAILED`, invalid-transition rejection and generation-incrementing
  reset. The immutable header carries workspace/config digests, seed, model
  revision, UTC epoch, mode and fixed Asia/Ho_Chi_Minh calendar.
- Shift A is 06–14, B 14–22 and C 22–06 local time, including C at midnight and
  the 06:00 A boundary. Production day rolls at 06:00.
- Modules expose typed ports, version/fidelity/capabilities/ownership and the
  required `initialize / next_event_time / propose / apply_committed / snapshot /
  restore` protocol. Missing capabilities fail closed at registration.
- Proposals are deeply frozen. The coordinator gathers them against an immutable
  read snapshot, sorts by `(tick_us, causal_phase, module_id, local_sequence,
  event_id)`, defers same-tick events whose causation is not yet committed, and
  commits serially with a bounded same-tick fixed point.
- Committed events are append-only and scoped by run, generation, module and
  local sequence. Duplicate IDs, reused idempotency keys and malformed events
  fail closed. Canonical JSON uses sorted keys, stable separators, UTF-8 and no
  NaN, with SHA-256 ledger and trace digests.
- Checkpoints capture run state/generation/tick, pending-event boundary, ledger
  cursor/events/digest and module snapshots. Restore rejects wrong run,
  generation, revision, module set or digest, and replays the canonical trace.
  This is an in-memory P0 replay boundary, not durable crash recovery.

## 5. Test evidence

### 5.1 Focused `done_when`

```text
.venv/bin/python -m pytest -q tests/factory/
19 passed in 0.16s
```

### 5.2 Full regression

The Issue requires `.venv/bin/python -m pytest -q`. The execution limit for this
run forbids a single command from exceeding ten minutes, and the full suite
exceeds that limit on this host (`tests/test_dday_b4_bottled_water_factory.py`
alone takes about 444 s). The suite was therefore run as bounded partitions
covering all 1901 collected tests:

```text
# contracts, factory, [a-c], DDAY B2/B3, demand, demo, discrete, engine, event, [f-v]
1754 passed in 53.40s

# DDAY B5 through UI deploy
117 passed in 366.37s

# DDAY B4 bottled-water factory
30 passed in 444.37s
```

The DDAY partitions used `GH_TOKEN=definitely-invalid` to match CI visibility.
Without that neutralisation, the pre-existing live-probe test
`test_c01_06_plantos_compatibility_records_exact_gap` observes the locally
authenticated `hieudovn/PlantOS` repository and fails for environment reasons;
the same test passes with the neutralised token. This is not a G2A-01 code
change and no forbidden compatibility claim is made.

### 5.3 Negative oracles covered

- Invalid lifecycle transitions, negative/bool ticks, backwards clock, naive or
  non-UTC epochs.
- Shift C at midnight, C immediately before 06:00 and A at 06:00.
- Shuffled module registration yields identical event order and ledger digest.
- Causal receipt is committed before dependent same-tick start despite phase
  priority; past events are rejected.
- Duplicate event IDs, conflicting idempotency keys, unsupported capabilities,
  zero-progress and bounded zero-tick cycles fail closed.
- Proposal purity against frozen snapshots; controlled proposal exceptions
  leave no committed event; pause/checkpoint/restore preserves cursor, order and
  replay digest; wrong generation/revision checkpoints are rejected.

## 6. Acceptance matrix

| ID | Result | Evidence |
|---|---|---|
| P01 Focused tests pass | **PASS** | 19 passed, exit 0 |
| P02 Zero test failures | **PASS** | 1901 tests covered in bounded partitions, 0 failures |
| P03 Exact-head CI succeeds | **NOT RUN** | Draft PR opened and left for operator/CI per run limit |
| F01 Report committed | **PASS** | This file |
| F02 Task contract committed | **PASS** | Bootstrap commit `db61fa8` |
| F03 No forbidden action | **PASS** | Allowlist-only changes; no merge/deploy/next Issue |
| F04 All canonical steps executed | **NOT RUN** | P01–P24 gate requires remote exact-head CI |
| F05 All required steps pass | **NOT RUN** | Depends on F04 |
| F06 Remote commit exists | **PENDING AT REPORT COMMIT** | Confirmed in final PM report after push |

## 7. Deferred oracles and non-objectives

- T01/T02 remain **specification-level oracles**. No ASSY AP04 material join,
  starvation, six-sublime common-clock or G3-A integration result is claimed.
- The generic two-module scheduler test is real executable evidence, not an ASSY
  integration proof.
- No `MaterialFlowLedger`, inventory, BOM, reservation, genealogy or material
  transaction is implemented.
- No parallel worker pool, broker, UI, MES/QMS/PlantOS write, production data,
  deployment, durable crash recovery or material-atomic snapshot is claimed.
- Material/quality/transfer semantics remain deferred to #128; G1B/C consumer
  mappings remain separate.

## 8. Blockers and unknown evidence

- Exact-head VF-DM CI and the P01–P24 harness gate are **UNKNOWN/NOT RUN** at
  this commit because the run limit directs a draft PR and no CI wait.
- The exact single full-suite command was not run to completion because it
  exceeded the ten-minute per-command cap; all collected tests were instead run
  in bounded partitions as recorded above.
- No remote SHA equality, CI conclusion, SA review, merge authorization or
  next-task authorization is claimed here.
