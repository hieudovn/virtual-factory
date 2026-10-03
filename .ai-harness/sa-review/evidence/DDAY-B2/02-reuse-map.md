# DDAY-B2 — 02. Reuse map

**Question answered:** which existing Virtual Factory capability is reused, what
was read-only, and what genuinely had to change — using the *smallest generic
extension* rule from Issue #102.

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `route`,
`implementation.patch`.

## Reused as-is (no change, no fork)

| Existing capability | Location | How B2 uses it |
|---|---|---|
| Deterministic indexed stop-and-go line engine | `assembly/line_runtime.py` → `AssyLineRuntime.execute_dwell()` / `index_line()` | The Bottled Water line runs on the *same* runtime object; dwell sizing, dwell overrun, station-elapsed accumulation and index synchronisation are unchanged |
| Config-driven line definition | `assembly/line_runtime.py` → `AssyLineConfig` + `load_assy_config_from_yaml()` | Positions, nominal dwell, station cycle durations and seed come from configuration |
| Operation-execution foundation | `assembly/operation_execution.py`, `assembly/station_contracts.py` | Completion modes, capabilities, `OperationExecution` state machine, auto-submission gating |
| Deterministic timing | `assembly/auto_timing.py` + `AssyLineConfig.timing_behavior/random_seed` | `DETERMINISTIC` + seed 42; fixed durations mean the resolver is not even sampled |
| WIP lifecycle + carrier/conveyor mechanics | `assembly/wip.py`, `carrier.py`, `conveyor.py` | Unit identity, lifecycle transitions, carrier placement and index shift |
| Quality-record mechanics | `assembly/quality_records.py` (`QualityRecord`, `QualityHistory`, `resolve_quality_disposition`) | Inspection produces a real quality record from observed measurements, then a disposition |
| Control-plane pattern | `assembly/demo_controller.py` | The controller stays the single control entry point; no parallel controller was created |
| Legacy regression suite | `tests/` | T13 — the frozen behaviour is asserted by the pre-existing tests, unmodified |

## Deliberately NOT reused (and why)

| Candidate | Decision | Reason |
|---|---|---|
| `assembly/tipa.py` legacy hard-coded topology | **Not used** | Explicitly excluded by Issue #102: a fixed 6-station topology is not the config-driven path |
| `assembly/demo_composition.py` (6 sub-line composition) | **Not used for Bottled Water** | It composes exactly six `ASSY-SLxx` contexts fed by `SSO2`/`RSO2` upstream. Reusing it would push legacy domain names and 6-sub-line assumptions into Bottled Water outward state. It was **not modified**, so the legacy path is untouched |
| `assembly/assy_mes_bridge.py` | **Not modified, not used** | Forbidden by Issue #102; carries legacy station assumptions and OEE semantics |
| `assembly/observation_bridge.py` | **Not modified, not used** | Forbidden by Issue #102; its projection is tied to the legacy demo snapshot |
| `assembly/demo_snapshot.py` (legacy demo snapshot) | **Not used to publish Bottled Water state** | Its station-label map and `motors_created/released` semantics are legacy-domain. Bottled Water publishes raw facts through the runtime instead (see evidence 10) |
| `core/`, `telemetry/`, `protocols/`, `scenarios/` | **Untouched** | Forbidden paths; no telemetry or protocol framework was needed for B2 |

## The smallest generic extension that was required

Four concrete blockers were found by reading the runtime, each fixed by the
smallest generic mechanism available — never by a Bottled Water hard-code:

| Blocker in the existing runtime | Smallest generic extension |
|---|---|
| Station contracts were built from a fixed AP station table | `build_line_station_contracts(config)` derives contracts from configuration; the legacy profile delegates to the unchanged `build_default_assy_contracts` |
| Quality checkpoints were resolved through a module-level AP station map | The map becomes a *fallback*: a configured `quality_stations` spec wins, so a workspace declares its own checkpoint |
| The final-disposition branch keyed off the literal station id `AP11` | Keyed off the `final_disposition` **capability**, which is what the branch actually means (identical behaviour for the legacy profile) |
| A failed quality decision could only hold/retry a unit, and units entered the line only at `PRE-ASSY` via `SSO2`/`RSO2` upstream | Config-driven `on_fail: reject` ejection + generic `produce_unit()`/`introduce_unit()` |

No existing behaviour was removed. The deletions in the patch are exactly the
five expressions above plus three reflowed docstrings — listed in evidence 03.
