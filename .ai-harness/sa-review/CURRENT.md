# SA REVIEW INBOX

Task: DDAY-B2-C01 — Semantic Isolation + Harness Gate Correction
Status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW (machine-derived, gate exit 0)

Authority:
SA Issue hieudovn/virtual-factory#103 (correction only)
Parent: hieudovn/virtual-factory#102
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
SA-issued C01 baseline / branch head at C01 start:
0a1d18e42b5a28009ae05a6e916f9e942a857b38 (match)
harness expected_base_sha (== origin/main):
f5261c8ca18cd4e01779c0274b55270ba028b4e5 (unchanged, not advanced)

Commits on this branch (C01):
27821cc  DDAY-B2-C01 task contract authored from SA Issue #103
8d77277  C01-A semantic isolation + C01-B harness gate repair
7e6221f  C01 allowlist correction (frozen B2 artifact handling)
54fafa6  PR state representation alignment (second harness defect)
(then)   C01 evidence pack + report + inbox pin  <-- reported review SHA

C01-A — semantic isolation:
- Generic units previously published the legacy lifecycle value 'in_assy'.
  Reproduced before the fix through the public API (produce_unit + introduce_unit).
- WipLifecycle gains IN_LINE ("in_line"); the generic route uses it. The legacy
  value is neither removed nor renamed and introduce_to_assy() still yields it.
- Neutral statuses proven at every stage: entry in_line, in-progress in_line,
  station completion completed_station, route completion released, reject rejected.
- Case-insensitive leak sweep (assy/tipa/sso2/rso2/ap05_jam/APxx): 0 findings over
  944 strings across four states; T12 strengthened to catch semantic variants.

C01-B — harness gate repair:
- P21 generated its provisional report without the implementation SHA while P22
  requires it, so the gate could never validate its own artefact (exit 5, P23/P24
  unreachable; reproduced at two heads).
- Fixed by a single report writer that always states the implementation SHA.
  validate_report_consistency.py is untouched and still fail-closed.
- A second task-independent defect surfaced during verification: with a token the
  REST path stores PR state "open" while derive_status.py expects "OPEN", so the
  gate reached P24 with everything PASS yet derived NOT READY. run_task_gate.py now
  aligns the representation; a closed PR still fails closed.

Full task gate (first successful run in this program):
  Status: IMPLEMENTED — PR OPEN — READY FOR SA REVIEW
  Gate: ready_for_sa_review | Satisfied: True | Exit: 0
  P01-P24 all PASS (including P22) | Acceptance 14 PASS, 0 FAIL, 0 UNKNOWN
  Exact-head invariants: remote = PR head = CI head = reported SHA (all true)

Tests:
  B2 + C01 tests 19/19 | harness tests 9/9 | legacy regression 575/575 |
  full suite 1666/1666 (1647 baseline, +17 B2, +2 C01)

Evidence:
.ai-harness/sa-review/evidence/DDAY-B2-C01/ (01..05, machine-evidence.json,
implementation.patch, before/after transcripts, smokes, JUnit XMLs)
Report:
.ai-harness/sa-review/reports/DDAY-B2-C01.md

Verification commands:
python .ai-harness/sa-review/evidence/DDAY-B2-C01/smoke_semantic_isolation.py
python .ai-harness/sa-review/evidence/DDAY-B2/smoke_bottled_water.py
python -m pytest -q
python .ai-harness/scripts/run_task_gate.py --task .ai-harness/tasks/DDAY-B2-C01.json --token <token>
  (do not set PYTHONIOENCODING=utf-8 on Windows for the gate invocation)

Machine record:
.ai-harness/traces/DDAY-B2-C01/evidence.json
.ai-harness/traces/DDAY-B2-C01/gate-report.md

Governance:
- Merge NOT authorized. No next slice authorized (B3+ not started).
- validate_report_consistency.py, derive_status.py and the PM execution contract
  are unmodified; exact-head invariants and acceptance criteria were not relaxed.
- Residual disclosed: the PR-state root cause remains in
  .ai-harness/scripts/verify_remote_state.py (outside the C01 allowlist); the
  orchestrator aligns the representation. SA decision requested if the source fix
  is preferred.
