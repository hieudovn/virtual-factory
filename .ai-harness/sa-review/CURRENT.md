# SA REVIEW INBOX

Task: SHW-PIM-EXPORT-01
Status: READY FOR SA REVIEW (authoritative PIM source resolved + SH WTP
semantic export pinned as immutable reference)

Gate type:
Cross-project dependency resolution / PIM export handoff

Authoritative VF baseline:
main @ d64f853ae37578f8b8b7afa8e0cc5de4db9bbae6 (post PR #32 merge)

Authoritative PIM source (PROVEN):
hieudovn/plant-intelligence-model @ main d241da61a6166df8359f892141609add75aec5b5

Pinned SH WTP export (reference-only; content stays PIM-owned):
- examples/song-hong-wtp/model_fixture/model.yaml (105 entities / 121 rels /
  4 contracts) + gap_register.yaml (12 gaps GAP-SHW-001..012)
- examples/song-hong-wtp/contracts/vf_readiness_contract_draft.yaml
  (CONTRACT-SHW-VF-READINESS-DRAFT-v0.1; GenericProjection; producer PIM,
  consumer VF-Planning; NOT a runtime VF package)
- plant_config/canonical_id_rules.md + contract_principles.md +
  evidence_policy.yaml (PIM-owned ID scheme + vocabularies)
- seed/signal_catalog_ph02.yaml + first_vf_readiness_slice_t106_t108_t110.yaml
- vf_readiness/vf_object_class_mapping.yaml + vf_readiness_profile_schema_draft.yaml
- Pin: git SHA d241da61 + per-file SHA-256 (see evidence/03)

Honest status:
- No SourceMapped / no SiteVerified items; GAP-SHW-001 blocks SourceMapped.
- Fidelity: LogicalOnly / FirstOrderReady only.
- PIM-side gates SHW-PIM-PH03 and SHW-CONTRACT-PH01 are "SA review required /
  not CLOSED" (PIM side); VF compatibility.status = review_required accordingly.
- model.yaml top-level source_model_version = SHW-PH02-v0.1 vs contract draft
  SHW-PH03-v0.1 (PIM-side version-string inconsistency noted, evidence/04).

Production code changed: NO
PH01 started: NO
VF workspace loader / binding validation implemented: NO
CORE provenance gate started: NO
No canonical IDs / vocabularies / site truth invented by VF: YES

Report:
.ai-harness/sa-review/reports/SHW-PIM-EXPORT-01.md

Evidence:
.ai-harness/sa-review/evidence/SHW-PIM-EXPORT-01/ (5 files: 01…05)



