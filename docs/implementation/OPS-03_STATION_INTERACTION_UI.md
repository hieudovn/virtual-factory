# OPS-03 — Station Interaction UI / Inspector Binding (implementation notes)

> Baseline: `33555f7`
> Gate: UI BINDING ONLY — no new domain semantics. Runtime state machine unchanged.

## Architecture

```text
Physical Canvas (positions[])
      │
      └── selected station / WIP  (same resolution target)
                    │
                    ▼
        active_operations[]  +  station_contracts[]
                    │
                    ▼
           Operation Inspector (top-right popup)
                    │
                    ▼
        POST /assy-demo/operation-command
                    │
                    ▼
        DemoController.submit_operation_command
                    │
                    ▼
        AssyLineRuntime.submit_operation_command   (runtime decides)
                    │
                    ▼
        next authoritative snapshot (refreshed; UI never mutates truth)
```

- Station and WIP selection resolve to the same `OperationExecution`
  (`station_id` + `wip_id` from `positions[]`); no separate station/WIP action state.
- The renderer derives controls from `station_contracts[].capabilities` and
  `required_action` — never from a hard-coded `if AP03 / if AP06` form tree.
- Action-required is derived from projection truth only: an operation still
  `AWAITING_*` in a snapshot whose `completion_mode != AUTO` needs a human
  command. This does not duplicate `_should_auto_submit()` (pure-execution
  ASSISTED and AUTO ops resolve within the dwell and never surface as
  `AWAITING_*`).

## Backend additions (additive)

- `AssyDemoSnapshot.station_contracts[]` — `StationContractView`
  (`station_id`, `capabilities`, `default_mode`, `required_action`,
  `normal_action`, `allowed_commands`, `checklist_items`). Checklist templates
  are neutral (`demo_item_1/2/3`, `completed: false`) — no TIPA process facts.
- `ActiveOperationView.checklist` — structured `{item_id, completed}` list
  (enriched additive field).
- `DemoController.submit_operation_command()` / `set_run_mode()` /
  `run_mode` — thin adapters over `AssyLineRuntime`.
- `AssyDemoComposition.set_run_mode()` — sets `global_run_mode` on all contexts.
- API endpoints:
  - `POST /assy-demo/operation-command` `{station_id, wip_id, command, payload?}`
    → 200 authoritative snapshot, 400 missing fields, 409 runtime rejection.
  - `POST /assy-demo/run-mode` `{mode}` → 200 snapshot / 400 invalid mode.

## Frontend additions (`assy_demo.js/html/css`)

- Run-mode select (`AUTO` / `MANUAL` / `ASSISTED`) bound to the run-mode endpoint.
- Capability-driven operation block in the top-right Context Inspector:
  - pure execution → `[DONE]`
  - checklist → neutral checkboxes + `[CONFIRM & COMPLETE]` (disabled until all checked)
  - quality decision → `[CONFIRM]` + result/attempt (PASS/FAIL read from runtime)
  - identity transformation → `[JOIN COMPLETE]`
  - final disposition → `[RELEASE]`
- Fail-closed submission: rejection shows a compact error and re-syncs the
  authoritative snapshot; no optimistic local completion.
- Subtle action-required indication: station highlight + compact count badge.
- RESET and sub-line switch clear pending checklist state and stale errors.

## Frozen boundaries preserved

- `positions[]` unchanged; `active_operations[]` / `station_contracts[]`
  additive only.
- No Line-Out/In/Rework/Scrap; no new quality vocabulary; no MO model; no
  conveyor/genealogy changes; AP04 child MTR created only by runtime.

## Tests

- `tests/test_ops03_interaction.py` (22 tests): projection shape, command
  surface (DONE / checklist / CONFIRM / JOIN / RELEASE), stale rejection,
  AUTO/ASSISTED non-blocking, controller run-mode integration, API fail-closed.

## OPS-03-C01 — Checklist interaction contract & server-side gate alignment

- **Capability ≠ gate.** `StationContract` now carries explicit interaction
  metadata: `checklist_items` (neutral required item ids) and
  `checklist_required_for_action` (the action gated by that checklist). Only
  AP03 currently sets both (`CONFIRM_AND_COMPLETE`); AP11 keeps `checklist`
  capability but has no checklist gate (`checklist_items=()`,
  `checklist_required_for_action=None`) — so RELEASE does not inherit the AP03
  demo checklist.
- **Server authority.** `_validate_checklist_completion(items, contract)`
  validates the **exact required set** against `contract.checklist_items`:
  fails closed on missing/empty, partial subset, unknown id, duplicate id,
  malformed item, and `completed != True`. Frontend button-disable is
  convenience only; the runtime is the authority.
- **Single source of truth.** The AUTO synthetic checklist is derived from
  `contract.checklist_items` (no duplicated id list). The snapshot projection
  exposes `checklist_items`/`checklist_required_for_action` only for gated
  actions; the renderer gates on `checklist_required_for_action ===
  current action`, not `capabilities.checklist`.
- **Distinction preserved.** `contract.checklist_items` = what is required;
  `operation.checklist` = what was actually submitted/completed. The UI submits
  the full required set.

