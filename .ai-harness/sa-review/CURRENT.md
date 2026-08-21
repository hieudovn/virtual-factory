# SA REVIEW INBOX

Task: VF-DM-DEMO-ASSY-MES-02
Status: IMPLEMENTED — READY FOR SA REVIEW (six-sub-line MES contract bridge)

Baseline (accepted six-sub-line): 248e70dd4dd327a104e00d200e51608ac017a301
Remote baseline branch: origin/docs/m6-s01-tipa-baseline (no newer commit)
Branch: feature/dm-demo-assy-mes-02
Contract version: tipa-assy-demo-v1

Report:
.ai-harness/sa-review/reports/VF-DM-DEMO-ASSY-MES-02.md

Evidence:
.ai-harness/sa-review/evidence/VF-DM-DEMO-ASSY-MES-02/

Production code changed: YES (additive)
Six-sub-line runtime / discrete engine / observation core / MQTT redesigned: NO

Summary:
Additive six-sub-line MES contract bridge (assy_mes_bridge.py) projects the
authoritative /assy-demo runtime to MES-compatible messages via the existing
M5 pipeline. Operational line state (mes.run_status) separated from
conveyor_state (RUNNING → FAULT → STOPPED → RUNNING); deterministic AP05_JAM
(mes.issue raised/resolved); one DOWNTIME_START → DOWNTIME_END (120 s);
LINE_OUT GOOD|REJECT derived from authoritative state; mes.oee_summary per
sub-line/run reconciled (below 100%, at least one reject); contract provenance
on every message (message_key==idempotency_key, contract_version, run_id,
subline_id, occurred_at). Control surface /assy-demo/{jam,recover,
run-to-terminal,mes-messages,version}; reset bumps generation. Docker bakes
SOURCE_SHA → VF_SOURCE_SHA exposed at /assy-demo/version. 18 new bridge tests;
full suite 1588 passed.

Open findings:
- Two pre-existing baseline test failures (test_assy_demo.py::test_scenario_switch_resets_state,
  test_ops04_c01.py::test_select_does_not_mutate_runtime_state) — unrelated to
  this gate; outside allowed paths.
- Docker smoke + exact-head CI pending (see SA-ready message for CI URLs).

