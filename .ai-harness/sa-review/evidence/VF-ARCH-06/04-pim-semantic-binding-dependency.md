# VF-ARCH-06 · Evidence 04 — Decision D: PIM / semantic-binding dependency

## 1. Decision statement

**PIM remains the semantic authority; VF consumes version-pinned semantic
artifacts read-only and fail-closed. The accepted PH00 B1–B10 and PIM/VF
contracts are reconciled, not reopened.**

## 2. Frozen identity/authority (PH00 B1–B3, ALIGN-01)

| Contract | Frozen meaning |
|---|---|
| B1 | PIM owns canonical object IDs and canonical signal IDs; VF consumes read-only; VF MUST NOT invent/rewrite `canonical_signal_id` |
| B2 | three distinct identities: `workspace_id` (VF logical), `canonical_signal_id` (PIM-owned), `outputs.namespace` (path-safe) |
| B3 | `runtime.engine: continuous_process` for SH WTP; `vf-core` is NOT an engine discriminator |
| ALIGN-01 | VF may own: `workspace_id`, runtime instance ids, `run_id/scenario_id`, `step/simulation_time_s`, runtime-local keys, fidelity, synthetic provenance, `outputs.namespace` |

## 3. Semantic binding (PH00 B4–B5, ALIGN-01)

- `semantic_binding.mode ∈ {required, optional, none}`; **SH WTP = `required`**.
- Fail-closed: workspace invalid to load/run when ANY of: missing artifact
  ref/version/hash; SHA mismatch; `compatibility.status` ≠ `compatible`;
  required mapping not `mapped`/exactly-one target; optional mapping mislabeled.
  "No fallback to fabricated canonical semantics is permitted."
- The local key is **never renamed** to `canonical_signal_id`; for SH WTP the
  only acceptable required state is `mapped` with exactly one valid target
  (`unmapped`/`review_required`/ambiguous → fail closed).

## 4. Version/hash pinning (EXPORT-01)

- Authoritative PIM repo: `https://github.com/hieudovn/plant-intelligence-model`.
- Pins: git SHA `d241da61a6166df8359f892141609add75aec5b5` + per-file SHA-256
  (10 artifacts). "a changed file flips its hash (→ `review_required`)."
- Handoff: export `SHW-PIM-VF-EXPORT-v0.1`; `status: review_required` (NOT
  `compatible`); `VF runtime authorization: NOT_AUTHORIZED`.

## 5. Compatibility + fidelity (COMPAT-01, PH00 B10, PH00 §09)

- Compatibility decision: **`compatible_with_constraints`** — semantically
  compatible with explicit fail-closed constraints; does NOT authorize runtime.
- Fidelity ceiling: **`logical_only`** (B10). Three-level taxonomy
  LogicalOnly / SyntheticReference / FirstOrder; S1..S4 runtime scopes from
  COMPAT-01:
  - S1 synthetic LogicalOnly — not blocked by any gap;
  - S2 source-mapped — blocked by GAP-SHW-001 (HIGH);
  - S3 site-faithful control — blocked by GAP-SHW-002 (HIGH);
  - S4 FirstOrder — possibly blocked by GAP-SHW-010 (MED).
- **No fidelity raise** beyond `logical_only` without evidence + an explicit
  SA-reviewed gate.

## 6. What VF may NOT do (ALIGN-01 §3.2)

invent/rewrite canonical ids; rename VF-local key to canonical id; mutate PIM
evidence maturity; upgrade/downgrade semantics silently; fabricate canonical
semantics for missing parameters; present simulation output as real plant truth;
overwrite PIM site truth with runtime values.

## 7. Dependency consequence

Semantic binding vNext depends on the shared identity/provenance foundation
(B8) — so the roadmap (evidence 08) places Semantic Binding vNext AFTER
Workspace/Scope Foundation + Runtime Context/Provenance-v2, not before.

**Decision D is explicit and consistent with accepted contracts.**
