# VF-vNEXT-G24-C01 — Workspace Shell reflects selected G22 TIPA RuntimeSession

Gate: `VF-vNEXT-G24-C01` (correction on G24)
Base (required): `899e851167de768669769dfe650bb46e011024d7` (G24 head)
Model: Pro
Status: READY FOR SA REVIEW

## Scope

Make the Workspace Shell's TIPA view reflect the SELECTED G22 TIPA
RuntimeSession — live per-sub-line state/status/key values read from the
selected session's own execution bridge, no second runtime, and `/assy-demo`
explicitly labelled a separate legacy demo runtime.

## Implemented (additive, read-only)

- `src/virtual_factory/runcontrol/assy_bridge.py` —
  `AssyExecutionBridge.sub_line_views()` (read-only per-sub-line projection).
- `src/virtual_factory/ui/workspace_monitor.py` — TIPA view now reads live
  per-sub-line values from `session.record.bridge`; carries
  `runtime_kind: "selected_g22_session"` + session identity; labels
  `/assy-demo` as a separate legacy demo runtime (`shares_session: false`,
  `shares_identity: false`).
- `src/virtual_factory/ui/static/workspace_shell.js` — renders the live
  per-sub-line table and labels the `/assy-demo` link as "(NOT this session)".
- `tests/test_vnext_g24_workspace_ui.py` — C01 tests added (7 new).

## Required semantics proven

- stepping the selected TIPA session changes per-sub-line values/status;
- exactly 6 sub-lines (ASSY-SL01..SL06);
- shell runtime identity is the selected G22 session;
- shell never creates a second runtime;
- `/assy-demo` is not presented as the same session (separate legacy demo
  runtime, identity/state not shared);
- ASSY oracle + full canonical baseline + full suite green.

## Frozen boundaries preserved

No ASSY runtime/UI rewrite; no legacy-controller unification; no G22/G23
semantics change; runcontrol SH-WTP-free; G21 slice untouched; no G25.

## Authority unchanged

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

## Regression

- G24 + C01: 37 passed.
- Full suite: PASS (see trace `g24c01_baseline.json`).
- Complete canonical vNext baseline
  (g1_workspace ... g23_workspace_registry, g24_workspace_shell, full_suite,
  checks_compile, checks_static_lint_type, checks_changed_files,
  checks_preflight): PASS.

## Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G24-C01/01-tipa-live-projection.md`
