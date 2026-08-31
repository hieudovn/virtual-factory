# VF-CONTRACT-FINALITY-01 — regression.md

## New tests

`tests/test_vf_contract_finality_01.py`: **16 passed** (covers gate §12 items
1–16).

## Targeted ASSY / observation / quality regression

Files: `test_m6_int_01.py`, `test_quality_records_projection.py`,
`test_quality.py`, `test_assy_line.py`, `test_assy_demo.py`,
`test_demo_composition.py`, `test_ops02_operation_execution.py`,
`test_ops02_schema_contract.py`, `test_ops04_c01.py`, `test_m5_s01_envelope.py`,
`test_m5_s02_point_policy.py`, `test_m5_s03_service.py`,
`test_m5_s04_projections.py`, `test_m5_s05_gateway.py`,
`test_vf_contract_finality_01.py`.

Result: **535 passed, 2 failed** — the same two documented pre-existing
failures:

- `TestVScenarioSwitch::test_scenario_switch_resets_state`
- `TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state`

## Full suite

```text
python -m pytest tests/ -q
2 failed, 1570 passed in 15.48s
```

1570 = 1554 (baseline) + 16 new tests. The 2 failures are the same pre-existing
ones (unchanged from the accepted baseline — see VF-DEPLOY-01 and
M6-INT-01-C01 reports). No new failures.

## Docker / native producer equivalence (enriched contract)

Rebuilt `vf-assy:latest` with the enriched `src`, recreated the container
(`--force-recreate`, healthy), and drove FAILED_FINAL over HTTP:

```text
RESULT: OK
releases: 0
terminal: ASSY-SL03:R1|QR-0002|assy.quality_result|1.0
          AP06 attempt 2 FAIL is_terminal=True terminal_state='failed_final'
```

Native and Docker emit the identical enriched terminal fact (native evidence in
`failed-final-journey.json`; Docker evidence via `verify_docker_enriched.py`).
