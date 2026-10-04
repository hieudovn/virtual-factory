# SA REVIEW INBOX

Task: DDAY-B4-C01 — Unmet Water Conservation + B3 Evidence Restore
Status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW

Authority:
SA Issue hieudovn/virtual-factory#106 (C01 ONLY)
Parent: hieudovn/virtual-factory#105
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Issue #106 was not readable via the available GitHub token (403/404). This
inbox follows the SA review comment on PR #101 (2026-10-03T15:35:49Z,
CORRECTION REQUIRED at 0f9606b) and the explicit user execution order.

Baselines:
SA-reviewed B4 head / C01 start: 0f9606bbc8690e80cfdbf9c4105bcfa998e6e0e8
origin/main (harness expected_base_sha): f5261c8ca18cd4e01779c0274b55270ba028b4e5
Accepted B3 head for the restore: 23b6208266751a8c508b0d96fd7a736dffc5676c

What was done:
- _apply_draw() keeps unpaid Filler demand on the pending ledger
  (pending -= drawn). Unmet demand is published as unmet_water_demand_m3;
  water_request_total_m3 = draw + unmet.
- The two accepted B3 evidence files were restored byte-for-byte to 23b6208.
  B4-specific UI-smoke compatibility lives under evidence/DDAY-B4/.

Tests:
  C01 3/3 | B4 30/30 | full suite 1719/1719 exit 0

Smokes:
  SMOKE-BW-UNMET    PASS
  SMOKE-BW-FACTORY  PASS
  SMOKE-BW-UI       PASS (B4-owned copy)
  SMOKE-BW          PASS

Evidence:
.ai-harness/sa-review/evidence/DDAY-B4-C01/
Report:
.ai-harness/sa-review/reports/DDAY-B4-C01.md

Verification commands:
python .ai-harness/sa-review/evidence/DDAY-B4-C01/smoke_unmet_water.py
python .ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_factory.py
python .ai-harness/sa-review/evidence/DDAY-B4/smoke_bottled_water_ui.py
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py
python -m pytest -q
python .ai-harness/scripts/run_task_gate.py --task .ai-harness/tasks/DDAY-B4-C01.json --token <token>

Machine gate (first READY derivation):
  exit 0, P01-P24 PASS, A01-A14 14/14
  SHA 9b51cbc47b34d65f72b604c6578adbf1d2eb2de4
  CI run 37170631556 success

NOT authorized: merge, B5, or any later slice.
