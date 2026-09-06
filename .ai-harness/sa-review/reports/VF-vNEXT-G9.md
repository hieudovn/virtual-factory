# VF-vNEXT-G9 — Semantic Binding vNext

| Field | Value |
|---|---|
| Task ID | `VF-vNEXT-G9` (GitHub Issue #54) |
| Program | Implementation phase (G9; only authorized gate after G8) |
| Required base (branch) | `e75fa95259f1b68e465c546e2e4dbc6b24e9a76d` (accepted G8-C02 head) |
| Branch | `feature/vf-vnext-g9` |
| Production base (`origin/main`) | `f5261c8ca18cd4e01779c0274b55270ba028b4e5` |
| Model | Pro |
| G10+ started | **NO** |

## 1. Objective

Implement the smallest generic Semantic Binding vNext seam so a VF Workspace can
validate and consume an explicitly pinned external semantic contract without
owning/rewriting PIM truth — preserving PIM as canonical semantic authority, VF
local ids as local, binding as an explicit local→canonical relationship,
fail-closed required-mode rules, separate compatibility vs runtime
authorization, pre-run admission (zero domain advancement), and exact
provenance threading of the consumed contract version/SHA.

## 2. Implementation (additive)

- `src/virtual_factory/semantic/binding.py` — immutable model + enums
  (`SemanticSourcePin`, `LocalCanonicalMapping`, `SemanticBinding`; modes
  required/optional/none; compatibility vs runtime authorization separate).
- `src/virtual_factory/semantic/validation.py` — deterministic fail-closed
  validator (pins, exact hash baseline, mapping cardinality/status, no
  name-only/heuristic).
- `src/virtual_factory/semantic/admission.py` — `SemanticAdmissionGate` +
  `SemanticAdmissionError` (validation AND runtime authorization; compatibility
  never admits; consume threads version/SHA on success).
- `src/virtual_factory/semantic/loader.py` — offline deterministic pinned
  artifact loader (`load_binding_artifact`, `binding_from_dict`).
- `src/virtual_factory/runcontrol/lifecycle.py` — bounded, additive pre-run
  admission seam: optional `admission` callable invoked in `start()`/`step()`
  before any advance; `RunRecord` carries `semantic_contract_version`/
  `semantic_contract_sha` (None when not consumed). G7 semantics unchanged
  (default no-op).
- `.ai-harness/regression/vnext_baseline_manifest.json` — minimally updated to
  add the additive `g9_semantic_binding` pytest group (no prior group weakened).

## 3. Frozen distinctions (NOT changed)

- PIM canonical ids are read-only references; VF never renames/repairs them.
- `compatible_with_constraints` ≠ unconditional `compatible`; never implies
  runtime admission.
- `vf_runtime_authorization: NOT_AUTHORIZED` for SH-WTP is not overridden.
- No name-based/heuristic fallback; no dynamic main/latest fetch; no fabricated
  semantic provenance when no contract is consumed.

## 4. Test / regression results

| Suite | Result |
|---|---|
| New G9 semantic-binding tests | **16 passed** |
| G7 run-control | **50 passed** |
| Full repository suite | **1984 passed** (0 failures) |
| Canonical baseline g9 group (entrypoint) | **PASS** (16) |
| checks_compile / checks_static_lint_type | **PASS** (truthful: no static tool) |
| Compile check | PASS |
| Preflight (G9 contract) | PASSED |
| Changed-file validation | PASSED |

## 5. STOP-condition assessment

None triggered: no decision that `compatible_with_constraints` equals
unconditional compatible; no `NOT_AUTHORIZED` override; no PIM canonical id
generation/rename/repair; no name-based/heuristic binding; no runtime
main/latest fetch; G2 authority unchanged; G7 lifecycle not redesigned; no
SH-WTP runtime/topology/physics/control; no cross-workspace/supply-chain; no
G10.

## 6. Acceptance (Issue #54 criteria)

| Criterion | Result |
|---|---|
| Generic fail-closed semantic-binding model + validator | PASS |
| Deterministic pinned artifact/loader seam (offline) | PASS |
| Bounded run-control admission seam (zero domain advancement) | PASS |
| Consumed contract version/SHA thread exactly; no fabrication when absent | PASS |
| Compatibility vs runtime authorization separate (SH-WTP frozen) | PASS |
| New G9 tests green | PASS |
| TIPA/continuous, G8 baseline, full suite green | PASS |
| No G10 implementation | PASS |
| Working tree clean and branch/head pushed | PASS (after push) |

## 7. Evidence

`.ai-harness/sa-review/evidence/VF-vNEXT-G9/` — `01-semantic-binding-model.md`.

## 8. Final status

```text
VF-vNEXT-G9 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. G10 is NOT started.
