# SA REVIEW INBOX

Task: VF-ARCH-05
Status: READY FOR SA REVIEW
Parent: Issue #39 VF-vNEXT-ARCH (prerequisite: ARCH-04 #43 CLOSED as completed)

Gate type:
Architecture / design gate — documentation & evidence only (no production
migration implementation)

Architecture baseline:
ARCH-01 @ feature/vf-arch-01 41903e186e96a05726483e4a17b9ac2d9cd56655
ARCH-02 @ feature/vf-arch-02 40454487acb4d5667872168a88c8b742c29cb975
ARCH-03 @ feature/vf-arch-03 392401bdfaf1ee2acf4ebcd204dbcfa419359e4c
ARCH-04 @ feature/vf-arch-04 d5c155b636481017a25596ace5e09062b88bc450
Production baseline: canonical main @ f5261c8 (unchanged; not merged)

Frozen decisions:
- Target hierarchy lossless with ARCH-01: TIPA = Workspace; ASSY = child
  Simulation Scope; ASSY-SL01..06 = child Simulation Scopes (executable, each
  owns one AssyLineRuntime); station/AP/WIP/carrier = Simulation Objects. No
  retype, no flatten.
- Standalone + federated ASSY use the SAME AssyLineRuntime; no second/forked
  runtime path.
- AssyLineRuntime reuse boundary: wrap/adapt around a frozen core; never
  rewrite route/quality/genealogy/timing.
- Identity migration: structural path TIPA/ASSY/ASSY-SLnn/<object>; local ids
  preserved; distinct from PIM semantic id and outputs.namespace.
- Parent/child authority non-overlapping: parent adds composition/run/context/
  boundary services only; never mutates child domain state.
- Regression invariants (12) frozen with repo evidence + discrepancies reported
  verbatim; they are the migration acceptance oracle.
- ASSY UX preserved unchanged until implementation migration (ARCH-04 boundary).
- ASSY projections map to ARCH-03 contracts; no duplicate store; station-level
  Capabilities not auto-promoted into a global platform capability registry.
- Migration sequence frozen (5 steps: host seam -> ASSY wrapper -> hierarchy
  exposure -> UI integration -> regression proof); not implemented.
- Fail-safe: any migration slice failing the frozen invariants STOPs for SA.

Regression invariants (evidence 06):
route 12 positions (PRE-ASSY first); AP04 both-parent genealogy; AP06 retest;
AP08 reinspect; AP11 final-QC; failed_final terminal+idempotent; LINE_OUT
good/reject; quality/checklist/measurement (DEMO_SYNTHETIC); deterministic
timing + idempotency keys; six sub-lines; continuous/compressor functionality;
demo behavior preserved unless demo-only.

Reported discrepancies (verbatim): SSO2_BUFFER/RSO2_BUFFER are conceptual labels
not code tokens; FINISHED = WipLifecycle.RELEASED (not a position); tipa.py
build_tipa_topology is legacy M3-S03 single-line; mes_adapter.py holds no
determinism/idempotency logic; AP06 retest-in-place != legacy AP04 rework.

STOP conditions: none triggered.

Production code changed: NO
ARCH-06 started: NO

Report:
.ai-harness/sa-review/reports/VF-ARCH-05.md

Evidence:
.ai-harness/sa-review/evidence/VF-ARCH-05/ (9 files: 01…09)





