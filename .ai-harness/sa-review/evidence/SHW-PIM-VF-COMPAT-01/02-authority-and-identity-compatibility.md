# 02 — Authority & Identity Compatibility

Verifies the export preserves the authority boundary frozen in ALIGN-01/PH00.

## 2.1 PIM ownership of canonical IDs — PRESERVED

- `plant_config/canonical_id_rules.md`: "`canonical_id` is **stable and
  PIM-owned**. No external system (SCADA, PLC, MES, ERP, CMMS) may assign or
  mutate it."
- ID pattern `{CLASS}-SHW-{SCOPE}-{SEQUENCE}` with per-class prefixes
  (`PLANT-SHW`, `AREA-SHW-*`, `UNIT-SHW-*`, `ASSET-SHW-*`, `INST-SHW-*`,
  `SIG-SHW-*`, `ALM-SHW-*`, `PROC-SHW-*`).
- Manifest: "PIM owns canonical IDs. VF must reference, not invent, canonical IDs."

→ VF read-only consumption holds; no VF invention required.

## 2.2 PIM ownership of state/evidence vocabularies — PRESERVED

- `plant_config/evidence_policy.yaml` defines `evidence_status`
  (`DocumentConfirmed | PatternInferred | IndustryExpected | Expected |
  SourceMapped | SiteVerified | Rejected`), `epistemic_state`
  (`Known | Unknown | InsufficientEvidence | Contradiction`), `truth_domain`
  (`Normative | Observed | Historical`), and promotion rules.
- Manifest: "PIM owns evidence_status / epistemic_state / truth_domain
  vocabulary" (reference `docs/06-canonical-model.md`).

→ VF must consume these read-only; no flattening or reinterpretation.

## 2.3 VF read-only consumption — PRESERVED

- Manifest `non_authorization_statement`: "This export does NOT authorize VF
  runtime implementation, VF package generation, simulation execution, or model
  calibration."
- CONTENTS §3 "What VF must NOT do": no runtime package, no invented IDs/
  vocabularies/SiteVerified/SourceMapped, no calibration, no repair of PIM
  semantics to close gaps.

→ No VF-side semantic repair or invention is required or permitted.

## 2.4 Version identity normalization — consistent

- `model.yaml` top-level `source_model_version` is now `SHW-PH03-v0.1`
  (previously `SHW-PH02-v0.1` in the EXPORT-01 baseline). The FINALIZE-01
  closeout documents this as a conservative identity normalization: PH03
  plant-wide skeleton accepted as the export basis; internal PH01/PH02 contract
  projections keep their historical phase versions.
- No semantic content changed beyond the version-identity field.

→ The prior EXPORT-01 observation (version-string inconsistency) is resolved.

## 2.5 Authority verdict

The export preserves: PIM ownership of canonical object/signal IDs ✅, PIM
ownership of state/evidence vocabularies ✅, VF read-only consumption ✅, and
no VF-side semantic repair/invention ✅.

**Authority boundary: COMPATIBLE.**
