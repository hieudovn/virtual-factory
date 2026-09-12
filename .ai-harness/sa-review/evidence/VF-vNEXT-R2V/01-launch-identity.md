Validation head: 12697dd9462e68e85761bee9fe25bfb68d18ce64
Base (technical branch point): `4fc81e72780fe14ba5532407fdc8113b44385617`
Branch: `feature/vf-vnext-r2v`
Verdict: PASS

# 01 — Launch / navigation / identity (V01)

Method: real product path driven in-process — `/workspaces` selection then the rich
`/assy-demo` page; no test doubles, no second controller.

Observed (source `01-launch-identity.json`):
- `/workspaces` selects `TIPA`: `workspace_id=TIPA`,
  `run_id=TIPA-0001`, `scenario_id=tipa-default`.
- Rich page opens HTTP **200** and shows
  **6** canonical rows immediately
  (`step_count_before=0` -> `step_count_after_open=0`).
- Same session in shell and rich UI: `same_workspace_id=True`,
  `same_run_id=True`, `same_scenario_id=True`,
  `profile_id=tipa-assy-happy_path`.
- Opening the rich UI advances no time:
  `opening_rich_ui_advances_time=False`.
- Federation count: `0` before ->
  `1` after open, i.e. exactly ONE runtime authority
  (`single_runtime_authority=True`,
  `authority=canonical_tipa_runtime_session`).

**V01 = PASS.**
