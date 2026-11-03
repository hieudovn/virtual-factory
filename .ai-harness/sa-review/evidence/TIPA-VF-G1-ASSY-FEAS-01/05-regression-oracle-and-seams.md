# 05 — Regression oracle and seam classification

## A. Regression oracle (deterministic, fail-closed)

| ID | Scenario | Exact expected oracle | Current runtime result | Verdict |
|---|---|---|---|---|
| OR-01 | Zero external input in integrated mode | `SO2/RSO2 external supplied = 0` → `SSO2_PRODUCED = 0`, `RSO2_PRODUCED = 0`, AP04 emits deterministic `WAITING_FOR_MATERIAL`, `motor_count` unchanged, no exception escapes `step_all` | `initialize` seeds 7 + 7; `step_context` can produce RSO2 on demand; with no RSO2 the runtime raises `AssyLineError` instead of a wait state (probe 06) | **FAIL — not supported** |
| OR-02 | Two sub-lines compete for one Rotor | Exactly one reservation/consumption wins; loser remains `WAITING_FOR_MATERIAL`; exactly one Motor child; one genealogy pair; no double consumption | No shared Rotor ledger; each context has its own `_rso2_wips` dict with its own `RSO2-0001`; no reservation/tie-break (probe 06) | **NO MECHANISM** |
| OR-03 | External WIP arrives late | Accepted under original external ID, no local ID rewrite, AP04 waits then joins when receipt is effective; no phantom WIP before arrival | No injection API; external WIP not registered → `Unknown WIP: EXT-SSO2-0001`; `produce_*` has no external-ID argument (probe 06) | **NO SUPPORT** |
| OR-04 | Replay/reset | Same seed/config → identical trace fingerprint; reset creates new generation `R<n+1>`; no key reuse; duplicate poll adds zero keys | Probe: fingerprint equal, `R1 → R2`, 384 → 384 keys. Existing reset/idempotency tests pass | **PASS** |
| OR-05 | AP06 FAIL → PASS retains both attempts | Attempt 1 `FAIL` and attempt 2 `PASS` both present with distinct record IDs/keys; attempt 1 not rewritten or terminal | Existing test `test_fail_measurement_preserved_after_retest` and finality tests pass; C4 has 57 quality results and 96 measurement results | **PASS** |

### Test commands executed

```text
PYTHONPATH=src python -m pytest -q \
  tests/test_sim_val_01_feed.py tests/test_demo_composition.py \
  tests/test_assy_mes_bridge_v1.py tests/test_assy_mes_03_evidence.py \
  tests/test_vf_contract_finality_01.py
# 109 passed, 1 warning

PYTHONPATH=src python -m pytest -q \
  tests/test_dday_b2_bottled_water_line.py tests/test_assy_line.py \
  tests/test_demo_assy_mes_v1.py tests/test_m6_int_01.py
# 110 passed, 1 warning
```

Legacy ASSY single-line and Bottled Water tests passed; no legacy test was
modified or deleted.

## B. Seam classification

| Seam | Classification | Why |
|---|---|---|
| S1 — suppress all local SSO2/RSO2 seed and replenish | `SAFE_ADDITIVE` | Add an immutable run mode and gate the four paths; legacy default remains STANDALONE |
| S2 — register external SSO2 at PRE-ASSY with original ID | `NEEDS_LOCAL_EXTENSION` | `introduce_to_assy` already preserves the ID, but only registered WIPs are accepted; need additive registration/port API |
| S3 — register external RSO2 for AP04 with original ID and eligibility | `NEEDS_LOCAL_EXTENSION` | `_rso2_wips` is private; `produce_rso2_wip()` takes no ID; AP04 pops first key |
| S4 — exact factory-clock / event-boundary advance | `BLOCKED_REDESIGN` (for same-time six-line coordination) | No `advance_to`, `next_event_time`, propose/commit or global scheduler wiring; per-line independent float time |
| S5 — reservation / all-or-nothing AP04 join | `NEEDS_LOCAL_EXTENSION` | No reservation ledger, no version/eligibility check, no rollback; requires bounded adapter + material ledger from G2 |
| S6 — snapshot/reset/run_id/C4 projection | `SAFE_ADDITIVE` | Existing reset/generation/C4 are proven stable; factory ID and external provenance must be additive |
| S7 — external WIP arriving late / waiting state | `NEEDS_LOCAL_EXTENSION` | No wait state; missing Rotor raises; need explicit `WAITING_FOR_MATERIAL` result |
| S8 — buffer capacity / FIFO / qualification | `BLOCKED_REDESIGN` for whole-factory claim | Current lists/dicts are unbounded and unqualified; must come from the G2 material ledger, not patched into ASSY as ad-hoc counters |

**Overall:** `NEEDS_LOCAL_EXTENSION` for a bounded G3-A adapter; **no authorization
to rewrite the ASSY core**. The whole-factory clock/reservation claim remains
blocked on the G1A/G2 design lock and shared coordinator/ledger, not on ASSY
alone.

## C. Smallest proposed G3-A allowlist (for a later SA-authorized issue only)

| File | Change |
|---|---|
| `src/virtual_factory/assembly/integrated_input.py` (new) | External input port, immutable `STANDALONE`/`INTEGRATED` mode, exact-ID registration, reservation request/result, `WAITING_FOR_MATERIAL` result |
| `src/virtual_factory/assembly/line_runtime.py` | Additive: register external SSO2/RSO2; AP04 reservation hook; no default behaviour change; no rewrite of join/quality/genealogy |
| `src/virtual_factory/assembly/demo_composition.py` | Additive: gate all four local seed/replenish paths in INTEGRATED mode; keep STANDALONE defaults byte-identical |
| `src/virtual_factory/assembly/assy_mes_bridge.py` | Additive: factory-run correlation metadata only; preserve C4 `run_id`, message_key and v1.1 wire contract |
| `tests/test_tipa_g3a_external_input.py` (new) | OR-01…OR-05 plus deterministic clock/reservation negatives |

Forbidden in G3-A: changing AP04 join math, quality/attempt semantics,
genealogy shape, C4 message types/keys, `discrete/`, legacy ASSY defaults, or
Bottled Water.

## D. G3-A stop criteria (proposal)

1. No exact event-boundary API exists and SA has not accepted a documented
   safe adapter boundary → STOP.
2. Any OR-01…OR-03 negative oracle still produces local WIP, double
   consumption, phantom child or an uncaught exception → STOP.
3. Legacy ASSY standalone or Bottled Water regression fails → STOP.
4. Implementer needs to change C4 or production quality/genealogy semantics →
   STOP and return to SA.
5. Scope requires changing files outside the table above → STOP.
