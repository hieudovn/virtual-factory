# SA REVIEW INBOX

Task: DDAY-B5 — Capper hero + Compressor secondary
Status: pending machine gate (local tests/smokes green)

Authority:
SA Issue hieudovn/virtual-factory#107 (B5 ONLY, including Compressor addendum)
Parents: DDAY-B4 / #105; DDAY-B4-C01 / #106
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
SA Issue #107 expected baseline: b6dcb08a1263e7a84792ea8697d3202fa5e79912
First-B5 READY head / correction baseline: a1e0a307bb360f05323690fe1831ef462f1acf71
origin/main (harness expected_base_sha): f5261c8ca18cd4e01779c0274b55270ba028b4e5

What was done:
- BW-CAP-DEG-01 remains the hero Capper abnormal story.
- BW-CMP-SAG-01 added as a simpler secondary compressor pressure-sag helper.
- Default demo is non-overlapping (compressor PRESSURE_SAG at t=240, after Capper RECOVERY).
- Each scenario is independently disableable and independently testable.
- Compressor does not inhibit production and does not emit downtime.

Local verification:
  B5 Capper + Compressor tests PASS
  Full suite 1739/1739
  SMOKE-BW-B5 / FACTORY / UI / BW all PASS

Evidence:
.ai-harness/sa-review/evidence/DDAY-B5/
Report:
.ai-harness/sa-review/reports/DDAY-B5.md

NOT authorized: merge, B6, or any later slice.
