# SA REVIEW INBOX

Task: VF-vNEXT-R2V
Status: READY FOR SA REVIEW (ASSY Functional & UI Validation before R3 — validation only)
Parent: TIPA ASSY recovery sequence R1..R4 (R0 / Issue #78 CLOSED - architecture frozen)
Prerequisite: R2 accepted head 4fc81e72780fe14ba5532407fdc8113b44385617 (Issue #80); Issue #82

Gate type:
VALIDATION gate. No product code change. Functional + browser evidence that the
accepted rich ASSY experience (Frame A six-sub-line overview + Frame B 2D physical
line + inspector read models) still preserves the accepted simulation configuration
and six-independent-sub-line behaviour on ONE canonical TIPA RuntimeSession. R3
Observation/MES/output, R4, SH-WTP expansion and gateway are NOT authorized and NOT
started.

Base (technical branch point): 4fc81e72780fe14ba5532407fdc8113b44385617
Branch: feature/vf-vnext-r2v
Head: (final commit on this branch)
Harness preflight: PASSED (branch + clean tree + expected_base_sha == origin/main)

Validated (verdict ASSY_RICH_SIMULATION_VALIDATED):
- V01 launch/navigation/identity: shell and rich UI share one workspace/run/scenario/
  profile (TIPA / TIPA-0001 / tipa-default / tipa-assy-happy_path); opening the rich UI
  advances no time and creates no second runtime (0 -> 1 federation).
- V02 Frame A: exactly six canonical sub-lines, all live, independent state, one parent
  run.
- V03 Frame B: 12 accepted positions per frame; visible WIP motion (PRE-ASSY -> AP01 ->
  AP02 -> AP03 -> AP04); AP04 JOIN creates MTR-0001 (<- SSO2-0001 + RSO2-0001) which
  then travels AP05 -> AP06 -> AP07 -> AP08; rendered == canonical positions[] truth.
- V04 inspector/quality/genealogy read models + retained OPS-03/OPS-04 thin bindings;
  sub-line selection is presentation-only.
- V05 lifecycle: STEP same session; RESET same run_id + fresh baseline for all six
  lines; NEW ATTEMPT fresh run_id; REPLAY deterministic; SH-WTP switch isolation.
- V06 six-line independence visible: hold ASSY-SL03 -> Frame A SL03 frozen while five
  continue; Frame B SL03 frozen vs SL01 advanced; release resumes SL03.
- V07 browser/visual sanity at the live server: Frame A six live cards, Frame B 12
  stations + conveyor + WIP tokens, repeated rich-page STEP moves WIPs on the SAME
  session (only /assy-demo/step + /assy-demo/sub-line/* calls), scenario pinned, no page
  overflow. Defects: 0 BLOCKER, 0 MAJOR, 1 MINOR (one 404 console error for the optional
  /vnext/runs/current context fetch), 3 OBSERVATION (viewport-scale pan/zoom, harness
  pointer-interception artefact, no JS exceptions).

Evidence: .ai-harness/sa-review/evidence/VF-vNEXT-R2V/ (01..06 {md,json},
07-visual-sanity.md, generate_evidence.py, shot-frame-a.png, shot-frame-b.png)

Report: .ai-harness/sa-review/reports/VF-vNEXT-R2V.md

Not validated here (out of scope, unchanged): R3 Observation/MES/output write paths,
R4 jam/recover/run-to-terminal/scenario mutation, OEE, gateway/OPC/MQTT, SH-WTP.

Authority unchanged: vf_runtime_authorization NOT_AUTHORIZED;
site_authorized_execution NOT_AUTHORIZED; whole_plant_runtime NOT_AUTHORIZED /
NOT_IMPLEMENTED.
