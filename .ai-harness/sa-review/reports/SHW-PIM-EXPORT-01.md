# SHW-PIM-EXPORT-01 — Resolve authoritative PIM source and deliver pinned SHW semantic export

| Field | Value |
|---|---|
| Task ID | `SHW-PIM-EXPORT-01` (GitHub Issue #33) |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Cross-project dependency resolution / PIM export handoff |
| Canonical VF baseline | `main` @ `d64f853ae37578f8b8b7afa8e0cc5de4db9bbae6` (post PR #32; recorded at task start) |
| PIM source resolved | `hieudovn/plant-intelligence-model` @ `main` `d241da61…` |
| Production code changed | **NO** (only `.ai-harness/`) |
| PH01 / VF loader / CORE provenance started | **NO** |

## 1. Objective

Resolve the authoritative PIM source-of-truth for SH WTP and, only if proven,
reference the exact pinned SH WTP semantic export package and record immutable
handoff evidence for VF. VF must not invent canonical IDs, vocabularies,
evidence maturity, site truth, or upstream semantic artifacts.

## 2. Priority 1 — source-resolution preflight: RESOLVED

The authoritative PIM source **is proven** (evidence §01):

| Required proof element | Result |
|---|---|
| Repository/system/source location | `https://github.com/hieudovn/plant-intelligence-model` (public) |
| Exact branch/ref/version | `main` @ `d241da61a6166df8359f892141609add75aec5b5` |
| Owner/authority context (PIM-side) | PIM README + `PROJECT_CONSTITUTION.md` = semantic backbone; VF is a listed downstream consumer; "PIM defines. VF simulates." |
| Exact artifact(s) for export | `examples/song-hong-wtp/` (inventory §02) |
| Exact version/hash mechanism | git SHA + per-file SHA-256 (pinning §03) |

No competing PIM source exists; no new canonical-ID scheme or vocabulary needs
to be invented by VF (PIM already owns both — `canonical_id_rules.md`,
`evidence_policy.yaml`).

## 3. STOP-condition assessment

| Stop condition | Assessment |
|---|---|
| Authoritative PIM source cannot be proven | **NOT triggered** — proven (evidence §01) |
| Multiple competing PIM sources with unclear authority | NOT triggered — exactly one PIM repo referenced/used |
| Export requires choosing a new canonical ID scheme | NOT triggered — PIM owns the scheme |
| Required vocabulary/ontology must be invented | NOT triggered — PIM owns the vocabulary |
| Site truth vs source mapping indistinguishable | NOT triggered — explicit `evidence_status`; no SourceMapped/SiteVerified; GAP-SHW-001 blocks SourceMapped |
| Export requires unrelated VF implementation | NOT triggered — reference-only |

**Conclusion: no STOP condition triggered.**

## 4. Export pinned (reference-only)

PIM SH WTP semantic export package `examples/song-hong-wtp/` pinned at git SHA
`d241da61…` with per-file SHA-256 hashes (evidence §03). Primary artifacts:

- `model_fixture/model.yaml` — 105 entities / 121 relationships / 4 contracts.
- `model_fixture/gap_register.yaml` — 12 explicit gaps (GAP-SHW-001…012).
- `contracts/vf_readiness_contract_draft.yaml` — `CONTRACT-SHW-VF-READINESS-DRAFT-v0.1`
  (`GenericProjection`; producer PIM → consumer VF-Planning; not a runtime VF package).
- `plant_config/canonical_id_rules.md`, `contract_principles.md`, `evidence_policy.yaml`.
- `seed/signal_catalog_ph02.yaml`, `seed/first_vf_readiness_slice_t106_t108_t110.yaml`.
- `vf_readiness/vf_object_class_mapping.yaml`, `vf_readiness_profile_schema_draft.yaml`.

All semantic content is PIM-owned; VF records only the reference (evidence §05).

## 5. Gap & maturity (honest)

- No `SourceMapped`, no `SiteVerified` items; source mapping pending
  (GAP-SHW-001), control logic missing (GAP-SHW-002); 10 further gaps explicit.
- Fidelity readiness: `LogicalOnly` / `FirstOrderReady` only.
- PIM-side harness: PASS_WITH_WARNINGS (0 errors, 2 REL-006 warnings).
- PIM-side gate status: `SHW-PIM-PH03` and `SHW-CONTRACT-PH01` are "SA review
  required / not CLOSED" on the PIM side; `model.yaml` top-level
  `source_model_version` is `SHW-PH02-v0.1` while the contract draft declares
  `SHW-PH03-v0.1` (version-string inconsistency noted, evidence §04).

**Consequence:** VF `compatibility.status = review_required` (NOT `compatible`)
until PIM-side gates are SA-accepted and the export version finalized — per the
frozen ALIGN-01 fail-closed contract.

## 6. Acceptance

| Criterion | Result |
|---|---|
| Authoritative PIM source proven | PASS (§01) |
| Exact export artifact/version/hash pinned | PASS (§03) |
| Semantic content from PIM authority, not VF invention | PASS (§02/§05) |
| Missing/unknown/review-required gaps explicit | PASS (§04) |
| VF handoff record immutable/reference-only | PASS (§05) |
| No VF production code changed | PASS |
| PH01 / VF-loader / CORE gates not started | PASS |

## 7. Evidence

`.ai-harness/sa-review/evidence/SHW-PIM-EXPORT-01/` — 5 files (01…05).

## 8. Final status

```text
SHW-PIM-EXPORT-01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. The PIM-side gates
(SHW-PIM-PH03 / SHW-CONTRACT-PH01) remain SA-review-pending on the PIM side;
VF compatibility status is `review_required` accordingly. PH01, the VF
workspace loader, and the CORE provenance gate are NOT started.
