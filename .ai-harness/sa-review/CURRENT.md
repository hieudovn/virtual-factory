# SA REVIEW INBOX

Task: VF-vNEXT-R2
Status: READY FOR SA REVIEW (Canonical Same-Session Rich ASSY 2D Experience)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R1-C01 accepted head 4f86632; Issue #80 + SA amendment comment 5629686166

Gate type:
IMPLEMENTATION gate. The accepted rich TIPA ASSY experience (Frame A six-sub-line
overview + Frame B existing 2D physical line + station/WIP inspector read models)
now projects the SAME canonical TIPA RuntimeSession used by /workspaces. ONE
product-path TIPA run authority; no legacy DemoController authority; no second
session/federation/runtime. R3 Observation/MES/output, R4, SH-WTP and gateway are
NOT authorized and NOT started.

Base: technical base (branch point) = 4f866323fc73a1f73f6d513d5c91220d14a997b3
Branch: feature/vf-vnext-r2
Head: ab8b943e38be8ef16997b67b2572ed722b91bc41 (local == origin)
Harness preflight: PASSED

Implemented:
- src/virtual_factory/ui/assy_experience.py (NEW): CanonicalAssyExperience --
  same-session rich projection/control adapter (Frame A via accepted
  build_summary/AssyOverviewSnapshot; Frame B detached build_snapshot; canonical
  identity envelope; presentation-only selection; THIN same-session OPS-03/OPS-04
  command + run-mode bindings; explicit deferred seam; hold/freeze read model).
- src/virtual_factory/ui/workspace_monitor.py: public live_session() seam (the ONE
  live session shared with /workspaces) + tipa_config_path + TIPA view metadata
  corrected to shares_session/shares_identity = true (canonical note).
- src/virtual_factory/ui/api.py: /assy-demo served by the canonical experience;
  _get_assy_controller()/legacy controller authority removed; reset/step/snapshot/
  select/overview/sub-lines/sub-line/identity canonicalized; observation/MES/jam/
  recover/run-to-terminal/scenario-change fail closed as explicit deferred
  (503/409 with legacy_runtime_authority=false); NO legacy runtime fallback.
- ui/static/assy_demo.js + .html: binding-only edits (canonical identity bar, no
  reset on page open, pinned scenario selectors disabled, deferred surfaced).
- tests/test_vnext_r2_same_session_rich_assy.py (NEW, 27 tests).
- Migrated legacy OWNERSHIP assertions only (G24/G25 metadata; demo_overview
  route-flag gating) per the SA amendment; OPS-03/OPS-04 API suites pass unchanged.

Evidence (deterministic, evidence/VF-vNEXT-R2/): same-session identity; Frame A six
canonical live rows; Frame B 12 accepted positions with successive WIP movement +
AP04 genealogy; inspector/quality read models; selection presentation-only; rich
STEP/RESET == shell session; held-one/five-continue reflected on UI; deferred
fail-closed endpoints; exactly ONE federation constructed and ZERO legacy
controllers instantiated; static UI binding facts.

Regression: R2 focused 27 passed; full suite 2556 passed; complete canonical
baseline PASS (39 groups) at the pushed head (see report).

Frozen boundaries preserved: no AssyLineRuntime rewrite; no R1 semantics change;
no generic coordinator/lifecycle redesign; no R3 Observation/MES work; no
gateway/OPC/MQTT; no SH-WTP; no broad visual redesign; no rebase onto main.

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED /
NOT_IMPLEMENTED.

Report: .ai-harness/sa-review/reports/VF-vNEXT-R2.md
Evidence: .ai-harness/sa-review/evidence/VF-vNEXT-R2/

Next gate started: NO (R3 NOT started)
