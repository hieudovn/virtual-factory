# OPS-02 — Runtime OperationExecution Engine (implementation notes)

> Baseline: `e3b4661`
> Gate: RUNTIME ONLY — no UI/frontend changes.
> Design authority: `docs/design/OPS-01_OPERATION_EXECUTION_CONTRACT.md`

## Modules

### `assembly/station_contracts.py`
- `CompletionMode` (`MANUAL` / `AUTO` / `ASSISTED`), `StationCommand` (`DONE` / `CONFIRM` / `CONFIRM_AND_COMPLETE` / `JOIN_COMPLETE` / `RELEASE`), `Capabilities`, `StationContract`.
- `build_default_assy_contracts(durations)` — canonical ASSY mapping (AP03 = checklist gate with `quality_decision: false`; AP04 = identity transformation with `prerequisites: (AP03,)`; AP06/AP08 = quality_decision; AP11 = final_disposition + quality_decision).
- `load_station_contracts_from_yaml(path)` — loads the approved example-YAML structure.

### `assembly/operation_execution.py`
- `OperationState` (10 states), `OperationResult` (6 normalized results incl. `RELEASED`), `OperationExecution`, `OperationRegistry`.
- Legal transition table enforced in `OperationExecution.transition()` — fails closed via `InvalidTransitionError`.
- Only `COMPLETED → ELIGIBLE_TO_INDEX`; `FAILED` / `HELD` / `EXCEPTION_PENDING` are never eligible. Terminal `FAILED` (`terminal=True`, quality `FAILED_FINAL`) has no outgoing transition and is never moved to `HELD`.

## Integration (`assembly/line_runtime.py`)

- `AssyLineRuntime` now owns `station_contracts`, `operation_registry`, `global_run_mode` (default `AUTO`).
- `execute_dwell()` advances an `OperationExecution` per occupied station via `_advance_operation()`. Work-duration completion maps `WORKING → AWAITING_COMPLETION` (execution/checklist) or `AWAITING_DECISION` (quality_decision) from the contract.
- Mode resolution (`_resolve_mode`): `station.mode_override` → `global_run_mode` → `station.default_mode`.
- `submit_operation_command(station_id, wip_id, command, payload?)` is the runtime command surface for OPS-03. Validates active operation, contract, state, and allowed command; fails closed.
- `_run_operation_domain()` reuses the existing domain handlers (`_execute_station` → AP04 join / quality resolution / generic complete) and maps their outcome onto `operation_result` / `quality_result` / state.
- MANUAL blocks waiting operations at `AWAITING_*`; AUTO auto-issues the contract's `required_action`; ASSISTED shares the same path.

## Additive projection (`assembly/demo_snapshot.py`)

- New `active_operations[]` field (list of `ActiveOperationView`) on `AssyDemoSnapshot`.
- `positions[]` schema and meaning are **unchanged**. `active_operations` is additive only.

## Behavior preservation

- With global AUTO + default config, observable happy-path behavior is preserved (verified by the pre-existing ASSY/demo test suites).
- `FAILED_FINAL` is terminal (`FAILED` + `terminal`, quality `FAILED_FINAL`); never `HELD`.
- AP03 produces no `quality_result` (checklist is the gate).
