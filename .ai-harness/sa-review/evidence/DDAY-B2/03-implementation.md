# DDAY-B2 — 03. Implementation diff, file-by-file rationale

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `git.diffstat_vs_b1`,
`git.name_status_vs_b1`; full patch [`implementation.patch`](./implementation.patch);
B2 implementation only [`implementation-only.patch`](./implementation-only.patch).

```
 .ai-harness/tasks/DDAY-B2.json                  | 212 ++++++++++
 configs/workspaces/bottled-water-dday/line.yaml |  79 ++++
 src/virtual_factory/assembly/demo_controller.py | 102 ++++-
 src/virtual_factory/assembly/line_runtime.py    | 454 +++++++++++++++++++-
 tests/test_dday_b2_bottled_water_line.py        | 526 ++++++++++++++++++++++++
 5 files changed, 1356 insertions(+), 17 deletions(-)
```

## 1. `configs/workspaces/bottled-water-dday/line.yaml` (new, 79 lines)

The runnable configuration for the frozen route. Declares plant identity
(`BW-DEMO-01`), line identity (`BW-FP`), the eight positions in frozen order,
logical cycle durations, unit metadata (`unit_type: bottle`,
`product_code: WATER-500ML`) and the single consolidated quality checkpoint at
`BW-FP-INS01` (`on_fail: reject`). Contains **no** legacy station semantics.

## 2. `src/virtual_factory/assembly/line_runtime.py` (+454 / −13)

The reused engine. Additions are profile-gated or purely additive.

| Addition | Rationale |
|---|---|
| `LineRunState` enum (`STOPPED`/`RUNNING`/`PAUSED`) | A run state that structurally cannot be a fault: there is no `FAULT` member, so `STOPPED != FAULT` holds by construction |
| `WipLifecycle.REJECTED` | A rejected unit is a distinct lifecycle outcome, not a silent removal |
| `QualityStationSpec` + `AssyLineConfig.quality_stations` | Lets a workspace declare its own quality checkpoint instead of relying on a fixed station table |
| `AssyLineConfig`: `line_profile`, `plant_id/name`, `line_id/label`, `unit_id_prefix/type/product_code`, `is_generic_profile` | Config-driven generic profile. Every field has a default that leaves the legacy profile unchanged |
| `build_line_station_contracts(config)` | Derives one contract per configured position; only positions declaring a quality checkpoint get a quality capability. Replaces the direct `build_default_assy_contracts(...)` call in `__post_init__` (the function itself is untouched and is still what the legacy profile returns) |
| `_quality_spec(pos)` | Configured spec first, legacy station map as fallback → the legacy profile resolves to exactly the same `(key, check_type, quality config, "hold")` as before |
| `produce_unit()` / `introduce_unit()` / `_feed_next_unit()` | Generic single-material line entry; removes the `PRE-ASSY`/`SSO2`/`RSO2` coupling for non-legacy workspaces |
| `_reject_unit()` | Config-gated (`on_fail: reject`) ejection: unit leaves the carrier, reject counted once, station completes so the line keeps running |
| `_count_completed_unit()` | A generic unit exiting the last station completed its route → `good_count`. Guarded by `ws.rejected` / `ws.counted_good`, which is what keeps the count invariant true |
| Counters + `unit_counts()`, `units_on_line()`, `operating_state()`, `line_facts()` | Raw production facts only. No OEE/availability/performance/quality%/energy-per-unit/utilization/health score is computed |
| `start()/pause()/resume()/stop()` + `advance_cycle()` | The run-control surface. `advance_cycle()` is a no-op outside `RUNNING`, which is what makes PAUSE freeze and RESUME continue from the preserved state |
| Empty-carrier handling in `execute_dwell()` | A carrier whose unit was ejected/removed does no work and is completed immediately, so an indexed line can never stall on an empty carrier. Uses only public `ConveyorLine` API |
| `index_line()` → `_count_completed_unit()` | Single, unambiguous exit hook |
| `reset()` clears the new state | RESET returns to a genuinely known initial state |

Behaviour-preserving refactors (the `−` side of the diff, verified by the
legacy regression suite):

```
-            self.station_contracts = build_default_assy_contracts(          → build_line_station_contracts(self.config)
-                dict(self.config.station_durations)
-            )
-            station_key, check_type = _QUALITY_STATION_MAP[pos]              → spec = self._quality_spec(pos)
-                pos, wip_id, op, station_key, check_type, decision=...)      → pos, wip_id, op, spec, decision=...
-            if qstatus == QualityStatus.CLEAR:
-                if pos == "AP11":                                            → if contract.capabilities.final_disposition:
-                    op.operation_result = _QUALITY_OPERATION_RESULT.get(      → .get(pos) or check-type fallback
-                        pos, OperationResult.TEST_COMPLETE)
-        station_key, check_type = _QUALITY_STATION_MAP[pos]                  → spec-based
-        qcfg = self.config.quality.get(station_key)                          → spec.quality
-        station_key: str,                                                   → spec: QualityStationSpec
-        check_type: CheckType,
```

`_apply_quality_decision(..., station_key, check_type, ...)` became
`_apply_quality_decision(..., spec, ...)` — a private signature, so no caller
outside this module is affected.

## 3. `src/virtual_factory/assembly/demo_controller.py` (+102 / −4)

| Change | Rationale |
|---|---|
| `initialize()` peeks the loaded profile | Selects one of two modes from configuration; the legacy branch body is byte-identical to before |
| `_line` / `_generic_profile` fields | Generic single-line state, `None`/`False` for the legacy composition |
| `is_generic_line`, `line`, `run_state` | Introspection for tests, smoke and the (later) B3 skin |
| `start()/pause()/resume()/stop()/advance()` | Thin delegation to the runtime's control surface — the controller remains the single control entry point |
| `line_facts()` | The generic workspace's outward raw-fact surface |
| `step()` / `snapshot()` generic branches | One deterministic cycle; the legacy demo snapshot is not used to publish Bottled Water state |
| `is_running`, `runtime`, `cycle` generic branches | Keep the existing properties meaningful in generic mode |

Only 4 lines were deleted: three reflowed docstrings and the moved
`AssyDemoComposition(...)` construction inside the restructured `initialize()`.

## 4. `tests/test_dday_b2_bottled_water_line.py` (new, 526 lines)

T01–T12 acceptance tests required by Issue #102. See evidence 09.

## 5. `.ai-harness/tasks/DDAY-B2.json` (new, 212 lines)

The task contract authored from Issue #102, as explicitly permitted by that issue.

## No other file was touched

Every other path in the repository is unmodified. The changed-file set above is
the complete change set; the allowlist audit is in evidence 10.
