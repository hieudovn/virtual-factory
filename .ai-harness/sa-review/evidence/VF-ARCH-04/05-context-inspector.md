# VF-ARCH-04 · Evidence 05 — Decision D: Context Inspector (object-centric)

## 1. Decision statement

**The Context Inspector is object-centric and projection-only. It answers
"Object X ra sao?" (what is the state of object X). It is a viewer over
ARCH-03 Observation/Event/Capability/Provenance facts — never a second domain
state store, and never the place to mutate runtime truth.**

## 2. Interaction loop (frozen)

```
select object → inspect → observe → understand → act/simulate → evidence
```

The Inspector opens when an **object** is selected (from the hierarchy tree,
the connectivity graph, or a Monitoring widget drill-down). It is bound to:

- structural identity of the object (scope + object id), and
- the current run/scenario context (so Live Trend is run-scoped).

## 3. Generic tabs (shared across archetypes)

| Tab | Content | Authority |
|---|---|---|
| Overview | identity, type, readiness, current capability state | ARCH-01 identity + ARCH-03 readiness/capability |
| State | current runtime state snapshot for the object | ARCH-02/ARCH-03 observation (projection) |
| Signals | signal/measurement list with current values + quality | ARCH-03 observation / telemetry projection |
| Live Trend | bounded **current-run** live series for the object | ARCH-03 Live Series (bounded, ≠ Historian) |
| Events / Alarms | event timeline + alarm list filtered to the object | ARCH-03 Event/Alarm projection |
| Actions | action surface scoped to the object | evidence 08 (authority-labeled) |
| Evidence / Provenance | provenance + evidence for the object | ARCH-03 provenance/evidence (VF ≠ PIM) |

Tab visibility and content are **capability-driven**: if the object has no
alarm capability, the Alarms tab is `not_applicable` (omitted or shown N/A) —
never a fake empty list.

## 4. Capability-driven domain extensions (not hard-coded by archetype name)

| Archetype | Domain extension tabs | Enabled by |
|---|---|---|
| Discrete / ASSY | Quality, Genealogy, Checklist, Retest, Reinspect | quality/genealogy capability available |
| Continuous | Process, Control, Balance, Quality, Parameters | process/control/balance capability available |
| Batch | Recipe, Phase, Material, Hold-Release, Genealogy | batch recipe/phase/material capability available |

The extensions are **declared by capability state** (ARCH-03), not by
`if workspace == "ASSY"`. Two workspaces in the same archetype with different
capability sets show different (honest) tabs.

## 5. Authority rules (projection-only)

- The Inspector **reads** from Observation/Event/Capability/Provenance
  contracts; it **caches/indexes but never mutates** runtime truth.
- The Inspector is **not** a second domain state store (ARCH-03 §2, §8).
- Actions surfaced in the Inspector are **authority-labeled** (evidence 08):
  simulation / runtime-model / plant-operational — never presented as an
  unlabeled "do it" button.
- The Inspector never upgrades evidence or relabels synthetic as site truth.

## 6. Empty / not-ready / not-applicable states

| State | Presentation |
|---|---|
| `not_applicable` | tab/panel omitted or labeled N/A with reason |
| `not_ready` / `required-missing` | panel visible with explicit blocker; never silently hidden |
| `restricted` | panel visible within permitted limits |
| `degraded` / `error` | panel visible, degraded styling + reason |
| no data (empty) | explicit "no data for current run" (distinct from "not applicable") |

## 7. Mapping to current repo

| Frozen concept | Current precedent |
|---|---|
| Object-centric inspector | `assy_demo.js` Context Inspector (`ctrlB`) bound to `_selectedStation`/`_selectedWipId` with `_contextType` (sso2/rso2/offline) |
| Run-scoped live trend | `assy_demo.js` snapshot fetch `/assy-demo/sub-line/{id}` + observations |
| Structural identity | `_subLineId` + selected object |
| Domain content (not shell) | inspector lives inside ASSY Frame B content region |
| Capability-driven (no hard-code) | ASSY OPS-03 "Operation Inspector binding (capability-driven, no AP hard-code)" |

The ASSY Context Inspector is the **reference implementation** the frozen
contract generalizes. ARCH-04 does not rewrite it; it declares the contract
that future workspaces will share the same *form* (object-centric, tabbed,
projection-only) with different *content* (capability-driven tabs).

**Decision D is explicit, object-centric, projection-only.**
