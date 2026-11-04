# TIPA-VF-G2A-02 — Material Ledger report

**Issue:** [#128](https://github.com/hieudovn/virtual-factory/issues/128)

**Task contract:** `.ai-harness/tasks/TIPA-VF-G2A-02.json`

**Requested gate:** `ready_for_sa_review`

**Branch:** `feature/tipa-g2a-material-ledger`

**Expected base:** `fe6d007bb4b744999245ee47e5d7de6c5551f015`

**Mode:** supervised single-Issue implementation; no merge, deploy or next Issue.

## 1. Status

```text
IMPLEMENTED — LOCAL REGRESSION PASS — PR/CI/GATE PENDING
```

This report is committed at the implementation head. It does not claim
exact-head CI success, P01–P24 gate success, SA approval, merge or production
readiness. The PR is opened non-draft only after the local implementation is
ready for SA review; CI is not awaited as a blocking step in this run.

### SA review remediation on PR #150

The SA review at `5e72d3fe41d3a726d32d1958be5a72537098b0a0` required two fixes,
both inside the existing allowlist:

1. **Torn-tail restart safety.** Journal recovery now identifies a partial
   final frame, truncates it to the last complete frame, flushes and fsyncs the
   file and directory before any append. A valid record is therefore never
   appended behind an old partial frame. The regression test runs
   `tx1 -> torn tx2 -> reopen -> retry tx2 -> reopen again` and verifies version
   2, exactly one stock item per material, two outbox rows, and the stored
   receipt. A complete checksum-corrupt frame still fails closed.
2. **Single-writer safety.** `MaterialFlowLedger` acquires a nonblocking
   exclusive `flock` on `material.journal.lock` before reading or appending and
   holds it for the ledger lifetime. A second in-process or cross-process
   writer fails with `JournalWriterLockError`; it cannot validate stale version
   state and append a competing version-1 frame. `close()` releases the lock.

## 2. Baseline and bootstrap

| Step | Result |
|---|---|
| Remote repository | `hieudovn/virtual-factory` |
| Existing #127 checkout | `feature/tipa-g2a-factory-coordinator` left intact |
| `git fetch origin main` | PASS |
| Fetched `origin/main` | `fe6d007bb4b744999245ee47e5d7de6c5551f015` |
| GitHub remote `main` | `fe6d007bb4b744999245ee47e5d7de6c5551f015` |
| Target remote branch before bootstrap | absent |
| New task branch | `feature/tipa-g2a-material-ledger` from the exact base |
| Task-only bootstrap commit | `9f3feb7` |
| Preflight | PASS on the clean post-bootstrap worktree |

No existing #127 branch state was reset, stashed, rebased, overwritten,
force-pushed or deleted. No source coordinator file was edited.

## 3. Deliverables

| File | Purpose |
|---|---|
| `src/virtual_factory/factory/material/__init__.py` | Public material package exports |
| `src/virtual_factory/factory/material/models.py` | Identities, canonical Decimal/UOM policy, items, reservations, transfers, recipes, buffers, receipts and the published transaction schema |
| `src/virtual_factory/factory/material/accounting.py` | Stock, reservation availability, buffer capacity and recipe conservation checks |
| `src/virtual_factory/factory/material/journal.py` | Length-framed SHA-256 journal, fsync, safe torn-tail truncation, exclusive writer lock and corrupt-record fail-closed handling |
| `src/virtual_factory/factory/material/transfer.py` | Transfer state machine and declared simulated latency policy |
| `src/virtual_factory/factory/material/ledger.py` | Atomic `apply_transaction` entry point, versioning, idempotency, replay, genealogy and ledger-owned outbox |
| `tests/factory/test_material_ledger.py` | Unit/lot accounting, Decimal, capacity, quality, versioning and idempotency |
| `tests/factory/test_material_transfer.py` | Staged transfer, latency, port/capacity, duplicate, return and loss |
| `tests/factory/test_material_join.py` | Two-parent join, genealogy, no-partial transform, recipe conservation and contention |
| `tests/factory/test_material_recovery.py` | Reopen, crash injection, torn tail, corrupt committed record and replay |
| `docs/reports/TIPA_VF_G2A_02_REPORT.md` | This report |
| `.ai-harness/tasks/TIPA-VF-G2A-02.json` | Authorized task contract bootstrap |

Only allowlisted paths were changed.

## 4. Implementation summary

- `MaterialFlowLedger` requires an explicit `generation >= 1`; generation zero
  is rejected. The run id, generation, definition digest, config digest, model
  revision and seed are pinned in the journal header and checked before replay.
- Quantities are canonical decimal strings parsed as `Decimal`, never float.
  EA and BATCH are integral. KG, L and M use pinned fractional precision.
  NaN, exponent, sign, leading zero and noncanonical precision are rejected.
- Material identity is `(factory_run_id, generation, material_id)` with separate
  location, quality, lifecycle, reservation, scope and provenance dimensions.
  Duplicate identifiers, negative stock and unowned creation fail closed.
- `apply_transaction(tx, expected_version)` validates the published
  `vf-material-transaction-v0.1` schema and semantic constraints before state
  change. A stale expected version raises a structured version conflict.
  Duplicate idempotency key plus identical canonical payload returns the
  original receipt without a new event, outbox row, genealogy edge or version.
  Reused keys or transaction ids with different payloads are hard conflicts.
- Reservations are versioned and all-or-none. Same-tick competing clients are
  ordered by a stable transaction key; the loser receives
  `WAITING_FOR_MATERIAL` without stock mutation. HOLD/UNKNOWN/REJECTED stock is
  owned but not eligible for reserve, consume or transform.
- Buffers support explicit unlimited capacity and finite zero/nonzero capacity.
  Capacity is checked at PRODUCE, transform child creation and RECEIVE.
- Transfers use `IN_TRANSIT` ownership with a declared nonnegative latency,
  destination capacity checks and exactly-once receive. Duplicate, early,
  wrong-port, missing-ship, return and loss paths cannot create phantom stock.
- TRANSFORM consumes all qualified parents, creates the child, writes both
  parent genealogy edges and a ledger-owned outbox row in one journal commit.
  The synthetic motor recipe declares its own input/output conversion; a naive
  `1 stator + 1 rotor = 2 motors` request is rejected by recipe validation.
- The journal uses append-only 8-byte length framing plus SHA-256, flushes and
  fsyncs before exposing a receipt, and fsyncs the directory when created.
  Replay validates the receipt and full state digest. A torn final frame is
  truncated to the last complete frame and fsynced before any later append; a
  checksum failure in a complete committed frame fails closed.
- One nonblocking exclusive `flock` writer lock is held for the ledger lifetime.
  A second in-process or cross-process writer fails before reading or appending,
  so it cannot append a competing frame from stale expected-version state.
- A subprocess crash hook (`VF_MATERIAL_CRASH_STAGE` / `VF_MATERIAL_CRASH_TYPE`)
  is present only for deterministic tests. It is not a production control.

## 5. Test evidence

### 5.1 Focused `done_when`

```text
.venv/bin/python -m pytest -q tests/factory/test_material_ledger.py \
  tests/factory/test_material_transfer.py tests/factory/test_material_join.py \
  tests/factory/test_material_recovery.py
35 passed in 2.13s
```

### 5.2 Factory partition

```text
.venv/bin/python -m pytest -q tests/factory/
68 passed in 2.26s
```

### 5.3 Full regression in bounded partitions

Each command stayed below the 8-minute per-command limit. `GH_TOKEN` was
neutralised to `definitely-invalid` to match CI visibility for the pre-existing
live-probe test.

```text
# contracts, factory and all non-DDAY-B4/B5/B6/B7/FR1/UAT/UI-deploy tests
1803 passed in 50.56s

# DDAY B5 through UI deploy
117 passed in 350.88s (0:05:50)

# DDAY B4 bottled-water factory
30 passed in 415.50s (0:06:55)
```

Total local regression coverage: **1950 passed, 0 failed**.

### 5.4 Recovery and crash evidence

- Process termination before journal append leaves no transaction, stock,
  outbox or genealogy state; the same request safely retries.
- Process termination after journal fsync but before acknowledgement replays
  the committed state and returns the original receipt by idempotency key,
  without duplicating stock, outbox or genealogy.
- Transfer and transform crash points after durable commit recover to the same
  sender/destination, child, two-edge genealogy and single outbox state; replay
  does not create a second child or edge.
- Truncating the final journal frame discards that uncommitted intent without
  phantom stock; recovery truncates and fsyncs the torn tail, retrying commits
  it once, and a second restart still reads version 2 with exactly one stock
  item, outbox row and receipt per retried transaction.
- Flipping a byte in a complete committed record raises `CorruptJournalError`
  instead of silently skipping the record.
- Reopening after reservations and after a join reproduces the same state digest.
- A second in-process ledger and a second cross-process ledger both fail with
  `JournalWriterLockError` while the first writer holds the journal; the first
  writer can still commit one version-1 frame and restart cleanly.

## 6. Negative oracles covered

- Noncanonical Decimal, exponent, sign, NaN, leading zero, EA fraction,
  KG/L/M precision, zero/negative material legs.
- Duplicate material creation, duplicate transaction id, duplicate idempotency
  key with different bytes, stale expected version and mismatched transaction
  expected version.
- Buffer overflow, zero-capacity buffers, incompatible buffer unit and
  destination capacity rejection without partial mutation.
- HOLD quality reservation/consumption, missing parent, quality-blocked parent,
  transform capacity failure and recipe conversion violation.
- Wrong sender, missing ship, early receive, wrong destination, duplicate
  receive, return then receive and loss then receive.
- Two same-tick competing reservations with reversed input order; one stable
  winner and one `WAITING_FOR_MATERIAL` loser.
- Torn tail followed by a retry and a second restart; complete corrupt frame
  fail-closed; duplicate in-process and cross-process writers fail closed.

## 7. Acceptance matrix

| ID | Result | Evidence |
|---|---|---|
| P01 Focused material tests pass | **PASS** | 35 passed, exit 0 |
| P02 Zero required test failures | **PASS** | 1950 passed, 0 failed in bounded exhaustive partitions |
| P03 Exact-head CI succeeds | **UNKNOWN** | CI not awaited as a blocking step in this run |
| F01 Material report committed | **PASS** | This file in the implementation commit |
| F02 Task contract committed | **PASS** | Bootstrap commit `9f3feb7` plus implementation commit |
| F03 No forbidden action | **PASS** | Allowlist-only changes; no merge, deploy, OS install or next Issue |
| F04 All canonical gate steps executed | **UNKNOWN** | P01–P24 gate not run; it invokes the full suite and needs PR/CI |
| F05 All required gate steps pass | **UNKNOWN** | Depends on F04 |
| F06 Remote commit exists | **PENDING AT REPORT COMMIT** | Confirmed after push in the PM final report |

## 8. Durability and scope limits

- The journal is a local file-backed reference. It relies on local `fsync` and
  directory `fsync`; it does not prove power-loss safety on every OS, file
  system or storage device.
- The writer lock is a local POSIX `flock`. It excludes other processes on the
  same host/file system; it is not a distributed or network-filesystem lease.
- No external database, broker, MES, QMS, PlantOS, UI, live input or production
  persistence path is used.
- The ledger is standalone. It does not change or claim atomicity for the G2A-01
  coordinator, the existing event ledger or a whole simulation tick.
- Cross-ledger transfer atomicity is not implemented. Transfer state and material
  accounting are journal-committed inside this ledger only.
- Splitting a transferred quantity creates a derived in-transit material id; this
  is an internal reference policy and not an external identity contract.
- No real T01/T02 runtime oracle, real line capacity, physical calibration or
  ASSY integration is claimed. The stator/rotor/motor fixture is synthetic.

## 9. Blockers and unknown evidence

- Exact-head VF-DM CI has not been awaited as a blocking step; its result is
  **UNKNOWN** at report commit.
- The P01–P24 gate result is recorded separately in the final PR evidence
  comment; it requires remote PR/CI evidence.
- The PR is marked non-draft only after the local implementation and bounded
  regression are ready for SA review.
- No SA review, merge authorization, deployment or next Issue authorization is
  claimed.
