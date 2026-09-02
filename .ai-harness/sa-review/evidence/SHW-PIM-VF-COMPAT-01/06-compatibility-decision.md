# 06 — Compatibility Decision

## 6.1 Evaluated axes

| Axis | Verdict |
|---|---|
| A. Identity / pinning | VERIFIED (evidence 01) — 3 pins resolved, hashes MATCH; 1 reading-precision nuance (`final_pim_main_sha` label). |
| B. Authority boundary | COMPATIBLE (evidence 02) — PIM owns IDs + vocab; VF read-only. |
| C. Required mapping feasibility | FEASIBLE (evidence 03) — canonical identity complete/unambiguous; no in-principle blocker. |
| D. State / evidence compatibility | COMPATIBLE (evidence 04) — no flattening; SourceMapped ≠ SiteVerified; gaps explicit. |
| E. Gap impact | Classified (evidence 05, C01-refined) — 0 blocks_binding; GAP-001→S2, GAP-002→S3 scope-precise; 7 compatible_with_gap; 3 out_of_scope. |
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
  later implementation (runtime not authorized by this gate; source-faithful/
  site-integrated/parameterized scopes fail-closed on missing evidence; draft
  hints non-authoritative; pin-reading precision required).

## 6.4 Constraints that must remain fail-closed (C01 scope-precise)

1. **Runtime remains `NOT_AUTHORIZED`** — a **governance state of this gate**, not
   a semantic impossibility. This review does not authorize VF loader, binding
   validation, CORE provenance, PH01, simulation, or calibration. A later SA may
   authorize a separate **synthetic LogicalOnly** runtime gate without
   contradicting this record.
2. **GAP-SHW-001 (HIGH, OPEN)** blocks **source-mapped/site-integrated runtime
   binding and source-truth claims** (`SourceMapped`/`SiteVerified`); it does
   **NOT** block an isolated synthetic LogicalOnly simulation with clearly
   synthetic provenance.
3. **GAP-SHW-002 (HIGH, OPEN)** blocks **site-faithful control/interlock
   behavior**; it does **NOT** block a simulation-owned logical controller/
   scenario model clearly labeled non-site-authoritative.
4. **GAP-SHW-010 (MEDIUM, OPEN)** may block **FirstOrder/parameterized execution
   for affected models** while physical parameters are missing; **LogicalOnly
   composition may remain feasible**.
5. **Draft VF readiness hints are non-authoritative** — planning/reference only
   (GAP-SHW-011).
6. **Pin-reading precision**: canonical main = `ec7f1266…`; the manifest
   `final_pim_main_sha` (`da33c1ea…`) is a historical finalization marker.
7. **No SourceMapped / no SiteVerified** — 30 signals remain
   `PendingSourceMapping`; VF must not assume source truth.

> C01: Source-faithful / plant-integrated behavior (S2/S3) and parameterized /
> FirstOrder execution with real parameters (S4) remain fail-closed while the
> corresponding plant evidence is missing. Synthetic LogicalOnly simulation (S1)
> is not semantically blocked by GAP-001/002/010 — whether it may run is the
> separate `NOT_AUTHORIZED` governance decision for this gate.

## 6.5 Decision statement

The exact PIM export `SHW-PIM-VF-EXPORT-v0.1` (source model `SHW-PH03-v0.1`)
is **semantically compatible** with the VF consumer/binding contract frozen in
ALIGN-01, **with explicit constraints that must remain fail-closed** for any
later implementation (C01: scope-precise — synthetic LogicalOnly simulation is
not semantically blocked by GAP-001/002/010; source-faithful/site-integrated/
parameterized scopes remain fail-closed on missing evidence). This result does
**not** authorize runtime by itself.
