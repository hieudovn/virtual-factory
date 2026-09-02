# 04 — Gap & Maturity Status

The PIM export does NOT claim site truth. Every item carries an evidence
status; missing/unknown information stays explicit. VF must not fabricate it.

## 4.1 Evidence maturity (PIM-owned, as declared)

From `examples/song-hong-wtp/plant_config/evidence_policy.yaml` (PIM-owned):

```text
Evidence statuses:  DocumentConfirmed | PatternInferred | IndustryExpected |
                    Expected | SourceMapped | SiteVerified | Rejected
Epistemic states:   Known | Unknown | InsufficientEvidence | Contradiction
Truth domains:      Normative | Observed | Historical
Promotion:          Expected --source evidence--> SourceMapped
                                              --site/human review--> SiteVerified
```

Hard rules in effect for SH WTP:

- Generated item cannot be SiteVerified.
- SourceMapped requires `source_system` + `external_source_id`.
- SiteVerified requires reviewer + review_date + evidence_reference.
- Promotion is never automatic.

## 4.2 Current SH WTP maturity (as of the pinned SHA)

- Evidence statuses present: `DocumentConfirmed`, `PatternInferred`,
  `IndustryExpected`, `Expected`.
- **No `SourceMapped`** and **no `SiteVerified`** items exist in the SH WTP
  model. Source mapping is pending.
- Fidelity readiness: `LogicalOnly` (most objects) / `FirstOrderReady` (tanks
  with basic level/flow); `ParameterizedReady` and `CalibratedReady` are
  NOT claimed.

## 4.3 Gap register (explicit; from `model_fixture/gap_register.yaml`)

| Gap | Title | Severity | Status |
|---|---|---|---|
| GAP-SHW-001 | PLC/SCADA tag export not available (blocks SourceMapped) | HIGH | OPEN |
| GAP-SHW-002 | PLC source code / interlock matrix not available | HIGH | OPEN |
| GAP-SHW-003 | Hydraulic parameters not available | MEDIUM | ACCEPTED_FOR_V0_1 |
| GAP-SHW-004 | Raw water / lab quality history not available | MEDIUM | ACCEPTED_FOR_V0_1 |
| GAP-SHW-005 | Electrical detailed mapping not available | MEDIUM | ACCEPTED_FOR_V0_1 |
| GAP-SHW-006 | Unconstrained relation types (DISCHARGES_TO / CONNECTED_TO) | LOW | ACCEPTED_FOR_V0_1 |
| GAP-SHW-007 | Alarm/event taxonomy not finalized | LOW | OPEN |
| GAP-SHW-008 | KPI category not available in harness | LOW | OPEN |
| GAP-SHW-009 | Procedure step modeling deferred | LOW | OPEN |
| GAP-SHW-010 | VF readiness parameters missing (→ LogicalOnly/FirstOrderReady) | MEDIUM | OPEN |
| GAP-SHW-011 | VF object class mapping is draft (validate vs real VF library) | LOW | OPEN |
| GAP-SHW-012 | VF fidelity not calibrated | LOW | OPEN |

Source-mapping vs site-truth are kept distinct: `GAP-SHW-001` explicitly blocks
`SourceMapped` until a PLC/SCADA tag export exists; no item is labelled
`SiteVerified`. This satisfies the Issue #33 STOP-check
"site truth/evidence maturity cannot be distinguished from source mapping" —
they ARE distinguished.

## 4.4 PIM-side harness result (machine-derived)

```text
SHW-PIM-PH03 harness (readiness mode) on model_fixture:
  Result: PASS_WITH_WARNINGS
  Entities: 105 | Relationships: 121 | Contracts: 4
  Errors: 0 | Warnings: 2 (REL-006)
```

## 4.5 PIM-side gate status (recorded honestly — NOT a VF-side claim)

The SH WTP content's own PIM-side gates are at these states as of the pinned
SHA:

- `SHW-PIM-PH01` — CLOSED / ACCEPTED (first VF-readiness slice fixture baseline).
- `SHW-PIM-PH02` — CLOSED (accepted baseline).
- `SHW-PIM-PH03` — "SA review required. Not CLOSED." (plant-wide skeleton).
- `SHW-CONTRACT-PH01` — READY_FOR_SA_REVIEW (as part of SHW-KG-W02); not CLOSED.
- Internal observation: `model.yaml` top-level `source_model_version` is
  `SHW-PH02-v0.1` while the PH03 closeout describes a plant-wide skeleton and
  `vf_readiness_contract_draft.yaml` declares `SHW-PH03-v0.1`. This is a
  PIM-side version-string inconsistency; the git SHA + content hashes pin the
  exact bytes regardless.

## 4.6 Consequence for VF compatibility status

Per the frozen ALIGN-01 contract (a changed/not-yet-compatible pin →
`review_required`), the VF-side compatibility status for this pin is:

```text
compatibility.status = review_required   (NOT "compatible")
```

until the PIM-side gates are SA-accepted and the export version is finalized.
VF does not invent or promote any evidence status to close this gap.
