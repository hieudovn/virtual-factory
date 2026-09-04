# SA REVIEW INBOX

Task: VF-vNEXT-G2
Status: READY FOR SA REVIEW
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized implementation gate)
Prerequisite: G1 PASS / COMPLETE at ac329fbd7f96614be9f09e8037a3e10cfabaf1dd (#46 CLOSED)

Gate type:
Accelerated implementation gate — Runtime Context + Provenance v2 (G2)

Architecture baseline:
ARCH-01..06 accepted; G1 base ac329fbd7f96614be9f09e8037a3e10cfabaf1dd
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented:
- src/virtual_factory/provenance/ (enums.py, context.py, envelope.py,
  namespace.py, adapter.py, __init__.py): generic immutable RunContextV2 +
  ProvenanceV2 + deterministic output namespace + discrete adapter.
- telemetry/telemetry_frame.py: additive ProvenancedFrame + build_provenanced_frame
  (legacy build_publishable_frame unchanged).
- tests/test_provenance_{context,envelope,namespace}.py,
  tests/test_run_context_adapter.py, tests/test_telemetry_provenance_threading.py.
- discrete.RunContext reconciled via thin adapter (no duplicate authority);
  origin_kind=simulation; only frozen data_status/fidelity; no fabricated PIM
  canonical id; no engine_kind universal authority (profile is informational).

Test / regression results:
- New G2 tests: 32 passed.
- G1 + discrete + telemetry/observation targeted: 415 passed.
- ASSY regression oracle: 354 passed.
- Continuous/compressor baseline: 61 passed.
- Full repository suite: 1711 passed (0 failures).
- Compile check PASS (no configured ruff/mypy/black in repo).

Deferred to G3+ (NOT implemented): observation/event/alarm alignment (G3),
coordinator/ports (G4), ASSY federation (G5), UI (G6), run-control/replay (G7),
regression baseline (G8), semantic binding (G9), SH WTP runtime (G10), protocol
propagation of ProvenancedFrame, namespace consumption.

STOP conditions: none triggered.

G3 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G2.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G2/ (7 files: 01…07)





