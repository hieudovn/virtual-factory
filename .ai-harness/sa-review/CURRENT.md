# SA REVIEW INBOX

Task: DDAY-B7-X01-C03 — export-session event cursor / watermark
Status: implementation in progress; machine status is derived by `run_task_gate.py`

Authority:
SA Issue hieudovn/virtual-factory#116 (C03 ONLY)
Parent: DDAY-B7-X01-C02 / #115
Grandparent: DDAY-B7-X01-C01 / #114
Great-grandparent: DDAY-B7-X01 / #113
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
SA-rejected C02 head / C03 baseline: 39428b08ff5fbd19efe6dc0701bb64bafa73bf83
origin/main (harness expected_base_sha): f5261c8ca18cd4e01779c0274b55270ba028b4e5

What this slice does:
- Adds a tiny export-session cursor so retained recent_events publish once per run/session.
- Keeps map_snapshot() a pure full projection.
- Applies the watermark to all six accepted event types.
- RESET / new run resets the cursor.

NOT authorized: merge, deploy, or PlantOS #49.
The PM does not self-certify COMPLETE / CLOSED / SA APPROVED.
