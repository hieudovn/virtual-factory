# VF-vNEXT-G9 · Evidence 01 — Semantic Binding vNext model + admission

Gate: GitHub Issue #54. PIM stays the canonical semantic authority (read-only
reference); VF owns runtime/simulation identity; binding is an explicit
local→canonical relationship; required bindings fail closed; semantic
compatibility and runtime authorization stay separate; admission fails before
domain advancement; consumed contract identity threads into G2 provenance.

## Base / head
- Required base (G8 accepted head): `e75fa95259f1b68e465c546e2e4dbc6b24e9a76d`
- Branch: `feature/vf-vnext-g9` (from the required base)
- Production base (`origin/main`): `f5261c8ca18cd4e01779c0274b55270ba028b4e5`

## Implementation (additive)
`src/virtual_factory/semantic/` (new package):
- `binding.py` — immutable value objects: `BindingMode` (`required|optional|none`),
  `CompatibilityDecision` (`compatible|compatible_with_constraints|not_compatible`),
  `RuntimeAuthorization` (`NOT_AUTHORIZED|AUTHORIZED`), `MappingStatus`
  (`accepted|unmapped|review_required`), `SemanticSourcePin` (producer_id /
  artifact_id / version / artifact_hash / semantic_identity_sha /
  source_model_version), `LocalCanonicalMapping` (local_id + canonical_id +
  status + published + canonical_claimed + explicit), `SemanticBinding`.
  Local ids are NEVER renamed to canonical ids (relationship, not rename).
- `validation.py` — deterministic fail-closed validation: required-mode source
  pins (producer/artifact/version/hash) required; known-artifact exact-hash
  baseline checked (mismatch fails); name-only (`explicit=false`) rejected;
  required mappings must resolve exactly one canonical target (zero target /
  multiple/ambiguous / `unmapped` / `review_required` fail); optional local-only
  mappings allowed only when explicitly non-published and non-canonical;
  optional canonical/published claim without a target fails.
  `KNOWN_SEMANTIC_ARTIFACTS` is a static offline pin registry (never a mutable
  `main/latest` lookup).
- `admission.py` — `SemanticAdmissionGate`: `assess()` (validation),
  `assert_admittable()` (validation AND runtime authorization; `compatibility`
  is deliberately NOT consulted — `compatible_with_constraints` never implies
  admission), `consume(record)` (threads `semantic_contract_version` /
  `semantic_contract_sha` on success only). `SemanticAdmissionError` is a
  `RunLifecycleError`.
- `loader.py` — `load_binding_artifact(path)` + `binding_from_dict(dict)`;
  deterministic, offline, pinned; no network, no dynamic main/latest.

`src/virtual_factory/runcontrol/lifecycle.py` (bounded G9 seam, additive):
- `RunRecord` gains `semantic_contract_version` / `semantic_contract_sha`
  (None == not consumed; never fabricated) and serializes them.
- `RunLifecycleService` accepts an optional `admission` callable (default
  no-op → G7 behavior unchanged); `start()` and `step()` invoke it BEFORE any
  state change / bridge advancement, so semantic admission failure leaves
  runtime/domain state unadvanced.

## Frozen distinctions preserved
- `compatible_with_constraints` ≠ unconditional `compatible`; it does NOT admit
  runtime execution.
- `vf_runtime_authorization: NOT_AUTHORIZED` is NOT overridden; SH-WTP cannot
  start/advance.
- PIM canonical ids are referenced read-only; VF never generates/renames/repairs
  them; no name-based/heuristic fallback; no fabricated semantic provenance.

## Exact SH-WTP reference proof
Fixture `tests/fixtures/semantic/song_hong_wtp_export_v0_1.yaml` records the
exact issued pins (package `SHW-PIM-VF-EXPORT-v0.1`, version `v0.1`, model
`SHW-PH03-v0.1`, semantic_identity_sha `f23f3c4614f50a1a2e3805f7e887433feb934915`,
artifact_hash baseline `ea3361a4aca9d25927a4a76c792f3af184e1aabb`), with
`compatibility: compatible_with_constraints` and
`runtime_authorization: NOT_AUTHORIZED`. Tests prove: the binding validates
structurally (exact pins recognized) but `assert_admittable()` raises
(NOT_AUTHORIZED), and a lifecycle service with that gate cannot `start` — the
run stays CREATED with zero bridge advancement and no fabricated semantic
provenance.

## Tests (tests/test_semantic_binding.py, 16 passed)
Covers Issue #54 required tests 1–15 + 18 (16/17 are the regression suites):
valid required binding deterministic; missing artifact id/version/SHA fail
closed; hash mismatch fail closed; name-only rejected; zero target fails;
multiple/ambiguous targets fail; unmapped/review_required fail; optional
local-only allowed only non-published/non-canonical; optional canonical claim
without target fails; local id not replaced; compatibility vs authorization
separate; SH-WTP NOT_AUTHORIZED cannot start/advance; admission failure → zero
domain advancement; consumed contract threads exact version/SHA into
RunRecord + ProvenanceV2; absent binding fabricates nothing; no G10 (no
SH-WTP runtime in the semantic package).

## Regression results
- New G9 tests: 16 passed.
- G7 run-control: 50 passed (unchanged; admission seam default no-op).
- Full repository suite: **1984 passed** (0 failures).
- Canonical G8 baseline: remains green at its accepted head
  `e75fa95259f1b68e465c546e2e4dbc6b24e9a76d`; the manifest was minimally updated
  ONLY by adding the additive `g9_semantic_binding` pytest group (no prior group
  weakened). The canonical entrypoint runs that group green
  (`g9_semantic_binding` PASS, 16 passed) plus `checks_compile` /
  `checks_static_lint_type` PASS.
- Compile: `python -m compileall -q src tests .ai-harness/regression
  .ai-harness/scripts` exit 0 (no configured ruff/mypy/black — truthful).
- Preflight: PASSED (G9 contract; after commit). Changed-file validation: PASSED.

## Confirmation
- No SH-WTP runtime/topology/physics/control implementation; no G10; no
  cross-workspace integration; no supply-chain semantics.
- G2 provenance authority unchanged; G7 lifecycle state machine unchanged
  (bounded optional pre-run admission seam only).
