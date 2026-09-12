# VF-vNEXT-G9-C02 · Evidence 03 — semantic SHA pin validation for known artifacts

SA review `5560021077` of head `de7d4e545c1349a4dc21aaba8586cd6c9abd3fcc`: for a
known pinned artifact, the accepted semantic identity SHA must be validated as
well as the artifact hash (a non-empty but wrong semantic SHA must fail closed).

## Fix (bounded; G9 validation only)
`validation.py`: `KNOWN_SEMANTIC_ARTIFACTS` now maps
`(artifact_id, version) -> (accepted artifact_hash, accepted semantic_identity_sha)`.
For a known artifact/version, BOTH pins are checked offline (no PIM fetch):
- artifact hash mismatch → fail closed ("artifact hash mismatch ...");
- non-empty semantic identity SHA mismatch → fail closed
  ("semantic identity SHA mismatch for <artifact>@<version>: supplied ... != accepted ...").

The exact SH-WTP pin is preserved:
- artifact_id `SHW-PIM-VF-EXPORT-v0.1`, version `v0.1`;
- artifact_hash `ea3361a4aca9d25927a4a76c792f3af184e1aabb`;
- semantic_identity_sha `f23f3c4614f50a1a2e3805f7e887433feb934915`.

Unknown generic artifacts remain valid when they carry their own explicit
non-empty pins (no future-artifact pre-registration requirement).

## Direct regression added
`tests/test_semantic_binding.py::TestSourceIdentity::test_semantic_sha_mismatch_fails_closed_for_known_artifact`
— exact SH-WTP artifact/version, correct artifact hash, wrong non-empty semantic
SHA → `validate_binding` fails with the explicit "semantic identity SHA mismatch"
diagnostic. (G9 tests 18 total.)

## Re-run results
- G9 semantic-binding tests: **18 passed**.
- G7 run-control: 50 passed (unchanged).
- COMPLETE canonical vNext baseline at the C02 head: overall **PASS**,
  failed_groups `[]` — g1 32; g2 36; g3 328; g4 56; g5 26; g6 31; g7 50;
  ui_api_dashboard 134; assy_oracle 354; continuous_compressor 61; g8 12; g9 18;
  full_suite **1986 passed** (0 failures);
  checks_compile / checks_static_lint_type / checks_changed_files (15) /
  checks_preflight all PASS.
- Compile exit 0; preflight PRECHECK PASSED; verify_changed_files PASSED (15).

## Confirmation
No PIM fetch/write; no compatibility-semantics change; no NOT_AUTHORIZED
override; no G2 authority change; no G7 lifecycle redesign; no G10; no SH-WTP
runtime/topology/physics/control.
