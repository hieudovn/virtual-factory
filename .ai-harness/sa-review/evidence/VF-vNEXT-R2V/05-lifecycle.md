Validation head: (final commit on this branch)
Base (technical branch point): `4fc81e72780fe14ba5532407fdc8113b44385617`
Branch: `feature/vf-vnext-r2v`
Verdict: PASS

# 05 — Lifecycle: STEP / RESET / NEW ATTEMPT / REPLAY + SH-WTP isolation (V05)

Observed (source `05-lifecycle.json`):
- STEP (workspace shell) advances the SAME session
  240.0 s -> 360.0 s
  (`shell_step_advanced_same_session=True`).
- RESET: `same_run_id=True`, `all_six_at_zero=True`,
  `motors_zero=True`, `scenario=HAPPY_PATH`,
  `detail_time_s=0.0`.
- NEW ATTEMPT: `fresh_run_id=True`,
  `rich_identity_follows=True`,
  `state_equivalent_to_pre_attempt=True`.
- REPLAY: `fresh_run_id=True`,
  `deterministic_state_equivalent=True`
  (state `[["ASSY-SL01", 240.0, 3, 0], ["ASSY-SL02", 240.0, 3, 0], ["ASSY-SL03", 240.0, 3, 0], ["ASSY-SL04", 240.0, 3, 0], ["ASSY-SL05", 240.0, 3, 0], ["ASSY-SL06", 240.0, 3, 0]]`).
- SH-WTP switch isolation: `{"shwtp_existed": true, "tipa_run_unchanged": true, "tipa_step_count_unchanged": true, "tipa_time_unchanged": true}`.

**V05 = PASS.**
