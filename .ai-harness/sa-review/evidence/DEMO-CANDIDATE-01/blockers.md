# DEMO-CANDIDATE-01 — Blockers & findings

Classification scale:
`BLOCKER-21AUG` · `HIGH` · `POLISH` · `POST-DEMO`

## BLOCKER-21AUG

None found.

## HIGH

None found. No false manufacturing/MES truth, no wrong WIP station, no lost
quality attempt, no false release, no reset corruption, no observation
duplication, canonical UI available.

## POLISH

| # | Finding | Detail | Impact |
|---|---|---|---|
| P1 | Page reload resets the demo | Frame A `ctrl.init()` calls `POST /assy-demo/reset` on every `DOMContentLoaded`. Reloading `/assy-demo` always starts a clean session. | Truth stays correct (clean start). Presenter should avoid refreshing mid-demo; the rehearsal used a single continuous browser session for UI evidence. |
| P2 | Observation volume is high in the live server | A full 6-sub-line HAPPY_PATH run emits 672 observations (all 6 sub-lines run in parallel with continuous feed). All 672 are unique by `(run_id, source_event_id, gateway_id)` — no true duplicates. | Expected for the composition; downstream consumers should partition by `run_id` (sub-line). |

## POST-DEMO

| # | Finding |
|---|---|
| D1 | Optional `resume`/`confirm` behavior before reset-on-reload for operator safety. |
| D2 | Optional dedicated MES receiver integration (external MES ingestion) — classified separately; not built in this gate (JSONL/InMemory fallback validated). |
