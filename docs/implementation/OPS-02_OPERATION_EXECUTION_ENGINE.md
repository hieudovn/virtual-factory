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
- MANUAL blocks waiting operations at `AWAITING_*`; AUTO auto-issues the contract's `required_action`; ASSISTED is distinct (see C01 below).

## Additive projection (`assembly/demo_snapshot.py`)

- New `active_operations[]` field (list of `ActiveOperationView`) on `AssyDemoSnapshot`.
- `positions[]` schema and meaning are **unchanged**. `active_operations` is additive only.

## Behavior preservation

- With global AUTO + default config, observable happy-path behavior is preserved (verified by the pre-existing ASSY/demo test suites).
- `FAILED_FINAL` is terminal (`FAILED` + `terminal`, quality `FAILED_FINAL`); never `HELD`.
- AP03 produces no `quality_result` (checklist is the gate).

## OPS-02-C01 — Semantic corrections

- **C01-01 (AP03 checklist gate).** AP03 is a checklist gate, not a quality-decision station. Completing AP03 runs `_execute_ap03_checklist` (emits `STATION_START`/`STATION_COMPLETE`, marks WIP `COMPLETED_STATION`) and produces `operation_result = CONFIRMED` with `quality_result = None`. **No quality record** is fabricated (nothing appears in the `quality_records` projection). `submit_operation_command` rejects `CONFIRM_AND_COMPLETE` at AP03 when `payload['checklist']` is missing or empty (no bypass).
- **C01-02 (ASSISTED distinct from AUTO).** `_should_auto_submit` now distinguishes modes: `AUTO` auto-submits; `MANUAL` never auto-submits; `ASSISTED` waits for explicit confirmation on checklist / quality-decision / final-disposition / identity-transformation contracts, while pure execution may auto-submit. Fail-safe: wait if unclear.
- **C01-03 (freeze effective mode).** The effective completion mode is resolved once at operation creation (`_resolve_mode` at `OperationRegistry.start`) and stored on `op.completion_mode`; all subsequent auto-submit gating reads the frozen value, so a mid-operation `global_run_mode` change does not retroactively alter an already-active operation.

## OPS-02-C02 — Checklist completion semantics

- Checklist payload is now **structured** — a list of `{"item_id": str, "completed": bool}` items. `OperationExecution.checklist` is `list[dict]`.
- `_validate_checklist_completion()` enforces the gate **fail-closed**: checklist must be a non-empty list; every item must be an object with a non-empty string `item_id`; and `completed` must be exactly `True` for every item. A present-but-incomplete item (`completed: False`), a missing `item_id`, or a plain-string item is rejected — **item exists ≠ item completed**.
- AUTO synthetic checklist is now fully neutral (`demo_item_1/2/3`, all `completed: true`) — simulation placeholders, not TIPA process facts.

## OPS-02-C03 — Runtime / schema contract reconciliation

- **Why.** The implemented `OperationExecution.to_dict()` had drifted from `.ai-harness/schemas/operation-execution.schema.json` (structured checklist, string `source`, `attempt_number`, `terminal`). This gate reconciles the schema to the runtime — **no runtime behavior changed**.
- **Final checklist schema.** `checklist` is `array` of `$defs/checklistItem` — `{item_id: string (minLength 1), completed: boolean}`, `additionalProperties: false` on the item. Generic; no TIPA-specific fields.
- **Final source representation.** `source` is a `string` enum `["simulated", "manual", "imported"]` (runtime emits `"simulated"`).
- **`attempt_number`.** `integer`, `minimum: 0`.
- **`terminal`.** `boolean` (true for no-recovery terminal state such as `FAILED + FAILED_FINAL`).
- **Also removed.** `LINE_OUT`/`LINE_IN` from the `routing_action` enum (frozen ASSY scope has no Line-Out/In).
- **Executable validation.** `tests/test_ops02_schema_contract.py` loads the authoritative schema and validates real runtime `to_dict()` payloads using `jsonschema` (`Draft202012Validator`): 9 positive runtime cases + 5 negative fail-closed cases, plus schema file-quality checks. Added `jsonschema>=4.0` to `[project.optional-dependencies].dev`.
- `active_operations[]` (`ActiveOperationView`) is a UI read-model subset (empty-string enum defaults, no `checklist`/`source`) and is intentionally **not** validated against this full contract schema.


