# SHW-PIM-VF-COMPAT-01 — Review PIM export v0.1 against VF semantic binding contract

> **C01 revision (Issue #36):** gap-impact semantics refined to scope-precise
> distinctions — synthetic `LogicalOnly` simulation (S1) vs source-mapped /
> site-integrated runtime (S2) vs site-faithful control/interlock (S3) vs
> FirstOrder/parameterized execution (S4). PIM package/SHA/hash unchanged;
> `0 blocks_binding` unchanged; decision `compatible_with_constraints` unchanged;
> runtime authorization `NOT_AUTHORIZED` unchanged.

| Field | Value |
|---|---|
| Task ID | `SHW-PIM-VF-COMPAT-01` (GitHub Issue #35) + C01 (Issue #36) |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Cross-project PIM↔VF compatibility review / documentation-evidence only |
| Canonical VF baseline | `main` @ `b0affc99b5eae175bf2558ad6072afab8cb8960a` (post PR #34; recorded at task start) |
| Reviewed PIM handoff | `hieudovn/plant-intelligence-model` @ `main` `ec7f1266…` — package `SHW-PIM-VF-EXPORT-v0.1` (v0.1, source model `SHW-PH03-v0.1`) |
| Production code changed | **NO** (only `.ai-harness/`) |
| Runtime authorization | **NOT_AUTHORIZED** (unchanged — governance state of this gate) |

## 1. Objective

Decide whether the exact PIM export `SHW-PIM-VF-EXPORT-v0.1` is semantically
compatible with the VF consumer/binding contract frozen in ALIGN-01. Review
only — no runtime binding implementation.

## 2. Handoff verification (evidence 01)

| Item | Result |
|---|---|
| PIM repo resolves | PASS |
| Canonical main = `ec7f1266…` | PASS (`git ls-remote`) |
| Semantic model identity SHA = `f23f3c46…` | PASS (commit "normalize … SHW-PH03-v0.1") |
| Export artifact hash baseline = `ea3361a4…` | PASS (commit "PIM→VF export manifest/contents/hashes") |
| Artifact SHA-256 vs HASHES table | PASS (all sampled hashes MATCH) |
| `model.yaml` source_model_version | PASS (`SHW-PH03-v0.1`) |

Linear SHA lineage confirmed: `d241da6 → f23f3c4 → ea3361a → 797546c → da33c1e → ec7f126`.
One reading-precision nuance recorded: manifest `final_pim_main_sha` =
`da33c1ea…` is the finalization marker; canonical main is `ec7f1266…`.

## 3. Assessment axes

| Axis | Verdict |
|---|---|
| A. Identity / pinning | Verified |
| B. Authority boundary | COMPATIBLE — PIM owns IDs + vocabularies; VF read-only (evidence 02) |
| C. Required mapping feasibility | FEASIBLE — canonical identity complete/unambiguous; no in-principle blocker (evidence 03) |
| D. State / evidence compatibility | COMPATIBLE — no flattening; SourceMapped ≠ SiteVerified; gaps explicit (evidence 04) |
| E. Gap impact | Classified (C01 scope-precise) — 0 blocks_binding; GAP-001→S2, GAP-002→S3; 7 compatible_with_gap; 3 out_of_scope (evidence 05) |
| F. VF readiness hints | Non-authoritative drafts — consumable as planning/reference only (evidence 06) |

## 4. Gap impact summary (C01 scope-precise)

Runtime scopes: **S1** synthetic LogicalOnly simulation · **S2** source-mapped /
site-integrated runtime · **S3** site-faithful control/interlock · **S4**
FirstOrder/parameterized execution.

- `blocks_runtime` (scope-precise):
  - GAP-SHW-001 → **S2** (source-mapped/site-integrated binding + source-truth claims) — HIGH/OPEN;
  - GAP-SHW-002 → **S3** (site-faithful control/interlock behavior) — HIGH/OPEN.
  - Neither blocks **S1 synthetic LogicalOnly simulation**.
- `compatible_with_gap`: GAP-SHW-003, 004, 006, 007, 009, 010, 011.
  - GAP-SHW-010 scopes **S4**: FirstOrder/parameterized execution of affected
    models blocked while parameters are missing; LogicalOnly composition remains feasible.
- `out_of_scope_for_v0.1`: GAP-SHW-005, 008, 012.
- `blocks_binding`: **none** (unchanged) — canonical identity is complete and
  unambiguous for the first slice; no gap prevents exact-one canonical binding
  in principle.

## 5. STOP-condition assessment

| Stop condition | Assessment |
|---|---|
| PIM SHA/package/hash cannot be verified | NOT triggered — all verified |
| Exact export identity is ambiguous | NOT triggered — 3 distinct pins resolved |
| Decision requires changing PIM semantics or VF authority boundaries | NOT triggered |
| Draft PIM hints are the only source for a required canonical guarantee | NOT triggered — `model_fixture/model.yaml` is the authoritative source |
| Compatibility cannot be decided without implementation | NOT triggered — decided from the pinned export |

**Conclusion: no STOP condition triggered.**

## 6. Compatibility decision

**`compatible_with_constraints`**

The export `SHW-PIM-VF-EXPORT-v0.1` is semantically compatible with the frozen
VF consumer/binding contract, with explicit constraints that must remain
fail-closed for later implementation:

1. Runtime remains `NOT_AUTHORIZED` — governance state of this gate; not a
   semantic impossibility. A later SA may authorize a separate synthetic
   LogicalOnly runtime gate without contradicting this record.
2. GAP-SHW-001 (HIGH, OPEN) blocks **source-mapped/site-integrated runtime
   binding and source-truth claims**; does NOT block synthetic LogicalOnly
   simulation with clearly synthetic provenance.
3. GAP-SHW-002 (HIGH, OPEN) blocks **site-faithful control/interlock behavior**;
   does NOT block a simulation-owned logical controller/scenario model clearly
   labeled non-site-authoritative.
4. GAP-SHW-010 may block **FirstOrder/parameterized execution for affected
   models**; LogicalOnly composition remains feasible.
5. Draft VF readiness hints are non-authoritative (planning/reference only).
6. Pin-reading precision: canonical main = `ec7f1266…`.
7. No SourceMapped / no SiteVerified; 30 signals `PendingSourceMapping`.

This result does **not** authorize runtime by itself.

## 7. Acceptance

| Criterion | Result |
|---|---|
| Exact PIM export verified | PASS |
| Authority/identity compatibility explicit | PASS |
| Required mapping feasibility assessed | PASS |
| State/evidence compatibility assessed | PASS |
| Gaps classified by impact | PASS |
| One compatibility result stated with rationale | PASS (`compatible_with_constraints`) |
| No production code changed | PASS |
| Runtime remains NOT_AUTHORIZED | PASS |

## 8. Evidence

`.ai-harness/sa-review/evidence/SHW-PIM-VF-COMPAT-01/` — 6 files (01…06).
Evidence 05/06 revised at C01 (scope-precise gap semantics).

## 9. Final status

```text
SHW-PIM-VF-COMPAT-01-C01 — READY FOR SA REVIEW
```

Decision: **`compatible_with_constraints`** (unchanged; evidence-backed). PM does
not self-certify COMPLETE/CLOSED. Runtime, VF loader/binding, CORE provenance,
and SHW-VF-PH01 remain NOT AUTHORIZED.
