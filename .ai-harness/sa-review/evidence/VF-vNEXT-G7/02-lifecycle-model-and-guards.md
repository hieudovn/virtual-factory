# VF-vNEXT-G7 · Evidence 02 — Run lifecycle model + guards (Issue #52 A, D, 1, 5)

`src/virtual_factory/runcontrol/lifecycle.py`

- `RunState` — `created | running | paused | stopped | failed`; `STOPPED` and
  `FAILED` are terminal for the current run attempt.
- `RunRecord` — one run attempt: immutable `RunContextV2` + guarded mutable
  lifecycle state + canonical `target_path`/`target_kind` + deterministic
  `effective_scopes` (path strings) + `effective_sub_line_ids` (leaf ids) +
  `step_count`/`last_time_s`/`last_result`/`failure`.
- `RunLifecycleService` — platform-level authority:
  - `create_run(target_path, scenario_id=...)` — builds one immutable
    `RunContextV2` (fresh `run_id`, coherent `workspace_id`/`scope_path`/
    `scenario_id`), resolves the effective executable scope set, state `created`.
  - `start/pause/resume/stop` — fail-closed transition guards; pause/resume
    change orchestration permission only (no domain call); stop is terminal
    (history preserved).
  - `step` — only from `running`; delegates to the execution bridge's next
    natural boundary; on a failed window the run transitions to `failed`
    (distinct from success) with no rollback claim.
  - `reset` — capability-scoped (only when the bridge declares `supports_reset`
    and the run is non-terminal); never reuses a terminal historical run.
  - `restart`/`replay` — require/accept terminal source runs and create a fresh
    `run_id` with `source_run_id` lineage; replay pins prior `scenario_id`/
    `model_id`/`profile`/`random_seed` and raises `ReplayUnavailableError` when
    the pinned scenario authority is missing (explicit, never fabricated).

Guards are fail-closed; a stale/wrong `run_id` raises `RunLifecycleError`
(`_get`), so no mutation can target a run that does not exist.

Proven by tests: `TestLifecycleGuards` (valid + invalid transitions),
`TestRunContext` (immutability, coherence, single scenario authority),
`TestRunIdentityAndLineage` (stale run_id, pause/resume no domain mutation,
stop terminal, restart lineage, replay lineage + no overwrite).
