# VF-ARCH-06 · Evidence 02 — Decision B: Target SH WTP hierarchy mapping

## 1. Decision statement

**SH WTP maps losslessly onto the frozen ARCH-01 hierarchy using ONLY
generic/representative scope names where site truth is not authoritative. No new
platform concept is introduced; illustrative mappings are marked as such.**

## 2. Frozen mapping (representative, evidence-safe)

```
SH-WTP = Workspace
 └─ <process-area / unit> = child Simulation Scope (hierarchical; container-only
 │   or executable per ARCH-01)
 └─ <equipment / instrument> = Simulation Object
```

Rules:
- Exact site topology is **evidence-dependent** and NOT asserted here. Scope
  names below are **illustrative** placeholders only.
- Continuous/Batch/Discrete are **archetypes**, not one-engine-per-workspace
  assumptions (ARCH-01 terminology).
- A scope may be **executable** (owns a runtime) or **container-only** (groups
  child scopes/objects); executability is a separate capability, never implied.

## 3. Illustrative representative scopes (marked illustrative)

| Illustrative scope | Role | Fidelity note |
|---|---|---|
| Intake / raw-water | child Scope | illustrative only |
| Coagulation-flocculation-sedimentation | child Scope | illustrative only |
| Filtration | child Scope | illustrative only |
| Disinfection | child Scope | illustrative only |
| Storage / distribution | child Scope | illustrative only |

These are **not** site truth: they echo the WTP mini-engine's stage names
(evidence 01 §2.1) as *representative* process areas, not a claimed SH WTP
topology.

## 4. Consistency with ARCH-01

| ARCH-01 rule | Mapping |
|---|---|
| Workspace → Scope → Object | SH-WTP Workspace → process-area Scopes → equipment/instrument Objects |
| Container vs executable scope | process areas may be container-only or executable |
| Federated child independently addressable | a child scope is addressable in its own right |
| Structural identity ≠ PIM canonical id | VF structural ids distinct from PIM ids (evidence 04) |
| Archetype is a label, not an engine | SH WTP = continuous archetype; engine selection at scope/runtime level (ARCH-01/ARCH-02) |

## 5. What this gate does NOT do

- No site topology, no `SourceMapped`/`SiteVerified`/control-interlock claims.
- No fidelity raise beyond `logical_only` (PH00 B10).
- No one-workspace-one-engine assumption (B3: `runtime.engine: continuous_process`
  is the discriminator; `vf-core` is not an engine discriminator).

**Decision B is explicit and evidence-safe.**
