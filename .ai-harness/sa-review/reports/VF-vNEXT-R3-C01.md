# VF-vNEXT-R3-C01 — Authoritative canonical reset generation (projection epoch)

Gate type: **CORRECTION** (SA review finding on Issue #81 comment `5643455951`).
Issue: https://github.com/hieudovn/virtual-factory/issues/81

- Repository: `hieudovn/virtual-factory`
- Branch: `feature/vf-vnext-r3-c01`
- Previous head (SA-reviewed R3 head): `311109c3c6a8f3b6550dfef8659348e0bd70e28e`
- New head: `(this implementation commit)`
- Expected base sha (origin/main): `f5261c8ca18cd4e01779c0274b55270ba028b4e5` · contract: `.ai-harness/tasks/VF-vNEXT-R3-C01.json`
- Harness preflight: **PASSED**

## 1. Finding addressed

The SA found that `CanonicalAssyOutput` derived the projection epoch by comparing
poll snapshots (time/step/per-line time regression). A reset that is not observed
between the reset and a deterministic re-step back to the same state S therefore
advanced no epoch, allowing byte-identical post-reset facts to collide with
pre-reset idempotency keys/checkpoints. Output correctness must not depend on
polling timing.

## 2. Fix (narrow, additive)

**One reset authority, exposed as lifecycle metadata — no G22 change, no second
authority, no redesign.**

- `src/virtual_factory/runcontrol/session.py`: `RuntimeSession` now owns a
  monotonic `reset_generation` (alias `reset_epoch`).
  - `reset()` increments it **only after** `RunLifecycleService.reset(run_id)`
    returns successfully (a failed reset never advances it) — the same `run_id`
    and all existing reset semantics are preserved.
  - `new_attempt()` / `replay()` restart it at **1** for their fresh canonical run.
  - It is read-only lifecycle metadata; it is not a run/lifecycle identity.
- `src/virtual_factory/ui/assy_output.py`:
  - the projection epoch is **read from** `session.reset_generation`
    (`epoch_source = canonical_session_reset_generation`); the previous
    poll-to-poll inference (`_advance_epoch_if_reset`) is **deleted**;
  - a session without the seam fails closed (`CanonicalOutputError`) instead of
    falling back to inference;
  - ordering fixed: the canonical binding is (re)computed **after** the epoch is
    resolved — `_bind()` = federation → epoch sync → bridges, and the fresh-run
    branch re-derives the epoch and **recomputes the binding** before creating the
    new bridges, so no stale prior-run epoch metadata can be bound into a
    new-attempt/replay bridge;
  - output stays downstream/read-only: it only observes lifecycle metadata and
    still never steps/resets the session (mutation guard unchanged).
- `tests/test_vnext_r3_c01_reset_generation.py` (**NEW**, 15 tests);
  `tests/test_vnext_r3_canonical_observation_mes.py`: the one epoch-sensitive
  assertion was migrated to be epoch-relative (R3-C01 makes the epoch
  authoritative, so a literal `E1:` can no longer be asserted).
- `.ai-harness/sa-review/evidence/VF-vNEXT-R3/**` regenerated under the corrected
  epoch semantics (identical PASS properties; epoch labels now come from the
  canonical generation) + new `evidence/VF-vNEXT-R3-C01/**` (01..05) + report +
  CURRENT + manifest gate context and the new `r3c01_reset_generation` baseline group.

## 3. Focused C01 results (evidence `VF-vNEXT-R3-C01/01..05`, all PASS)

| Evidence | Result |
|---|---|
| `01-reset-generation-seam.json` | generation 1 → 2 → 3 monotonic on successful resets; **failed reset does not advance** it (3 → 3); `run_id` unchanged; `new_attempt` → 1 and `replay` → 1; adapter has **no** epoch-inference method; `epoch_source = canonical_session_reset_generation`; read-only polls do not change the generation |
| `02-poll-timing-independence.json` | the required sequence — poll at S (t = 480 s) → reset → **no poll** → re-step to the byte-identical state S (`state_after_restep_identical = true`) → poll: epoch 2 → 3 (`session_reset_generation = 3`), **60 new facts emitted**, `delivered_this_poll == new keys`, all new keys in the new epoch, **no collision** with pre-reset keys; repeated poll → 0 delivered (obs and MES) |
| `03-fresh-run-epoch-one.json` | with a prior epoch of 3: `new_attempt` → `TIPA-0002`, envelope epoch **1**, `session_reset_generation` 1, `epoch_changes` 0, keys and payload metadata `E1:` only (no stale epoch), bridge binding epoch 1; `replay` → `TIPA-0003` likewise epoch 1 |
| `04-no-second-authority-read-only.json` | in-context reset does **not** rebuild the federation (1 → 1); a fresh attempt adds exactly its own run federation (→ 2, one per run authority); exactly **1 RuntimeSession**; **0** legacy controllers; three full polls leave domain state and the reset generation unchanged; the injected-mutation guard still raises `OutputMutationError` |
| `05-regression.json` | machine-derived pytest runs (all exit 0): C01 focused 15, R3 focused 27, R1 40, R2 27, G22 session/replay 15, observation/MES contracts 77, **full suite 2598 passed** |

## 4. Regression and baseline

- Full suite: **2598 passed** (`python -m pytest -q -p no:cacheprovider tests`;
  R3 head was 2583 → +15 C01 tests, no regression).
- Canonical baseline (now 41 groups incl. `r3c01_reset_generation`, plus
  `checks_compile` / `checks_static_lint_type` / `checks_changed_files` /
  `checks_preflight`): **recorded at the pushed head in the SA submission**.

## 5. Boundaries

No R4, no R5, no SH-WTP expansion, no gateway/protocol work, no change to G22 run
identity semantics (reset keeps `run_id`; fresh attempts/replays keep their own
run ids), no second lifecycle authority, no architecture redesign, no rebase onto
`main`, no merge. `AssyLineRuntime`, R1 production driver/profile, G4 coordinator,
`federation/`, the two output bridges and all domain facts are untouched.

Authority unchanged: `vf_runtime_authorization = NOT_AUTHORIZED`;
`site_authorized_execution = NOT_AUTHORIZED`;
`whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`.

## 6. Verdict

`VF-vNEXT-R3-C01 — READY FOR SA REVIEW`.
