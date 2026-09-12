# SA REVIEW INBOX

Task: VF-vNEXT-R3
Status: READY FOR SA REVIEW (Canonical Same-Session Observation / MES Output Reintegration)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R2 accepted head 4fc81e72780fe14ba5532407fdc8113b44385617 (Issue #80); R2V PASS (Issue #82); Issue #81

Gate type:
IMPLEMENTATION gate — the ONLY authorized implementation gate. ASSY outbound
Observation/MES projection restored READ-ONLY on top of the SAME canonical TIPA
RuntimeSession accepted in R1/R2. One run authority; no second runtime/session/
federation/controller; no output-owned lifecycle; no output-driven step/reset.
R4/R5, SH-WTP expansion and gateway/protocol expansion are NOT authorized and NOT
started.

Base (technical branch point): 4fc81e72780fe14ba5532407fdc8113b44385617
Branch: feature/vf-vnext-r3
Head: 5e22da63bee238817327b0f4e21c77bfbcd32b6c
Harness preflight: PASSED

Delivered:
- src/virtual_factory/ui/assy_output.py (NEW): CanonicalAssyOutput read-only
  same-session output adapter (canonical binding; composition shim over
  federation.sub_lines; projection namespace + epoch; hard read-only mutation guard;
  observations()/mes_messages()/mes_trace()/identity()).
- Additive canonical seam in assembly/observation_bridge.py + assembly/assy_mes_bridge.py
  (canonical ran id supersedes the legacy ASSY-SLxx:R<n> generation; canonical identity
  in the fact context; source_run_key + projection_epoch + scope in fact identity;
  default/unbound behaviour unchanged).
- ui/assy_experience.py require_federation() seam; DEFERRED_FEATURES no longer defers
  R3 output (jam/recover/run-to-terminal/scenario_change stay R4).
- ui/api.py: /assy-demo/observations | /mes-messages | /mes-trace serve the canonical
  projection (no longer 503); memoized canonical output adapter; fail-closed
  output_unavailable/output_mutation_blocked responses.
- tests/test_vnext_r3_canonical_observation_mes.py (NEW, 27 tests); migrated the
  obsolete R2 ownership assertion for the R3 endpoints.
- Evidence .ai-harness/sa-review/evidence/VF-vNEXT-R3/ (01..08 JSON + generator);
  report .ai-harness/sa-review/reports/VF-vNEXT-R3.md; manifest gate context + new
  baseline group r3_canonical_observation_mes.

Verified (evidence 01..08, all PASS):
- same canonical run id across shell/rich/output; same six runtime objects; exactly ONE
  federation + ONE session + ZERO legacy controllers on the API path;
- 780 canonical facts over 20 steps (546 operation completions, 72 AP04 genealogy with
  child MTR-0001, 138 quality, 30 AP11 final-QC, 24 releases; 130 per sub-line x 6);
- 1159 MES messages across 7 families covering all six sub-lines, canonical run id in
  every key/payload, contract tipa-assy-demo-v1.1;
- poll idempotency (repeat poll delivers 0; step-then-poll delivers only new facts);
- reset same run id -> fresh projection epoch with no pre-reset collision; NEW ATTEMPT
  (TIPA-0002) and REPLAY (TIPA-0003) fresh output namespaces, deterministic content;
- hold ASSY-SL03 -> 0 new facts on the held line while the other five advance; release
  resumes;
- polling changes nothing (step count/time/positions/genealogy/production/quality) and
  the injected-mutation guard raises OutputMutationError;
- /assy-demo R3 endpoints return 200 canonical data (legacy_runtime_authority false);
  jam/recover/run-to-terminal remain 409 R4.

Regression: R3 focused 27 passed; R1 40 passed; R2 + observation/MES contract suites
passed unchanged; full suite 2556 -> 2583 passed; canonical baseline (40 groups)
machine-derived at the pushed head (see report / SA submission).

Frozen boundaries preserved: no AssyLineRuntime / R1 profile / G4 coordinator change;
no federation/runcontrol change; no G22 reset semantics change; no SH-WTP; no
gateway/protocol work; no R4/R5; no rebase onto main; no merge.

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED /
NOT_IMPLEMENTED.
