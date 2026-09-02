# 02 — Export Artifact Inventory

Inventory of the PIM-side SH WTP semantic export package, as it exists in the
authoritative PIM repo at the pinned SHA. This is an **inventory of references**
— the VF repo does not become the semantic source of truth; the content remains
PIM-owned and is consumed read-only.

## 2.1 Export package boundary

The export package is the PIM repo directory:

```text
examples/song-hong-wtp/
```

Referenced from PIM `main` @ `d241da61a6166df8359f892141609add75aec5b5`.

## 2.2 Primary semantic model fixture

| Artifact (PIM path) | Role | Verified content |
|---|---|---|
| `examples/song-hong-wtp/model_fixture/model.yaml` | Canonical semantic model (harness target) | 105 entities / 121 relationships / 4 contracts; top-level `model_version: 1`, `evidence_policy_version: "0.1"` |
| `examples/song-hong-wtp/model_fixture/gap_register.yaml` | Explicit gap register (harness WARNING linkage) | 12 gaps (GAP-SHW-001 … GAP-SHW-012) |

Note (recorded honestly): the top-level `source_model_version` field in
`model.yaml` is `SHW-PH02-v0.1` (line 30), while `SHW-PIM-PH03-closeout-report.md`
describes `model.yaml` as "UPDATED — plant-wide skeleton" (105 entities). The
git SHA + per-file SHA-256 pin unambiguously identifies the exact bytes; the
internal version-string inconsistency is a PIM-side observation (see evidence 04,
§4.5), not a VF-side resolution target.

## 2.3 PIM → VF handoff contract

| Artifact (PIM path) | Role |
|---|---|
| `examples/song-hong-wtp/contracts/vf_readiness_contract_draft.yaml` | PIM→VF planning/reference contract. `contract_id: CONTRACT-SHW-VF-READINESS-DRAFT-v0.1`, `contract_type: GenericProjection`, `schema_version: 0.1.0`, `producer: PIM`, `consumer: VF-Planning`, `source_model_version: SHW-PH03-v0.1`. Explicit statement: "This is NOT a runtime VF package." |

It carries: `plant_id`, `model_version`, `slice_id`, `included_units`
(UNIT-SHW-L1-T106, UNIT-SHW-L1-T108, UNIT-SHW-WASH-T110), `vf_object_catalog`
(canonical assets with `vf_object_type`, `vf_model_family_hint`,
`fidelity_readiness`, `required_parameters`, `optional_parameters`,
`missing_parameters`, `readiness_gaps`, `evidence_status`), and
`included_signals` (canonical signals with `signal_role` + `evidence_status`).

## 2.4 Identity / classification / vocabulary sources (PIM-owned)

| Artifact (PIM path) | Role |
|---|---|
| `examples/song-hong-wtp/plant_config/canonical_id_rules.md` | Canonical ID scheme `{CLASS}-SHW-{SCOPE}-{SEQUENCE}` (PIM-owned; no new scheme needed by VF) |
| `examples/song-hong-wtp/plant_config/contract_principles.md` | Contract versioning/compatibility principles ("VF package must be generated from PIM, not manually authored") |
| `examples/song-hong-wtp/plant_config/evidence_policy.yaml` | Evidence vocabulary (`DocumentConfirmed/PatternInferred/IndustryExpected/Expected/SourceMapped/SiteVerified/Rejected`; epistemic states; truth domains; promotion rules) |
| `examples/song-hong-wtp/plant_config/model_scope.md`, `system_boundary.md`, `responsibility_matrix.md` | Scope/boundary/responsibility (PIM-owned) |

## 2.5 Signal / slice catalogs (PIM-owned)

| Artifact (PIM path) | Role |
|---|---|
| `examples/song-hong-wtp/seed/signal_catalog_ph02.yaml` | Expected signal catalog (PH02) |
| `examples/song-hong-wtp/seed/first_vf_readiness_slice_t106_t108_t110.yaml` | First VF-readiness slice seed (T106/T108/T110) |
| `examples/song-hong-wtp/seed/plant_wide_skeleton_ph03.yaml` | Plant-wide skeleton (PH03 review artifact) |
| `examples/song-hong-wtp/seed/plant_skeleton.yaml` | Plant skeleton (PH01) |

## 2.6 VF-readiness mapping (PIM-side advisory)

| Artifact (PIM path) | Role |
|---|---|
| `examples/song-hong-wtp/vf_readiness/vf_object_class_mapping.yaml` | PIM-side advisory object-class → VF model-family mapping (GAP-SHW-011: draft, to be validated against a real VF model library) |
| `examples/song-hong-wtp/vf_readiness/vf_readiness_profile_schema_draft.yaml` | VF Readiness Profile schema draft (advisory; fidelity enum; `missing_parameters` must be explicit) |
| `examples/song-hong-wtp/vf_readiness/readiness_level_policy.md`, `missing_parameter_policy.md` | Readiness + missing-parameter policies |

## 2.7 Cross-reference (VF-2 schema, also PIM-owned)

`docs/vf2-simulation-package-schema.md` exists in the PIM repo (verified present).
This is the canonical VF-2 package schema referenced by the VF repo — PIM-owned,
not VF-authored.

## 2.8 Coverage vs Issue #33 required export content

| Required export content | Satisfied by (PIM-owned) |
|---|---|
| canonical objects/assets | `model.yaml` entities + `vf_object_catalog` |
| canonical signals | `included_signals` + `signal_catalog_ph02.yaml` |
| object↔signal relationships | `model.yaml` relationships (121) |
| classification/type | `entity_type`, `asset_class`, `asset_subclass` |
| orthogonal state dimensions + vocabularies (where established) | `fidelity_readiness`, `evidence_status`, `epistemic_state`, `truth_domain` enums |
| signal→state semantics (where established) | `signal_role` (measurement/control) |
| observability (where established) | `evidence_status` (Expected / DocumentConfirmed / IndustryExpected / PatternInferred) |
| evidence/source maturity (where established) | `evidence_status` + `evidence_policy.yaml` promotion rules; explicitly NO SourceMapped / NO SiteVerified |
| known/missing/review-required parameters + readiness gaps | `required_parameters`/`optional_parameters`/`missing_parameters`/`readiness_gaps` + `gap_register.yaml` (12 gaps) |
| artifact identity/version/content hash | `contract_id`, `schema_version`, `source_model_version` + git SHA + per-file SHA-256 (evidence 03) |
