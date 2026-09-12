# VF-vNEXT-G9-C01 · Evidence 02 — required-target fail-closed, semantic SHA, reusable baseline

SA review `5559907951` of head `ab0b39a01f20da4be2419dd35d4ab11afe13f912` found
three bounded corrections. All are TEST/HARNESS/G9-scope only; no production
semantics beyond the G9 fail-closed rules; no G2 authority change; no G7
lifecycle redesign; no G10.

## 1. Required-mode mapping: canonical target is mandatory (fail-open hole fixed)
`validation.py`: in `BindingMode.REQUIRED`, EVERY mapping must now have exactly
one non-empty `canonical_id`, independent of `published` / `canonical_claimed`.
Duplicate-local-id / multiple-target ambiguity remains fail-closed. The optional
simulation-only rule (local/unmapped allowed only when explicitly non-published
and non-canonical) is unchanged. Regression added for the exact case
(`status=accepted`, `canonical_id=None`, `published=False`,
`canonical_claimed=False` → fails).

## 2. Semantic SHA required before admission/consume (no fabricated SHA)
`validation.py`: `semantic_identity_sha` is now a required source pin for
`BindingMode.REQUIRED`. A required binding without it fails validation, so
`SemanticAdmissionGate` raises before `start()` and `RunRecord.semantic_contract_sha`
stays `None` (no fabricated provenance). Test added: missing SHA fails closed
before start with zero bridge advancement and no provenance written.

## 3. Canonical baseline reuse (no second script; gate context seam)
`run_vnext_baseline.py` now resolves the current-gate context from a single
manifest top-level `gate` object (`task_contract`, `changed_files_base`) and
supports `{task_contract}` substitution in command groups. The manifest
`checks_changed_files` / `checks_preflight` use `{task_contract}` and the
gate-level `changed_files_base` instead of hard-coded G8 values. The SAME
canonical entrypoint now runs the complete baseline on the current authorized
gate (G9 here) — reusable for G10+ by updating the `gate` context. All G1–G8
groups preserved exactly; `g9_semantic_binding` remains additive.

## Complete canonical vNext baseline at the G9-C01 head
Command: `python .ai-harness/regression/run_vnext_baseline.py --json-output
.ai-harness/traces/g9c01_baseline.json` — overall **PASS**, failed_groups `[]`:
- g1 32; g2 36; g3 328; g4 56; g5 26; g6 31; g7 run-control 50; ui_api_dashboard
  134; assy_oracle 354; continuous_compressor 61; g8_cross_gate_invariants 12;
  g9_semantic_binding **17**; full_suite **1985 passed** (0 failures);
- checks_compile PASS; checks_static_lint_type PASS (truthful: no static tool);
  checks_changed_files PASS (14 files); checks_preflight PASS.

## Harness
- Compile: `python -m compileall -q src tests .ai-harness/regression
  .ai-harness/scripts` exit 0 (no configured ruff/mypy/black — truthful).
- Preflight (G9 contract): PASSED. Changed-file validation: PASSED (14 files).

## Confirmation
No decision that `compatible_with_constraints` == runtime-compatible; no
`NOT_AUTHORIZED` override; no PIM writes; no G2 authority change; no G7
lifecycle redesign; no SH-WTP runtime/topology/physics/control; no G10.
