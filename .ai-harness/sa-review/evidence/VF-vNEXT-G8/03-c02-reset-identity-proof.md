# VF-vNEXT-G8-C02 · Evidence 03 — Deterministic reset identity proof

SA review `5557757350` of head `9439a9e464467bfca504bad9384608ac20590502`:
G8 was not accepted because the accepted test
`tests/test_demo_composition.py::TestReset::test_reset_creates_fresh_configs`
(and its sibling `test_reset_creates_fresh_runtimes`) captured only integer
`id()` values, let the old objects become unreachable before `comp.reset()`, and
compared address-based ids — CPython may reuse a freed address, so the
`isdisjoint` assertion could fail even though reset created genuinely fresh
objects. This correction is TEST-ONLY.

## Fix (test-only, no production/semantics change)
In `tests/test_demo_composition.py`, both reset identity tests now:
1. keep STRONG references to the pre-reset runtime/config objects for the whole
   test (a dict keyed by sub-line id), so the old objects are never garbage
   collected and their addresses cannot be recycled;
2. after `comp.reset()`, compare the new objects to the still-alive old objects
   by DIRECT identity (`assert old is not new_runtimes[sid]` /
   `assert old is not new_configs[sid]`).

This proves the intended invariant — reset creates genuinely fresh
runtime/config objects — deterministically by construction, WITHOUT weakening
the assertion and WITHOUT depending on memory-address reuse.

- Files changed: `tests/test_demo_composition.py` (the two reset tests),
  `.ai-harness/tasks/VF-vNEXT-G8.json` (minimum allowlist addition for this one
  test file). No `src/` change; no `AssyDemoComposition`/`AssyLineRuntime`
  edit; no ASSY semantics change.

## Stress proof (requirement 5)
The two corrected tests were stress-run 30× in FRESH subprocess invocations
(`python -m pytest "…::test_reset_creates_fresh_runtimes" "…::test_reset_creates_fresh_configs"`),
each with a different process heap state: **runs=30 failures=0**.
`tests/test_demo_composition.py` as a whole: 49 passed.

## Complete canonical G8 baseline (requirement 6/7/8)
Command: `python .ai-harness/regression/run_vnext_baseline.py --json-output
.ai-harness/traces/g8c02_baseline.json`
Result: overall **PASS**, failed_groups `[]`:
- g1 32, g2 36, g3 328, g4 56, g5 26, g6 31, g7 50, ui_api_dashboard 134,
  assy_oracle **354**, continuous_compressor 61, g8_cross_gate_invariants 12,
  full_suite **1968 passed** (0 failures);
- checks_compile PASS; checks_static_lint_type PASS (truthful: no static tool);
  checks_changed_files PASS (11 files); checks_preflight PASS.

Full suite green (1968). Compile/static/changed-files/preflight green.

## Confirmation
- No `src/` change; no architecture/runtime semantics change; no G9/G10.
- The baseline is now deterministic by construction (no known intermittent
  member test remains).
