# 06 — Compatibility Decision

## 6.1 Evaluated axes

| Axis | Verdict |
|---|---|
| A. Identity / pinning | VERIFIED (evidence 01) — 3 pins resolved, hashes MATCH; 1 reading-precision nuance (`final_pim_main_sha` label). |
| B. Authority boundary | COMPATIBLE (evidence 02) — PIM owns IDs + vocab; VF read-only. |
| C. Required mapping feasibility | FEASIBLE (evidence 03) — canonical identity complete/unambiguous; no in-principle blocker. |
| D. State / evidence compatibility | COMPATIBLE (evidence 04) — no flattening; SourceMapped ≠ SiteVerified; gaps explicit. |
| E. Gap impact | Classified (evidence 05) — 2 blocks_runtime; 7 compatible_with_gap; 3 out_of_scope; 0 blocks_binding. |
| F. VF readiness hints | Non-authoritative drafts (below) — consumable as planning/reference only. |

## 6.2 VF readiness hints (draft, non-authoritative)

`vf_object_class_mapping.yaml`, `vf_readiness_profile_schema_draft.yaml`,
`readiness_level_policy.md`, `missing_parameter_policy.md` are all PIM-side
**draft / advisory** artifacts (GAP-SHW-011: "must be validated against a real
VF model library before use"). VF may consume them as **planning/reference
inputs** without violating ownership — but they MUST NOT be treated as
authoritative VF runtime model selection or behavior.

## 6.3 Decision

**`compatible_with_constraints`**

Rationale:

- **Not `incompatible`**: no authority/schema/identity mismatch; the boundary
  and pins are correct.
- **Not `correction_required`**: no specific PIM/VF contract mismatch requires a
  PIM-side correction before acceptance. (The version-identity inconsistency
  observed in EXPORT-01 is already resolved by the PIM FINALIZE-01 gate.)
- **Not plain `compatible`**: explicit constraints must remain fail-closed for
  later implementation (runtime not authorized; HIGH gaps block runtime; draft
  hints non-authoritative; pin-reading precision required).

## 6.4 Constraints that must remain fail-closed

1. **Runtime remains `NOT_AUTHORIZED`** — this review does not authorize VF
   loader, binding validation, CORE provenance, PH01, simulation, or calibration.
2. **GAP-SHW-001 / GAP-SHW-002 (HIGH, OPEN) = `blocks_runtime`** — source tags
   and control logic must be resolved before any runtime work.
3. **Draft VF readiness hints are non-authoritative** — planning/reference only
   (GAP-SHW-011).
4. **Pin-reading precision**: canonical main = `ec7f1266…`; the manifest
   `final_pim_main_sha` (`da33c1ea…`) is a historical finalization marker.
5. **No SourceMapped / no SiteVerified** — 30 signals remain
   `PendingSourceMapping`; VF must not assume source truth.

## 6.5 Decision statement

The exact PIM export `SHW-PIM-VF-EXPORT-v0.1` (source model `SHW-PH03-v0.1`)
is **semantically compatible** with the VF consumer/binding contract frozen in
ALIGN-01, **with explicit constraints that must remain fail-closed** for any
later implementation. This result does **not** authorize runtime by itself.
