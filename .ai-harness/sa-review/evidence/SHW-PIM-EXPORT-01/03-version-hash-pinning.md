# 03 — Version & Hash Pinning

The export is pinned by two independent mechanisms:

1. **Git SHA** — the whole PIM repo at the exact commit that contains the
   export content.
2. **Per-file SHA-256 content hashes** — byte-level pinning of each key export
   artifact, so a changed file flips its hash (→ `review_required` per the
   frozen ALIGN-01 contract).

## 3.1 Repository pin

```text
Repository:  https://github.com/hieudovn/plant-intelligence-model
Branch/ref:  main
Git SHA:     d241da61a6166df8359f892141609add75aec5b5
Commit date: 2026-08-29 10:02:55 +0700
```

## 3.2 Per-file SHA-256 (computed at pin time, SHA-256)

```text
examples/song-hong-wtp/model_fixture/model.yaml
  F818E61937BD4F766121D1991EBD1B75885C41BC597B4B1444ECD90A78D23525

examples/song-hong-wtp/model_fixture/gap_register.yaml
  7C95878B226730D7A6531542320EE4DD7173D5BF8461D0F038BD996A500929DB

examples/song-hong-wtp/contracts/vf_readiness_contract_draft.yaml
  29C2C1862BDAF80AAA78E5BE554C1BEF7EAF51EEB3F55852CDD3517A0C1694EC

examples/song-hong-wtp/plant_config/canonical_id_rules.md
  1CCE5E007F22CC2087F1E64F3E6125D5ABE7A343077C156C4F121A25B53612B8

examples/song-hong-wtp/plant_config/contract_principles.md
  2257C614604A9AE2E633E761CDFA7D401FF5A0853278EE6CF69B88A88D2A7B68

examples/song-hong-wtp/plant_config/evidence_policy.yaml
  D2C83F46826E8CBF62CD4E9929B91BEE5A83188022878E6147652FE25B7DE811

examples/song-hong-wtp/seed/signal_catalog_ph02.yaml
  12CC8FF818D05663166D2A2EA61A7486D2587615894D1DF865DF03D706A15A5E

examples/song-hong-wtp/seed/first_vf_readiness_slice_t106_t108_t110.yaml
  47581A3FEF5099481D4D61925E77A1BC231C1C5CDE2A26EC7EB5662CD89EC8A3

examples/song-hong-wtp/vf_readiness/vf_object_class_mapping.yaml
  09BDEF764919D4CF22562AE8D4D222B6F8D46CC3457F86BF4BB1D6332001E946

examples/song-hong-wtp/vf_readiness/vf_readiness_profile_schema_draft.yaml
  15EC55B8C6DDA20DA0D1F41C5364BA5991476C0DBBAC338181D15D7B85B4AC26
```

## 3.3 PIM-side version identifiers (as declared in the artifacts)

```text
vf_readiness_contract_draft.yaml:
  contract_id:          CONTRACT-SHW-VF-READINESS-DRAFT-v0.1
  contract_type:        GenericProjection
  schema_version:       0.1.0
  producer:             PIM
  consumer:             VF-Planning
  source_model_version: SHW-PH03-v0.1
  model_version:        SHW-PH03-v0.1

model_fixture/model.yaml:
  model_version:        1
  source_model_version: SHW-PH02-v0.1   # top-level field (see 04 §4.5 note)
  evidence_policy_version: "0.1"
```

## 3.4 Pinning mechanism verdict

- Exact artifact: YES — the SH WTP export package `examples/song-hong-wtp/`.
- Exact version: YES — PIM-side identifiers above + git SHA + content hashes.
- Exact hash mechanism: YES — git SHA (repo-wide) + SHA-256 (per-file).
- A changed SHA or content hash flips `compatibility.status` to
  `review_required` until re-reviewed (frozen ALIGN-01 §04).
