# SHW-PIM-VF-ALIGN-01 — PIM↔VF Semantic Handoff Contract

| Field | Value |
|---|---|
| Task ID | `SHW-PIM-VF-ALIGN-01` (GitHub Issue #30) |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Cross-project semantic-boundary alignment / documentation-contract only |
| Authoritative VF baseline | `main` @ `3b006c5f58879eb3a9cd72aee21135b7fbbfcb24` (post PR #29 merge; recorded at task start) |
| Production code changed | **NO** (only `.ai-harness/`) |
| SHW runtime / PIM export / workspace loader implemented | **NO** |
| PH01 started | **NO** |

## 1. Objective

Freeze the PIM↔VF semantic handoff boundary for SH WTP **at contract level
only**, so neither side implements the runtime binding before the boundary is
unambiguous.

## 2. Frozen authority (carried from PH00 C02, preserved)

- PIM owns canonical object IDs and canonical signal IDs; VF consumes read-only.
- `workspace_id`, `canonical_signal_id`, `outputs.namespace` are distinct.
- PIM owns artifact identity/version/content-hash; compatibility is an
  integration-review relationship.
- SH WTP `semantic_binding.mode: required` — fail closed.
- VF runtime state/provenance never overwrites PIM semantic/evidence truth.

## 3. What is now frozen (contract)

### A. PIM-owned export contract (evidence §02)
PIM owns: canonical objects/assets, canonical signals, object↔signal
relationships, classification/type, orthogonal state dimensions + vocabularies,
signal→state semantics (where defined), observability, evidence maturity/source
status, known/missing parameters, and artifact identity/version/content-hash.

### B. VF-owned runtime contract (evidence §03)
VF owns: workspace/runtime instance ids, run/scenario/step/time, runtime-local
model/signal keys, simulation state instances, transitions/scenario execution,
fidelity, synthetic output provenance, and `data_status ∈ {synthetic,
simulated_ground_truth}`. VF must NOT mutate PIM evidence maturity, canonical
ids, or site truth.

### C. Binding/mapping (evidence §04)
VF maps `runtime_signal_id` → `canonical_signal_id` via an explicit mapping
artifact; local keys are **never renamed** to canonical ids; required vs
optional mappings are explicit.

### D. Fail-closed (evidence §04)
With `mode: required`, the workspace is invalid to load/run if a required
artifact reference/version/SHA is missing, the SHA mismatches, compatibility is
not `compatible`, or a required mapping is not `mapped` with exactly one valid
PIM-owned canonical target — i.e. it is `unmapped`, `review_required`, missing
its target, or ambiguous/multiple-target. Optional simulation-only mappings may
remain local/unmapped only when explicitly non-published and non-canonical.

### E. Compatibility review ownership (evidence §05)
A compatibility record binds exact PIM artifact (name/version/SHA) ↔ exact VF
consumer contract/version, with status and reviewing gate — owned by PIM/VF
integration review, not PIM alone.

### F. State-model boundary (evidence §05)
Orthogonal state dimensions (not a flat enum); PIM owns dimensions + vocabulary
+ signal→dimension mapping; VF owns runtime instances + transitions.

### G. Open-gap handling (evidence §06)
Missing/unknown/review-required is marked explicitly; VF never fabricates
canonical semantics to keep the run going.

## 4. STOP-condition assessment

| Stop condition | Assessment |
|---|---|
| Authority boundary unresolvable from accepted principles | NO — resolved by frozen PH00 ownership |
| Existing PIM contract contradicts frozen PH00 ownership | NO — `examples/contracts/wtp-demo-01.contract.yaml` (stub) does not contradict the frozen ownership model; it is INSUFFICIENT to serve as the final SH WTP semantic export contract and remains non-authoritative/incomplete for runtime binding until the future PIM export gate produces the required pinned artifact. A VF-side documentation gate does NOT supersede or replace a PIM/upstream artifact. |
| Alignment requires a new canonical identifier scheme | NO — no scheme chosen; PIM ownership frozen |
| New state vocabulary/ontology with material impact required | NO — dimensions reference the frozen orthogonal model; no new vocabulary invented |
| Implementation needed to answer the contract | NO — contract answered purely at documentation level |

**Conclusion: no STOP condition triggered.**

## 5. Acceptance

| Criterion | Result |
|---|---|
| PIM↔VF ownership unambiguous | PASS (evidence §01) |
| Semantic artifact pinning + fail-closed explicit | PASS (evidence §02/§04) |
| Canonical vs runtime-local identities separated | PASS (evidence §03/§04) |
| State-dimension ownership explicit | PASS (evidence §05) |
| Missing/unknown semantic info cannot be fabricated | PASS (evidence §06) |
| No production code changed | PASS |
| PH01 remains not started | PASS |

## 6. Evidence

`.ai-harness/sa-review/evidence/SHW-PIM-VF-ALIGN-01/` — 6 files (01…06).

## 7. Final status

```text
SHW-PIM-VF-ALIGN-01 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. PH01 and the CORE provenance gate are
not started.
