Validation head: 12697dd9462e68e85761bee9fe25bfb68d18ce64
Base (technical branch point): `4fc81e72780fe14ba5532407fdc8113b44385617`
Branch: `feature/vf-vnext-r2v`
Verdict: PASS

# 04 — Inspector / quality / genealogy + retained thin bindings (V04)

Observed (source `04-inspector-quality-genealogy.json`):
- Station contracts: **12** (fields
  ['allowed_commands', 'capabilities', 'checklist_items', 'checklist_required_for_action', 'decision_actions', 'default_mode', 'exception_actions', 'final_disposition_actions', 'normal_action', 'required_action', 'station_id']).
- Read-model keys: ['active_operations', 'actual_dwell_s', 'bottleneck_duration_s', 'bottleneck_station_id', 'canonical', 'canonical_sub_line', 'dwell_number', 'dwell_overrun_s', 'genealogy', 'line_state', 'nominal_dwell_s', 'plant_id', 'positions', 'production', 'production_line_id', 'quality_records', 'recent_quality_events', 'scenario', 'scope', 'simulation_time_s', 'station_contracts', 'sub_line_id', 'variant'].
- Presence: operations `True`,
  quality `True`, genealogy `True`,
  AP04 genealogy visible `True`.
- Selection: `presentation_only=True`, flagged
  `True`; selecting another line keeps the
  same session time (`sl01_detail_time_s_before=720.0`,
  `sl02_detail_time_s=720.0`).
- Retained OPS-03/OPS-04 thin bindings behave unchanged:
  `{"operation_command_missing_fields": 400, "operation_command_stale_target": 409, "run_mode_assisted": 200, "run_mode_invalid": 400, "run_mode_manual": 200, "station_action_stale_target": 409}`.
- Deferred capabilities fail closed (no legacy authority):
  `{"jam": 409, "mes_messages": 503, "mes_trace": 503, "observations": 503, "recover": 409, "run_to_terminal": 409, "scenario_change": 409}`.

**V04 = PASS.**
