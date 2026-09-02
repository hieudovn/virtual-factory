# 05 — State-Dimension Boundary & Compatibility Review

## 5.1 Orthogonal state dimensions (not a flat enum)

SH WTP state is modeled as **orthogonal dimensions**, each with a PIM-owned
vocabulary. VF owns the runtime **instances** (which value is active at a given
simulation time) but not the dimension definitions or vocabularies.

| Dimension (PIM owns the vocabulary) | Runtime instance (VF owns) |
|---|---|
| `operating_state` | which value is active at step N (RUN/IDLE/FAULT/…) |
| `quality_state` | which quality value is active |
| `availability` | active availability value |
| `maintenance_state` | active maintenance value |
| `fidelity` (declared ceiling) | which fidelity level is actually used |

- PIM defines the **dimensions** and their **allowed value vocabularies** and the
  **signal → dimension** mapping (where established).
- VF defines the **runtime instance values** and **transitions** between them
  during a simulation run.
- If PIM has not established a dimension or its vocabulary, VF must NOT invent
  one — the dimension is marked `unknown`/`review_required` (see §06).

## 5.2 Compatibility review record (owned by PIM/VF integration review)

```text
compatibility:
  pim_artifact:          # exact artifact identity
    name: ...
    version: ...
    content_sha: ...
  vf_consumer:
    name: vf
    consumer_contract_version: ...   # the VF consumer contract/runtime version
  status: compatible | review_required | incompatible
  reviewed_by_gate: SHW-PIM-VF-ALIGN-01   # or the gate that performed the review
  reviewed_at: ...
```

- Compatibility is a **relationship** between the exact PIM artifact and the
  exact VF consumer contract/version — NOT a property owned solely by PIM.
- A changed PIM `content_sha` or VF `consumer_contract_version` invalidates the
  record (status → `review_required`) until a fresh review.

## 5.3 What cannot be silently decided here

Choosing a NEW canonical identifier scheme, or a NEW state vocabulary/ontology
with material product impact, requires its own SA decision (STOP condition).
