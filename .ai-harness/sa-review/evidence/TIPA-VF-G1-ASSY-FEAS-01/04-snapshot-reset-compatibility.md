# 04 — Snapshot, reset, run identity and C4 compatibility

## Snapshot

`AssyDemoComposition.snapshot()` builds a detached `AssyDemoSnapshot` from the
selected runtime (`demo_composition.py:360-375`); `build_snapshot` reads public
runtime state only (`src/virtual_factory/assembly/demo_snapshot.py`). The MES
bridge is also read-only over runtime facts: `AssyMesBridge.poll` collects facts
and never mutates runtime (`src/virtual_factory/assembly/assy_mes_bridge.py:337-358`,
`:506-590`). Adding an adapter-side projection or extra fields is therefore
additive and does not require changing the snapshot contract.

## Reset

- `AssyLineRuntime.reset()` clears WIPs, RSO2 buffer, trace, quality history,
  counters, timing and simulation time (`line_runtime.py:1824-1846`).
- `AssyDemoComposition.reset()` calls `initialize()` again, so all six contexts
  are rebuilt and the 7 + 7 seed is recreated (`demo_composition.py:377-379`).
- The bridge detects reset by simulation-time regression and increments the
  sub-line generation; `run_id` becomes `ASSY-SLxx:R<n>`
  (`assy_mes_bridge.py:281-291`, `:376-387`).
- Duplicate polls do not reuse or add message keys
  (`assy_mes_bridge.py:1126-1160`; regression
  `tests/test_assy_mes_bridge_v1.py:358-390`).

Probe 06 (read-only in-memory):

```text
run ids after first 6 steps:  ASSY-SL01:R1 ... ASSY-SL06:R1
run ids after reset + 6 steps: ... ASSY-SL01:R2 ... ASSY-SL06:R2
trace fingerprint equal after reset: true
keys before duplicate poll: 384
keys after duplicate poll:  384
```

The first-run keys remain in the in-memory gateway list; the new generation uses
new keys (`:R2`). That is expected and matches the reset contract.

## C4 projection stability

The C4 wire contract remains `tipa-assy-demo-v1.1`
(`assy_mes_bridge.py:81`). The six-sub-line smoke produced exactly 9 message
types:

```text
mes.run_status              9
mes.execution_event        399
mes.checklist_result        49
mes.genealogy_relationship  43
mes.issue                    2
mes.quality_result          57
mes.measurement_result      96
mes.release                  5
mes.oee_summary              6
total                      666
unique message keys        666
duplicate message keys       0
sub-lines                    6
```

Contract/identity fields on every message are asserted by
`tests/test_assy_mes_bridge_v1.py:337-356` (message_key == idempotency_key,
`contract_version=tipa-assy-demo-v1.1`, run_id pattern, subline_id,
occurred_at, simulation_time_s).

## Can a provisional adapter be added without changing the existing contract?

| Question | Answer |
|---|---|
| Add a new adapter module without editing existing runtime defaults? | Yes — `SAFE_ADDITIVE` |
| Keep legacy standalone C4 bytes/message types stable? | Yes, provided the adapter does not change `CONTRACT_VERSION`, `key` construction or projection fields |
| Reuse existing `run_id` as `factory_run_id`? | No — C4 `run_id` is `ASSY-SLxx:R<n>` and is sub-line scoped; a factory-scoped ID must be carried additively (e.g. extra adapter/ledger metadata), not by rewriting C4 identity |
| Reset without reusing idempotency keys? | Yes, generation bump is already proven |
| Add external input while preserving original parent IDs? | Not yet — requires the bounded registration/reservation extension in `03` |

## Decision

Snapshot/reset/run-generation/C4 compatibility is **SAFE_ADDITIVE** for a new
adapter. The factory-scoped run identity and external material reservation are
**NEEDS_LOCAL_EXTENSION**; neither justifies rewriting the existing runtime or
the C4 contract.
