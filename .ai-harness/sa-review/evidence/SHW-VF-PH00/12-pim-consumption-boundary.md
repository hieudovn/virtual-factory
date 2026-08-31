# 12 — PIM Consumption Boundary

PH00 prepares the VF side only. VF **consumes immutable, versioned upstream
artifacts** and does not modify them.

## 12.1 Upstream artifacts VF must NOT modify

- PIM knowledge graph (KG)
- ontology
- evidence vocabulary
- `SourceMapped` mappings
- `SiteVerified` mappings

## 12.2 Reference shape (frozen, used by the workspace manifest §06)

Every consumed upstream artifact reference must carry:

```text
artifact name
version
commit SHA / content hash
compatibility status    # compatible | review_required | incompatible
```

Example (proposal):

```yaml
semantic_sources:
  pim_contract:
    artifact: shw-wtp-pim-contract
    version: "0.1.0"
    commit_sha: <full sha>
    compatibility_status: review_required
  state_templates:
    artifact: shw-wtp-state-templates
    version: "0.1.0"
    commit_sha: <full sha>
    compatibility_status: review_required
```

## 12.3 Boundary rules (frozen)

1. VF stores **references**, not copies, of PIM/ontology/evidence-vocabulary
   artifacts. If a local cache copy is needed for offline runs, it is a
   **content-hash-pinned mirror**, never an editable fork.
2. Any upstream `commit_sha`/hash change → the workspace's
   `compatibility_status` flips to `review_required` until re-reviewed.
3. `SourceMapped`/`SiteVerified` tags are consumed read-only into a **mapping
   artifact** separate from `canonical_signal_id` (the canonical id is VF
   internal, §10).
4. VF never writes back to PIM, ontology, evidence vocabulary, or PlantOS/MES.
5. If the PIM contract shape is required to decide a VF **core API** (not just
   workspace config) → **STOP FOR SA** (§17). PH00 assessment: the VF core API
   is already fixed (`--config` + `ModelRegistry` + `create_engine`); PIM shape
   affects workspace **mapping/config**, not core API.

## 12.4 Existing evidence in repo

- `examples/contracts/wtp-demo-01.contract.yaml` — PlantOS Integration Contract
  v2 stub (`plant.id=WTP-DEMO-01`, 9 areas, empty assets/signals/behaviors).
- `simulators/vf2/package_loader.py` + `package_validator.py` — VF-2 already
  demonstrates package/contract loading + validation (read-only pattern to reuse).
- No `SourceMapped`/`SiteVerified` artifacts exist in the repo today.
