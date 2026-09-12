# VF-ARCH-05 · Evidence 04 — Decision D: Identity/context migration

## 1. Decision statement

**Existing TIPA/ASSY/sub-line identities map losslessly onto ARCH-01 structural
identities and paths, while local runtime/object identities are preserved. This
mapping is distinct from PIM canonical semantic identity and from
`outputs.namespace` (PH00 §06).**

## 2. Identity mapping (lossless)

| Existing identity (source) | ARCH-01 structural identity | Evidence |
|---|---|---|
| TIPA (`plant_id`) | **Workspace** | `sub_line_identity.py` `AssyProductionLineIdentity(plant_id="TIPA", …)` |
| ASSY (`production_line_id`) | **child Simulation Scope** | same file |
| ASSY-SL01..06 (`sub_line_id`) | **child Simulation Scopes of ASSY** | `CANONICAL_TIPA_SUB_LINE_IDS` (exactly 6; error if ≠6) |
| variant `hydraulic`/`thermal` | scope metadata (input-process variant), not a scope level | `VALID_VARIANTS`; `CANONICAL_HYDRAULIC_IDS`/`CANONICAL_THERMAL_IDS` |
| station / AP / WIP / carrier | **Simulation Objects** | `line_runtime.py`, `wip.py`, `carrier.py` |

Rules:
- No flattening `line_id="ASSY-SL01"`; no "six ASSY lines".
- A sub-line is a Scope, never an Object; ASSY is a Scope, never a Workspace.
- The structural path of any object is `TIPA / ASSY / ASSY-SLnn / <object>`.

## 3. What is preserved vs what is introduced

| Concern | Status |
|---|---|
| Local runtime identity (`wip_id`, `run_id`, `source_event_id`) | **preserved** — migration must not alter them |
| Structural path | **introduced** as path metadata, derived from existing identity (no new IDs) |
| Canonical semantic identity | **NOT introduced here** — that is PIM's concern |
| `outputs.namespace` / `workspace_id` / `canonical_signal_id` | **three distinct concepts** (PH00 §06) — migration does not conflate them |

## 4. Non-conflation guard

- TIPA/ASSY/ASSY-SL structural ids are **VF runtime structural identity**, not
  PIM semantic ids and not `outputs.namespace`.
- Migration exposes the structural path for navigation/context (ARCH-04), but it
  does not create or mint canonical semantic ids.

## 5. Context model (ARCH-04 reuse)

The migrated identity feeds the ARCH-04 context strip exactly:

```
workspace=TIPA / scope=ASSY / scope=ASSY-SL03 / object=<station|AP|WIP|carrier>
+ optional run / scenario
```

No workspace-name hard-coding; capability state drives composition (ARCH-04 H).

**Decision D is explicit and non-conflating.**
