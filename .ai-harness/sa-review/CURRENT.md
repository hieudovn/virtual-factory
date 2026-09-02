# SA REVIEW INBOX

Task: VF-ARCH-03-C01
Status: READY FOR SA REVIEW (C01: event/alarm fact-vs-state, capability authority, required-capability visibility, container readiness corrected)
Parent: Issue #39 VF-vNEXT-ARCH (prerequisite: ARCH-02 #41 CLOSED as completed)

Gate type:
Architecture / design gate — documentation & evidence only (no production
implementation)

Architecture baseline:
ARCH-01 @ feature/vf-arch-01 41903e186e96a05726483e4a17b9ac2d9cd56655
ARCH-02 @ feature/vf-arch-02 40454487acb4d5667872168a88c8b742c29cb975
Production baseline: canonical main @ f5261c8 (unchanged; not merged)

Frozen contracts:
- Runtime State -> Observation -> Monitoring / Live Series / Export /
  Integration: Runtime State = only mutable truth; Observation = immutable/
  downstream; projections cache/index but never mutate truth.
- Runtime Activity -> Event -> Alarm: Alarm ⊂ Event (not a parallel store);
  Event Timeline + Alarm List are projections; alarm lifecycle never mutates
  the historical event fact.
- Live Series (bounded current-run) != Historian (durable, outside baseline);
  Run Result = finalized summary, not a warehouse.
- Capability namespaces: platform / execution-domain / workspace-feature —
  separated; never hard-coded by workspace name.
- Capability states: available / not_applicable / not_ready / restricted /
  error-degraded (error vs degraded = operational substates).
- Readiness = deterministic categorical aggregation of capability + binding +
  runtime + child-scope states; never a competing evaluator; never hides
  blockers; no arbitrary health score.
- Provenance != Evidence: VF owns provenance (origin_kind=simulation, synthetic
  vocabulary); PIM/external owns evidence (SourceMapped/SiteVerified/...); VF
  never upgrades evidence; synthetic never relabeled measured/site truth.
- Monitoring and Context Inspector share the same observation/event facts
  (different perspective, not two stores).

Conceptual mappings:
- ASSY: stations/WIP/quality/genealogy -> observations/events; quality alarms =
  event specializations; station capabilities = domain capabilities
  (capability-driven dispatch, no workspace-name routing).
- SH WTP: continuous/equipment observations, water-quality domain capabilities,
  threshold alarms, aggregated readiness — conceptual only (no invented site
  truth).

C01 corrections applied:
- Alarm Event (immutable fact) vs Alarm Condition/State (mutable projection)
  separated; Event.status constrained to occurrence/fact classification captured
  at creation; ack/clear workflow never mutates the Alarm Event fact.
- Capability state authority = declared provider/contract owner (observation does
  not confer authority); aggregators observe but do not invent/upgrade.
- Capability requirement/declaration (required/optional/not expected) is a
  separate axis from runtime state; required-missing = explicit blocker
  (derived not_ready), never silently omitted; not_applicable = declaratively
  irrelevant, not merely absent.
- Container-only scope readiness separates structural/composition readiness (can
  be READY) from execution readiness (not_applicable); aggregation exposes child
  blockers explicitly.

Production code changed: NO
ARCH-04 started: NO

Report:
.ai-harness/sa-review/reports/VF-ARCH-03.md

Evidence:
.ai-harness/sa-review/evidence/VF-ARCH-03/ (7 files: 01…07)





