# SA REVIEW INBOX

Task: VF-vNEXT-G9
Status: READY FOR SA REVIEW (Semantic Binding vNext)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH CLOSED; only authorized gate after G8)
Prerequisite: Issue #53 accepted as completed; G1-G8 contracts authoritative

Gate type:
Implementation gate — Semantic Binding vNext (G9), per Issue #54

Architecture baseline:
ARCH-01..06 accepted; G1-G8 contracts authoritative
Required base (branch point): e75fa95259f1b68e465c546e2e4dbc6b24e9a76d (accepted G8-C02 head)
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive):
- src/virtual_factory/semantic/ — generic Semantic Binding vNext model +
  fail-closed validator + admission gate + offline pinned loader:
  * binding.py: BindingMode (required|optional|none); CompatibilityDecision
    (compatible|compatible_with_constraints|not_compatible); RuntimeAuthorization
    (NOT_AUTHORIZED|AUTHORIZED); MappingStatus (accepted|unmapped|review_required);
    SemanticSourcePin (producer_id/artifact_id/version/artifact_hash/
    semantic_identity_sha/source_model_version); LocalCanonicalMapping
    (local_id + canonical_id + status + published + canonical_claimed +
    explicit); SemanticBinding. Local ids are NEVER renamed to canonical ids
    (explicit relationship, not a rename).
  * validation.py: deterministic fail-closed rules — required source pins
    present; exact accepted hash baseline (mismatch fails); name-only
    (explicit=false) rejected; required mappings resolve exactly one canonical
    target (zero/multiple/ambiguous/unmapped/review_required fail); optional
    local-only allowed only non-published/non-canonical; optional
    canonical/published claim without target fails. KNOWN_SEMANTIC_ARTIFACTS is
    a static offline pin registry (no main/latest lookup).
  * admission.py: SemanticAdmissionGate (assess/assert_admittable/consume) +
    SemanticAdmissionError. compatibility is NOT consulted for admission —
    compatible_with_constraints never authorizes; NOT_AUTHORIZED always fails
    closed. consume() threads semantic_contract_version/sha on success only.
  * loader.py: load_binding_artifact/binding_from_dict (deterministic, offline).
- src/virtual_factory/runcontrol/lifecycle.py (bounded additive seam): optional
  admission callable invoked in start()/step() BEFORE any advance; RunRecord
  carries semantic_contract_version/semantic_contract_sha (None == not
  consumed). G7 state machine unchanged (default no-op).
- .ai-harness/regression/vnext_baseline_manifest.json: minimally updated ONLY by
  adding the additive g9_semantic_binding pytest group (no prior group weakened).
- tests/test_semantic_binding.py (16 tests) + tests/fixtures/semantic/
  song_hong_wtp_export_v0_1.yaml (pinned SH-WTP reference fixture).

Frozen distinctions preserved:
- PIM = canonical semantic authority (read-only); VF = runtime/simulation
  authority; canonical ids referenced, never generated/renamed/repaired.
- compatible_with_constraints != unconditional compatible; never implies
  runtime admission.
- vf_runtime_authorization: NOT_AUTHORIZED (SH-WTP) is NOT overridden.
- No name-based/heuristic fallback; no dynamic main/latest; no fabricated
  semantic provenance when no contract consumed.

SH-WTP reference proof (evidence 01): fixture pins package SHW-PIM-VF-EXPORT-v0.1
/ v0.1 / SHW-PH03-v0.1 / semantic_identity_sha f23f3c... / artifact_hash
ea3361a4... with compatibility compatible_with_constraints + runtime_authorization
NOT_AUTHORIZED. Validation passes (pins recognized); admission raises; lifecycle
cannot start (run stays CREATED, zero advancement, no fabricated provenance).

Test / regression results (evidence 01):
- New G9 semantic-binding tests: 16 passed.
- G7 run-control: 50 passed (unchanged).
- Full repository suite: 1984 passed (0 failures).
- Canonical G8 baseline: green at its accepted head (e75fa95) + minimal additive
  g9_semantic_binding group; entrypoint g9_semantic_binding PASS (16) +
  checks_compile + checks_static_lint_type PASS.
- Compile check PASS; no configured ruff/mypy/black (truthful).
- Preflight PASSED (G9 contract); verify_changed_files PASSED.

Deferred (NOT implemented): G10 SH-WTP runtime/topology/physics/control, full
replay browser/editor/history subsystem, scenario editor, universal reset/
synchronization policy.

STOP conditions: none triggered.

G10 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G9.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G9/ (01 semantic-binding model + admission)






