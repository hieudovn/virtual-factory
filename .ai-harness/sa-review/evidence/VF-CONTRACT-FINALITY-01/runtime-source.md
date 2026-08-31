# VF-CONTRACT-FINALITY-01 — runtime-source.md

## Authoritative source of truth for FAILED_FINAL

| Item | Value |
|---|---|
| Source class | `AssyLineRuntime` (`src/virtual_factory/assembly/line_runtime.py`) |
| Method | `_execute_quality_disposition(...)` |
| Status model | `QualityStatus.FAILED_FINAL = "failed_final"` (`src/virtual_factory/assembly/quality_records.py`) |
| WIP identity | per-WIP `QualityHistory.current_status` (WIP-scoped, not line/station-global) |
| Transition trigger | `if disposition in ("FAIL","NG") and attempt >= qcfg.max_attempts:` → `history.set_status(QualityStatus.FAILED_FINAL)` |
| Explicit runtime event | YES — `LineEvent` `"QUALITY_FAILED_FINAL"` (pos, wip_id, `max_attempts=N exhausted`) |
| Emission | once per WIP terminal transition (idempotent; a later disposition attempt sees `current_status == FAILED_FINAL` and returns early) |
| Timing vs second FAIL record | the `QualityRecord` for the final FAIL attempt is added FIRST, then `FAILED_FINAL` is set, then `QUALITY_FAILED_FINAL` is emitted — one atomic outcome within the same call |

## Exact transition code (line_runtime.py ~1200-1240)

```python
record = QualityRecord(
    record_id=self._next_quality_id(),
    wip_id=wip_id,
    station_id=pos,
    ...
    attempt_number=attempt,
    simulation_time_s=self._simulation_time_s + self._station_elapsed.get(pos, 0.0),
    ...
)
history.add_record(record)
...
if disposition in ("FAIL", "NG"):
    history.set_status(RETEST_PENDING if check_type == TEST else REINSPECT_PENDING)
    op.routing_action = "STAY_AT_STATION"
    ...
    if attempt >= qcfg.max_attempts:
        history.set_status(QualityStatus.FAILED_FINAL)
        events.append(self._make_event(
            "QUALITY_FAILED_FINAL", pos, wip_id,
            f"max_attempts={qcfg.max_attempts} exhausted"))
```

## FAILED_FINAL scenario configuration (demo_composition.py)

```python
DemoScenario.FAILED_FINAL: {
    "ap06": {"scenario": "ALWAYS_FAIL", "overrides": {}},
    "ap08": {"scenario": "PASS", "overrides": {}},
}
# + max_attempts adjusted to 2 for the FAILED_FINAL scenario
# target sub-line: ASSY-SL03
```

## What this gate exposes (additive only)

The authoritative terminal decision already made by the runtime
(`attempt >= max_attempts` → FAILED_FINAL) is stamped on the final
`QualityRecord` and carried into the outbound `mes.quality_result` observation.
No transition logic is altered.

## Rejected alternative

Reconstructing finality in the bridge by counting attempts (e.g. "attempt == 2
⇒ terminal") is NOT used — the runtime already carries the authoritative
terminal transition, so finality is read from runtime truth, never guessed.
