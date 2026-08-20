# SA REVIEW INBOX

Task: VF-DM-DEMO-ASSY-MES-01
Status: READY FOR SA REVIEW

Baseline (origin/main): 17a1d9ecafb170fa94e8d01a1f12d84e79982773
Branch: feature/dm-demo-assy-mes-01
Contract version: tipa-assy-demo-v1

Report:
.ai-harness/sa-review/reports/VF-DM-DEMO-ASSY-MES-01.md

Evidence:
.ai-harness/sa-review/evidence/VF-DM-DEMO-ASSY-MES-01/

Production code changed: YES (additive)
Simulation engine redesigned: NO
Observation pipeline core redesigned: NO
MQTT gateway redesigned: NO

Summary:
Deterministic resettable single-sub-line ASSY-SL01 VF→MES customer demo
(SSO2+RSO2 → PRE-ASSY → AP01..AP11 → LINE_OUT) built on the existing M5
pipeline. 4 deterministic WIPs (happy GOOD, AP06 fail/retest/pass GOOD, AP05
jam fault→recover GOOD, terminal final-QC FAIL REJECT), line-state
(RUNNING/FAULT/STOPPED), exception AP05_JAM, downtime 120s, LINE_OUT
GOOD/REJECT, and a reconciled OEE summary (60%). Additive projection:
mes.oee_summary + LINE_OUT execution_event. Minimal control surface in
ui/api.py. 19 new tests pass; full suite 1086 passed. Fixtures + JSONL evidence
under evidence/. Demo: python -m virtual_factory.assembly.demo_assy_mes.
