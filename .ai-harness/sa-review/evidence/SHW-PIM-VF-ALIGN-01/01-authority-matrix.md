# 01 — PIM↔VF Authority Matrix

**Authoritative VF baseline:** `main` @ `3b006c5f58879eb3a9cd72aee21135b7fbbfcb24`
(post PR #29 merge; recorded at ALIGN-01 task start).
**Scope:** contract-level only; no implementation.

Legend: **PIM** = upstream semantic authority · **VF** = simulation runtime ·
**REVIEW** = PIM/VF integration review (joint) · **OUT-OF-SCOPE** = deferred.

| Concept | Owner | Rule |
|---|---|---|
| canonical object id / asset id | **PIM** | VF consumes read-only; never invents/rewrites |
| canonical signal id | **PIM** | VF consumes read-only; never invents/rewrites |
| object ↔ signal relationship | **PIM** | structural truth of the plant semantics |
| classification / type (asset, signal, area, system) | **PIM** | taxonomy owned upstream |
| orthogonal state dimensions + vocabularies | **PIM** (dimensions + vocabulary) / **VF** (runtime instance of those dimensions) | PIM defines which dimensions exist and their value vocabularies; VF owns the runtime *instances* of states |
| signal → state semantics (which dimension a signal reports) | **PIM** | where defined; may be `unknown` (gap) |
| observability (what is measurable vs inferred) | **PIM** | evidence-backed; VF must not downgrade/upgrade silently |
| evidence maturity / source status (SourceMapped, SiteVerified, …) | **PIM** | VF must NOT mutate |
| known / missing parameters + readiness | **PIM** | gaps marked `missing`/`unknown`/`review_required` |
| artifact identity / version / content hash | **PIM** | VF consumes pinned references |
| compatibility status (artifact ↔ VF contract) | **REVIEW** (PIM/VF integration review) | relationship, not a PIM property |
| workspace_id / runtime instance ids | **VF** | runtime identity |
| run / scenario / step / simulation time | **VF** | runtime provenance |
| runtime-local model/signal keys (`runtime_signal_id`, `model_signal_key`) | **VF** | distinct from canonical ids; never renamed to canonical |
| simulation state instances + transitions | **VF** | runtime behavior |
| fidelity | **VF** (declared per workspace) | bounded by `runtime.fidelity_ceiling` |
| synthetic output provenance (`origin_kind: simulation`, `data_status: synthetic|simulated_ground_truth`) | **VF** | simulation-only truth, never presented as site truth |
| outputs.namespace | **VF** | protocol/path-safe; deterministically bound to workspace_id |

## Non-negotiable (carried from PH00 C02)

1. PIM owns canonical object/signal IDs — VF reads only.
2. `workspace_id`, `canonical_signal_id`, `outputs.namespace` are distinct.
3. PIM owns artifact identity/version/hash; compatibility is a REVIEW relationship.
4. SH WTP `semantic_binding.mode: required` — fail closed.
5. VF runtime state/provenance never overwrites PIM semantic/evidence truth.

## Vocabulary note (frozen)

The concrete value lists mentioned above (e.g. observability examples,
`SourceMapped` / `SiteVerified` evidence maturity) are **NON-NORMATIVE examples**
in this gate. ALIGN-01 freezes only ownership + structural fields; it does NOT
create or expand a PIM ontology/vocabulary. Any value vocabulary becomes
normative only when proven by an authoritative PIM artifact. `SourceMapped`
proves mapping/provenance to an identified source — it does NOT imply site
verification or plant ground truth, and stays distinct from `SiteVerified`.
