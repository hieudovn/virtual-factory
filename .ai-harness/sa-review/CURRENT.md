# SA REVIEW INBOX

Task: DDAY-B7-X01-C02 — no synthesized state events + fail-closed QoS-1 ACK
Status: implementation pushed; machine status is derived by `run_task_gate.py`

Authority:
SA Issue hieudovn/virtual-factory#115 (C02 ONLY)
Parent: DDAY-B7-X01-C01 / #114
Grandparent: DDAY-B7-X01 / #113
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
SA-rejected C01 head / C02 baseline: 97e313ab0df6efb19b4374cfd857940f9e5c76fd
origin/main (harness expected_base_sha): f5261c8ca18cd4e01779c0274b55270ba028b4e5

What was done:
- Stopped synthesizing MACHINE_STATE_CHANGED from current operating_state values.
- Kept EVENT_ONLY / NON_MEASUREMENT metadata for the three operating_state entries.
- QoS-1 publish now fails closed on timeout, missing ACK, or negative rc.
- Drain/disconnect reports an undelivered tail as failure.

NOT authorized: merge, deploy, or PlantOS #49.
The PM does not self-certify COMPLETE / CLOSED / SA APPROVED.
