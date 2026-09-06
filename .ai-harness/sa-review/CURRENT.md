# SA REVIEW INBOX

Task: VF-vNEXT-G9-C02
Status: READY FOR SA REVIEW (Semantic Binding vNext — C02 semantic SHA pin validation)
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
- .ai-harness/regression/vnext_baseline_manifest.json + run_vnext_baseline.py:
  minimally updated ONLY by adding the additive g9_semantic_binding pytest group
  (no prior group weakened). C01: top-level `gate` context (task_contract /
  changed_files_base) + {task_contract} substitution so the SAME canonical
  entrypoint runs the current authorized gate (changed-files/preflight use the
  current task/branch/base, not hard-coded G8).
- C01 (SA 5559907951): REQUIRED mappings now require exactly one non-empty
  canonical target independent of published/canonical_claimed; semantic_identity_sha
  is a required pin for admittable bindings (no fabricated SHA); G9 tests 16 -> 17.
- C02 (SA 5560021077): KNOWN_SEMANTIC_ARTIFACTS pins BOTH accepted artifact hash
  and accepted semantic identity SHA; known artifact with non-empty-but-wrong
  semantic SHA fails closed with explicit diagnostic; unknown generic artifacts
  remain valid with explicit non-empty pins; exact SH-WTP pins preserved; G9
  tests 17 -> 18.
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

Test / regression results (evidence 01/02/03):
- New G9 semantic-binding tests: 18 passed.
- G7 run-control: 50 passed (unchanged).
- COMPLETE canonical vNext baseline at C02 head: overall PASS (all groups) —
  g1 32; g2 36; g3 328; g4 56; g5 26; g6 31; g7 50; ui_api_dashboard 134;
  assy_oracle 354; continuous_compressor 61; g8 12; g9 18; full_suite 1986
  passed (0 failures); checks_compile/static/changed_files(15)/preflight PASS.
- Compile check PASS; no configured ruff/mypy/black (truthful).
- Preflight PASSED (G9 contract); verify_changed_files PASSED (15 files).

Deferred (NOT implemented): G10 SH-WTP runtime/topology/physics/control, full
replay browser/editor/history subsystem, scenario editor, universal reset/
synchronization policy.

STOP conditions: none triggered.

G10 started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G9.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G9/ (01 semantic-binding model + admission;
02 C01 corrections — required-target fail-closed, semantic SHA, reusable baseline;
03 C02 semantic SHA pin validation for known artifacts)






