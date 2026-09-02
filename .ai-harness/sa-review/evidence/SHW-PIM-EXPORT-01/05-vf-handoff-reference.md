# 05 — VF Handoff Reference (immutable, reference-only)

The VF repo records ONLY the immutable handoff reference. It does NOT copy the
PIM semantic content as a VF-owned artifact, and does NOT become the semantic
source of truth.

## 5.1 Immutable handoff reference

```text
Semantic source (PIM-owned):
  repository:  https://github.com/hieudovn/plant-intelligence-model
  ref:         main
  git_sha:     d241da61a6166df8359f892141609add75aec5b5
  package:     examples/song-hong-wtp/

Pinned artifacts (PIM path → SHA-256):
  model_fixture/model.yaml
    F818E61937BD4F766121D1991EBD1B75885C41BC597B4B1444ECD90A78D23525
  model_fixture/gap_register.yaml
    7C95878B226730D7A6531542320EE4DD7173D5BF8461D0F038BD996A500929DB
  contracts/vf_readiness_contract_draft.yaml
    29C2C1862BDAF80AAA78E5BE554C1BEF7EAF51EEB3F55852CDD3517A0C1694EC
  plant_config/canonical_id_rules.md
    1CCE5E007F22CC2087F1E64F3E6125D5ABE7A343077C156C4F121A25B53612B8
  plant_config/contract_principles.md
    2257C614604A9AE2E633E761CDFA7D401FF5A0853278EE6CF69B88A88D2A7B68
  plant_config/evidence_policy.yaml
    D2C83F46826E8CBF62CD4E9929B91BEE5A83188022878E6147652FE25B7DE811
  seed/signal_catalog_ph02.yaml
    12CC8FF818D05663166D2A2EA61A7486D2587615894D1DF865DF03D706A15A5E
  seed/first_vf_readiness_slice_t106_t108_t110.yaml
    47581A3FEF5099481D4D61925E77A1BC231C1C5CDE2A26EC7EB5662CD89EC8A3
  vf_readiness/vf_object_class_mapping.yaml
    09BDEF764919D4CF22562AE8D4D222B6F8D46CC3457F86BF4BB1D6332001E946
  vf_readiness/vf_readiness_profile_schema_draft.yaml
    15EC55B8C6DDA20DA0D1F41C5364BA5991476C0DBBAC338181D15D7B85B4AC26
```

## 5.2 Compatibility (VF/PIM integration-review relationship)

```text
semantic_source:
  artifact: shw-wtp-pim-export
  version:  SHW-PH03-v0.1 (contract draft) / model.yaml model_version 1
  git_sha:  d241da61a6166df8359f892141609add75aec5b5

compatibility:
  consumer: vf
  status:   review_required      # NOT "compatible"
  reason:   PIM-side SHW-PIM-PH03 / SHW-CONTRACT-PH01 gates not yet SA-CLOSED;
            PIM-side version-string inconsistency (SHW-PH02 vs SHW-PH03) noted.
  reviewed_by_gate: SHW-PIM-EXPORT-01
```

## 5.3 Boundary rules (preserved from ALIGN-01 / PH00)

1. VF stores references, not copies, of PIM semantic artifacts.
2. PIM owns `canonical_id`; VF consumes read-only and never invents/rewrites.
3. A changed git SHA or content hash flips `compatibility.status` to
   `review_required` until re-reviewed.
4. `SourceMapped` ≠ `SiteVerified` ≠ site truth; VF never promotes evidence.
5. VF never writes back to PIM.
6. Required runtime→canonical mapping must resolve to exactly one valid
   PIM-owned canonical target (fail-closed; SH WTP mode `required`).

## 5.4 What VF is NOT doing here

- NOT inventing canonical IDs, vocabularies, evidence maturity, or site truth.
- NOT converting `examples/contracts/wtp-demo-01.contract.yaml` (VF-side empty
  stub) into authoritative PIM truth.
- NOT implementing the VF workspace loader or binding validation.
- NOT implementing CORE provenance threading.
- NOT starting PH01.
