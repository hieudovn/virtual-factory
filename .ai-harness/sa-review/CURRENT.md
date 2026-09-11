# SA REVIEW INBOX

Task: VF-vNEXT-R2
Status: READY FOR SA REVIEW (Canonical Same-Session Rich ASSY 2D Experience)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R1-C01 accepted head 4f86632; Issue #80 (R2) + SA amendment 5629686166

Gate type:
IMPLEMENTATION gate - rich ASSY experience restored on the SAME canonical TIPA
RuntimeSession accepted in R1. ONE product-path TIPA run authority: /assy-demo
obtains the session through the WorkspaceMonitor live-session seam used by
/workspaces (no private cache, no second session/federation/runtime, no legacy
DemoController authority). Frame A = six canonical sub-lines; Frame B = existing
2D renderer from canonical positions[]; inspector/quality/genealogy = detached
read models; selection = presentation only; STEP/RESET = canonical lifecycle;
scenario/profile = pinned run input; R3/R4 capabilities fail closed as deferred.
No broad visual redesign.

Base:
Technical base (branch point) = 4f866323fc73a1f73f6d513d5c91220d14a997b3 (R1-C01 head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged; not rebased)

Implemented:
- src/virtual_factory/ui/assy_experience.py (NEW): CanonicalAssyExperience -
  same-session rich projection/control adapter (Frame A overview via accepted
  build_summary/AssyOverviewSnapshot view models; Frame B detached build_snapshot
  projections + canonical identity envelope; presentation-only selection; thin
  OPS-03/OPS-04 same-session bindings; explicit deferred seam; hold/freeze model).
- src/virtual_factory/ui/workspace_monitor.py: public live_session() seam +
  tipa_config_path; TIPA view metadata corrected to same-session semantics
  (shares_session/shares_identity = true, canonical note).
- src/virtual_factory/ui/api.py: /assy-demo served by the canonical experience;
  _get_assy_controller()/legacy authority removed; reset/step/snapshot/select/
  overview/sub-lines/sub-line/identity canonicalized; observation/MES/jam/recover/
  run-to-terminal/scenario-change fail closed as deferred.
- src/virtual_factory/ui/static/assy_demo.js + assy_demo.html: binding-only edits
  (canonical identity bar, no reset on page open, no scenario mutation, pinned
  scenario selectors disabled, deferred surfaced).
- tests/test_vnext_r2_same_session_rich_assy.py (NEW, 27 tests).
- Legacy ownership assertions migrated per SA amendment:
  tests/test_vnext_g24_workspace_ui.py, tests/test_vnext_g25_acceptance.py,
  tests/test_demo_overview.py (accepted domain capability preserved;
  test_ops03_interaction.py + test_ops04_c01.py pass unmodified).
- .ai-harness/regression/vnext_baseline_manifest.json (R2 gate context +
  r2_same_session_rich_assy group).

Evidence (.ai-harness/sa-review/evidence/VF-vNEXT-R2/): 01 same-session identity,
02 Frame A six live canonical rows, 03 Frame B positions[]/WIP movement/AP04
genealogy, 04 inspector read models, 05 selection presentation-only + STEP/RESET
coherence, 06 held-one/five-continue on the UI projection, 07 deferred fail-closed
(503 R3 / 409 R4, legacy_runtime_authority false), 08 one federation constructed /
zero legacy instantiations, 09 static UI binding facts.

Regression: R2 27 passed; full suite 2556 passed; canonical baseline PASS at the
pushed head (39 groups).

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED;
whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Next gate started: NO (R3 NOT started)

Report:
.ai-harness/sa-review/reports/VF-vNEXT-R2.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-R2/
