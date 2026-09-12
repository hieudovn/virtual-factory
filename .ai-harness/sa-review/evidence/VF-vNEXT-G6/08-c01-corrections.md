# VF-vNEXT-G6-C01 · Evidence 08 — Bind ASSY hierarchy selection to the authoritative /assy-demo/select seam

SA review of exact head `bf2f65646f70aecc040d1bd312990a0a9ce9e376`
(comment `5544316295`) found that `assy_context.js` handled executable
ASSY-SLxx hierarchy selection by directly mutating the private client field
`ctrl._selectedSubLineId` / `ctrl._refreshCardStyles()` — a second UI-only
selection authority that never reached the backend
`POST /assy-demo/select` surface used by step/command/detail. Fixed.

## C01 — hierarchy selection updates the same existing ASSY selection authority

`src/virtual_factory/ui/static/assy_context.js` (additive seam only;
`assy_demo.js` NOT modified):
- An executable `ASSY-SLxx` hierarchy selection is forwarded to the EXISTING
  backend authority `POST /assy-demo/select` with body `{ sub_line_id: <leaf> }`.
  That surface only sets the controller's selected context
  (`DemoController.select_sub_line` → `AssyDemoComposition.select_sub_line`); it
  does NOT reset/reconstruct/step the runtime and adds no new endpoint or G7
  orchestration semantics.
- Only AFTER the backend accepts the selection (response ok) does the seam
  update the structural breadcrumb and the existing presentation card selection
  (`ctrl._selectedSubLineId` + `_refreshCardStyles`). Fail-safe: on a failed
  request the UI never commits a breadcrumb/card selection that the backend
  authority does not hold.
- Workspace / container (and non-selectable executable) selection is
  structural-context-only and NEVER calls `/assy-demo/select`
  (container-only implies no execution).
- The only `/assy-demo/select` fetch in the seam is guarded by
  `kind === 'executable'` and the `/^ASSY-SL\d+$/` leaf pattern.

## Mandatory tests (evidence 07)
1. `test_static_seam_binds_to_assy_select_authority` — the seam calls
   `POST /assy-demo/select` with `sub_line_id` exactly once; fail-safe ordering
   (`if (!res.ok)` precedes the breadcrumb/card commit); no
   reset/step/reconstruction calls.
2. `test_structural_sub_line_path_maps_to_select_id` — canonical
   `TIPA/ASSY/ASSY-SLxx` leaf equals the select seam's `sub_line_id`.
3. `test_select_endpoint_accepts_hierarchy_sub_line_and_fails_closed` —
   `POST /assy-demo/select {ASSY-SL03}` → 200 snapshot `sub_line_id ==
   ASSY-SL03`; unknown id → 404; missing → 400 (failed backend selection never
   commits).
4. `test_workspace_container_selection_does_not_invoke_select` — Python
   container selection implies no execution
   (`executable_controls_implied=False`); the seam routes only executable
   ASSY-SL leaves to the select fetch.
5. `test_select_is_non_mutating_controller_level` — selecting a sub-line (away
   and back) leaves every runtime's simulation time / dwell number / WIP ids /
   lifecycle states unchanged (no reset/reconstruct/step).
6. Existing ASSY selection/non-mutation regressions green (UI/API + S04B gating
   incl. `test_ops03_interaction` 134 passed) plus full G6/G5/G4/G1-G3/ASSY/
   continuous/full regressions (evidence 07).

## Regression (re-run)
New G6 tests 31 passed (was 26; +5 C01); UI/API + S04B gating 134; G5 26;
G4 56; G1 32; G2 36; G3 328; ASSY oracle 354; continuous 61; full suite
**1906 passed** (0 failures). Compile PASS.

## Preserved (unchanged)
Hierarchy/context projection; domain-agnostic navigator/breadcrumb; ASSY
domain rendering (assy_demo.js) and continuous behavior untouched; container/
workspace structural-context-only; no G7+; no new UX/architecture decision.
