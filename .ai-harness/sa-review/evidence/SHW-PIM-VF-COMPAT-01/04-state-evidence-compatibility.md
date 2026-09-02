# 04 — State / Evidence Compatibility

Verifies the export can be consumed against the frozen state/evidence boundary.

## 4.1 State dimensions / vocabulary — consumable without flattening

- State vocabulary is PIM-owned and orthogonal (`evidence_status`,
  `epistemic_state`, `truth_domain`, plus `fidelity_readiness` in the readiness
  profile).
- Readiness ladder is a separate, PIM-side advisory enum:
  `NotReady → LogicalOnly → FirstOrderReady → ParameterizedReady → CalibratedReady`.
- No requirement to flatten into a single enum; ALIGN-01 §05 forbids flattening.
  The export keeps dimensions distinct.

→ COMPATIBLE.

## 4.2 SourceMapped vs SiteVerified — not conflated

- `model.yaml`: **0 `SourceMapped`**, **0 `SiteVerified`** entities (harness-verified).
- 30 expected signals carry `PendingSourceMapping` (harness `MAP-004` INFO) —
  i.e., mapping is pending, not claimed.
- `evidence_policy.yaml` promotion ladder: `Expected → SourceMapped → SiteVerified`;
  `SourceMapped` requires `source_system` + `external_source_id`;
  `SiteVerified` requires reviewer + date + evidence reference; promotion never
  automatic.

→ `SourceMapped` and `SiteVerified` remain distinct; neither is claimed.

## 4.3 Missing / unknown evidence — explicit

- 12 gaps in `model_fixture/gap_register.yaml` (GAP-SHW-001…012).
- `missing_parameters` listed explicitly per object in the readiness profile
  (`missing_parameter_policy.md`: "Never hide missing data").
- Fidelity readiness never over-claimed: `ParameterizedReady` and
  `CalibratedReady` are NOT claimed (GAP-SHW-010/012).

→ Missing/unknown remains explicit; no fabrication.

## 4.4 VF synthetic/runtime provenance vs PIM evidence truth — separable

- PIM truth domains are `Normative | Observed | Historical` (PIM-owned evidence).
- VF runtime provenance (`origin_kind: simulation`,
  `data_status: synthetic | simulated_ground_truth`) is a separate VF-owned axis
  (frozen in PH00 §10).
- The export does not overlap or claim VF runtime provenance; it stays on the
  PIM semantic side.

→ VF synthetic/runtime provenance can remain separate from PIM evidence truth.

## 4.5 Verdict

**State / evidence compatibility: COMPATIBLE** — vocabularies are consumable
without flattening, `SourceMapped` is not conflated with `SiteVerified`,
missing/unknown evidence is explicit, and VF runtime provenance stays separate.
