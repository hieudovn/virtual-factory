# SA REVIEW INBOX

Task: VF-vNEXT-G5
Status: READY FOR SA REVIEW (Migrate TIPA Workspace / ASSY Federation onto G1–G4)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized implementation gate after G4)
Prerequisite: Issue #49 accepted as completed; G1–G4 contracts authoritative

Gate type:
Accelerated implementation gate — Migrate TIPA Workspace / ASSY Federation onto G1–G4 (G5), per Issue #50

Architecture baseline:
ARCH-01..06 accepted; G1–G4 contracts authoritative
Required base (branch point): ae0a86e4ad8add77c731fbd597534f24a2f7b575 (accepted G4 final head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (new additive package src/virtual_factory/federation/):
- tipa_workspace.py: canonical Workspace "TIPA" -> container-only Scope "ASSY"
  -> six executable-capable ASSY-SL01..SL06; deterministic G1 structural paths
  TIPA/ASSY/ASSY-SLxx; fail-closed sub_line_path/assy_scope_path.
- assy_participant.py: AssySubLineAdapter — G4 ExecutableParticipant over one
  existing AssyLineRuntime (fixed G1 scope_path; current_time_s delegates;
  advancement via public ASSY runtime ops only, oracle-driver order). Exact
  natural-boundary landing only; overshooting/fractional targets fail closed.
- assy_host.py: TipaAssyFederation — owns TIPA Workspace; six isolated runtimes
  via existing demo construction/config-isolation pattern (deepcopy + ordinal
  seed); binds each to its executable G1 scope; exposes G4 Coordinator seam
  (empty graph); ASSY container never executable; domain truth stays in runtime.

Frozen invariants preserved:
- AssyLineRuntime is the single source of ASSY truth; NOT rewritten.
- G1 StructuralPath is the runtime structural identity; no PIM canonical ID
  fabricated; demo identity is deployment metadata only.
- G4 coordinator remains a composition service; C01/C02/C03 rules preserved
  (identity drift/mismatch fails closed).
- No new cross-sub-line synchronization policy; no fractional dwell/index; no
  hidden time rewrite; supported boundaries are natural ASSY boundaries.
- ASSY stays container-only; no G6 UI, G7 run-control/replay, G8+, G9 semantic
  binding, G10 SH-WTP.

Standalone / federated parity (evidence 05):
- Fast-config: 16-cycle RELEASE and 7-cycle AP04 JOIN parity — standalone vs
  federated identical canonical domain state + released set.
- Real demo-config: six sub-lines federated at shared natural 120s boundary;
  each equals its standalone replica.
- Complete ASSY regression oracle stays green (354).

Identity / isolation (evidence 06):
- TIPA/ASSY/ASSY-SL01..06 resolve through G1 Workspace.
- Six runtimes/configs/RNG seeds isolated; no cross-scope mutation (single
  sub-line window leaves the other five untouched).
- Identity drift/mismatch (incl. during advance_to) fails closed via existing
  G4 rules.

STOP-condition assessment: none triggered (no AssyLineRuntime rewrite, no
fractional dwell, no new sync policy, ASSY container-only, G1–G4 intact, no
demo-policy-to-plant-truth leakage, no G6+).

Test / regression results (evidence 07):
- New G5 tests: 24 passed.
- G4 composition tests: 56 passed.
- G1 workspace: 32 passed.
- G2 provenance: 36 passed.
- G3 Observation/Event/Alarm (+ M5 + alarm_manager): 328 passed.
- Core graph/port/runtime: 21 passed.
- Discrete runtime/scheduler: 279 passed.
- Complete ASSY regression oracle: 354 passed.
- Continuous/compressor baseline: 61 passed.
- Full repository suite: 1873 passed (0 failures).
- Compile check PASS (no configured ruff/mypy/black in repo).

Deferred (NOT implemented): G6 UI, G7 run-control/UI/API/replay policy, G8+,
G9 semantic binding, G10 SH-WTP runtime, any new synchronization policy, any
AssyLineRuntime rewrite.

STOP conditions: none triggered.

G6 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G5.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G5/ (7 files: 01 repo-first discovery +
scope; 02 tipa workspace mapping; 03 assy participant adapter; 04 federation
host; 05 standalone/federated parity; 06 identity/isolation + STOP assessment;
07 tests + regression results)






