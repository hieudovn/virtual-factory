# VF-vNEXT-G7 · Evidence 04 — Coordinator/runtime execution bridge (Issue #52 C, 10-11)

`src/virtual_factory/runcontrol/assy_bridge.py`

`AssyExecutionBridge(TipaAssyFederation)` reuses the accepted G5 federation +
G4 Coordinator seams (no `AssyLineRuntime` rewrite, no demo-policy promotion,
no new synchronization rule):

- `natural_next_boundary(scope_ids)` — next legitimate natural boundary =
  current time + nominal dwell (ASSY domain cadence, NOT a universal timestep).
- `advance(target_time_s, scope_ids, window_id)` — builds a fresh G4 Coordinator,
  registers the selected sub-line adapters, runs ONE window to the target, and
  returns a `StepResult(status, target_time_s, participants, committed,
  failure)`. The G4 exact-landing rules fail closed for any non-natural target
  (no fractional dwell/index).
- `reset(scope_ids)` — capability-scoped in-context reset via the existing
  public `AssyLineRuntime.reset()` (same objects, time back to 0; never rebuilds
  run identity); `supports_reset = True`.

Proven by tests (`TestAssyExecutionBridge`):
- natural steps land exactly at 120s / 240s (single sub-line and all six);
- an arbitrary boundary (60s) fails closed with "overshoots" (no fractional
  dwell);
- runtime OBJECT identity is preserved across step + reset (no reconstruction);
- container-target step advances only the six descendants; `TIPA/ASSY` never
  appears in `participants`.

Standalone ASSY/domain semantics are unchanged (bridge only drives the same
public runtime operations; ASSY oracle stays green — evidence 07).
