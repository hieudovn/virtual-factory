# 03 — Required Mapping Feasibility

Assesses whether the export gives VF enough authoritative semantic identity for
later required runtime-local → canonical mappings (exact-one canonical binding,
per ALIGN-01 §04). The loader/binding implementation gate has NOT started; this
assesses feasibility in principle only.

## 3.1 Canonical identity availability

- `model.yaml`: 105 entities, each with a unique `canonical_id`
  (`PLANT-SHW`, `AREA-SHW-*`, `UNIT-SHW-*`, `ASSET-SHW-*`, `INST-SHW-*`, …).
- Canonical signals use `SIG-SHW-*` (signal catalog `seed/signal_catalog_ph02.yaml`
  + `included_signals` in the readiness contract).
- Object↔signal relationships and `signal_role` (`measurement` / `control`) are
  present (121 relationships).

→ The **canonical side** of the required mapping (PIM-owned target) exists and is
  unique per entity/signal.

## 3.2 First slice sufficiency

The first VF-readiness slice (T106 OSF filtration / T108 clean water tank /
T110 wash water recovery) carries:

- Units: `UNIT-SHW-L1-T106`, `UNIT-SHW-L1-T108`, `UNIT-SHW-WASH-T110`.
- VF object catalog (`vf_readiness_contract_draft.yaml`) lists canonical assets
  with `vf_object_type`, `vf_model_family_hint`, `fidelity_readiness`,
  required/optional/missing parameters, and `readiness_gaps`.
- Included signals with `signal_role` + `evidence_status`.

→ Enough authoritative semantic identity exists to plan exact-one
  runtime-local → canonical mappings for the slice.

## 3.3 What is NOT yet available (and why it does not block feasibility)

- The **runtime-local side** (`runtime_signal_id`, `model_signal_key`) does not
  exist yet — the VF loader/binding gate has not started. This is expected and
  not required by this review.
- `GAP-SHW-001` (PLC/SCADA tag export unavailable) means no **raw source tags**
  exist to produce `SourceMapped` evidence. This blocks source-mapped/site-verified
  truth (a runtime/evidence concern), but does NOT block the canonical identity
  structure: the required mapping target is the PIM canonical ID, which exists
  and is unique.

## 3.4 Feasibility verdict

No semantic gap makes exact-one canonical binding **impossible in principle**:

- Canonical IDs are PIM-owned, stable, and unique.
- The first slice has a complete canonical object/signal/relationship inventory.
- The runtime-local side is VF's own future key space (not yet defined, correctly
  deferred).

**Required mapping feasibility: FEASIBLE** — with constraints that the
source-mapped evidence chain (GAP-SHW-001) and control logic (GAP-SHW-002)
remain pending and must stay fail-closed for runtime (see evidence 05).
