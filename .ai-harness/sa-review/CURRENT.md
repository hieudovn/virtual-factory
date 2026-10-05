# SA REVIEW INBOX

Task: DDAY-B7-X01-C01 — event-only operating_state + v2 contract + QoS-1 drain
Status: implementation pushed; machine status is derived by `run_task_gate.py`

Authority:
SA Issue hieudovn/virtual-factory#114 (C01 ONLY)
Parent: DDAY-B7-X01 / #113
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
SA-reviewed C02 head / C01 baseline: f0f5428e21d3f63f22c3e1419600dd63a30b1f75
origin/main (harness expected_base_sha): f5261c8ca18cd4e01779c0274b55270ba028b4e5

What was done:
- Enum operating_state is event-only / non-measurement (MACHINE_STATE_CHANGED).
- Contract version bumped to dday-bw-b1-v2.
- Existing MqttGateway uses acknowledged QoS-1 publish_raw and bounded drain before disconnect.
- Topology/route, timestamps, six event types, Capper/Compressor, and KPI ownership preserved.

NOT authorized: merge, deploy, or PlantOS #49.
The PM does not self-certify COMPLETE / CLOSED / SA APPROVED.
