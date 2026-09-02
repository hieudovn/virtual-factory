# SA REVIEW INBOX

Task: VF-ARCH-02
Status: READY FOR SA REVIEW (runtime composition contract frozen)
Parent: Issue #39 VF-vNEXT-ARCH (prerequisite: ARCH-01 #40 CLOSED as completed)

Gate type:
Architecture / design gate — documentation & evidence only (no production
implementation)

Architecture baseline:
ARCH-01 package @ feature/vf-arch-01 41903e186e96a05726483e4a17b9ac2d9cd56655
Production baseline: canonical main @ f5261c8 (unchanged; not merged)

Frozen runtime-composition contract:
- Coordinator = composition service; NOT a domain engine (anti-responsibilities:
  no AP/WIP/quality, physics, recipe, control logic, PIM, monitoring).
- Common run lifecycle: validate -> create -> start -> step/pause/resume ->
  stop -> reset; replay distinct from reset; one workspace run owns child run
  contexts; child run identity scope-scoped; container-only scopes have no run
  context.
- Time/sync: composition time vs scope-local time vs sync boundary vs internal
  cadence vs wall-clock. Invariant: synchronized composition does NOT require
  identical timestep/scheduler (C/D/Batch mixed cadences compose).
- Determinism: stable ordering key; explicit inputs/version/seed; no
  dict/set/hash/time-of-day ordering; replay != snapshot restore.
- Boundaries: material / utility-energy / information-observation /
  coordination-event categories; structural identity (NOT PIM canonical);
  boundary exchange = only cross-scope data path; direct mutation forbidden.
- Hybrid archetypes (C+C, D+D, C+D, Batch+C) compose without one shared engine.
- ASSY maps as six executable sub-line scopes over existing AssyLineRuntime
  (not rewritten); demo policy != plant truth.
- PH00 runtime.engine = compatibility/default/profile descriptor; not
  one-engine-per-workspace; no schema change.

Non-decisions deferred to ARCH-03+: production coordinator classes; final port
payload/schema; Observation/Event/Alarm schema (ARCH-03); capability registry
(ARCH-03); UI (ARCH-04); TIPA/ASSY migration (ARCH-05+); SH WTP runtime;
semantic binding; provenance impl; historian; snapshot/checkpoint impl;
frontend migration; plant-control authority.

Production code changed: NO
ARCH-03 started: NO

Report:
.ai-harness/sa-review/reports/VF-ARCH-02.md

Evidence:
.ai-harness/sa-review/evidence/VF-ARCH-02/ (7 files: 01…07)




