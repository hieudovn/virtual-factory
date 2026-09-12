# VF-ARCH-04 · Evidence 07 — Decision G: Archetype presentation patterns

## 1. Decision statement

**Continuous, Discrete and Batch each have a presentation *pattern* — not a
final label and not a mandatory layout. All three fit one shared architecture
(shell + hierarchy + floating control + inspector + monitoring) while keeping
distinct content organization. Unified architecture ≠ identical layout.**

## 2. The one shared architecture (all archetypes)

```
Platform Shell (chrome, context strip, global nav, health surface)
  ├─ Floating Simulation Control (run control primitive)
  ├─ Context Inspector (object-centric, tabbed, projection-only)
  ├─ Monitoring View Composition (scope-centric, 0..N views)
  └─ Content region ← archetype-specific domain experience
```

The **shared** part is the frame; the **archetype-specific** part is the content
region: what views exist, what domain extensions appear, how objects are laid
out.

## 3. Discrete / ASSY pattern (reference experience)

- **Organization**: line → sub-line → station → WIP/unit hierarchy.
- **Scope navigation**: overview cards (Frame A) → per-sub-line detail
  (Frame B); cards grouped by domain grouping (hydraulic/thermal).
- **Object-centric**: station / WIP selected → Context Inspector.
- **Domain extensions (Inspector)**: Quality, Genealogy, Checklist, Retest,
  Reinspect.
- **Monitoring**: line/station status cards, WIP, quality summary, MES message
  projection.
- **Reference**: the accepted ASSY UX (`assy_demo.html`/`js`) is preserved as
  the Discrete Experience (evidence 09).

## 4. Continuous pattern (SH WTP illustrative)

- **Organization**: process/area → equipment → instrument hierarchy; favors
  process/monitoring/analysis organization, **not** forced into line/station
  layout.
- **Scope navigation**: process-flow graph (P&ID-style) + area tree.
- **Object-centric**: equipment/instrument selected → Inspector.
- **Domain extensions (Inspector)**: Process, Control, Balance, Quality,
  Parameters.
- **Monitoring**: process overview, trend/analysis views, threshold alarms,
  balance/quality summary.
- **Rule**: Continuous workspace UX is **not** forced into ASSY line/station
  layout (critical risk explicitly rejected).

## 5. Batch pattern

- **Organization**: recipe → phase → material/batch lot.
- **Scope navigation**: recipe/phase tree + material flow.
- **Object-centric**: batch/lot/phase selected → Inspector.
- **Domain extensions (Inspector)**: Recipe, Phase, Material, Hold-Release,
  Genealogy.
- **Monitoring**: phase status, material/hold-release, genealogy summary.
- **Rule**: Batch **extends** shared primitives with recipe/phase/material; it is
  **not** forced into Discrete (line) or Continuous (process) layout.

## 6. What the three patterns share (frozen) vs differ (not frozen)

| Shared (frozen) | Archetype-specific (pattern, not final layout) |
|---|---|
| Shell chrome + context strip | content region organization |
| Hierarchy + connectivity navigation | which views exist (0..N) |
| Floating Simulation Control | domain controls (station ops / process setpoint / phase advance) |
| Inspector generic tabs | Inspector domain extension tabs |
| Monitoring widget categories | which widgets compose each view |
| Capability-driven visibility | which capabilities are declared |

## 7. Fit test (one architecture, three patterns)

- One shell hosts all three: **yes** (content region swaps archetype experience).
- No identical layout imposed: **yes** (patterns, not layouts).
- ASSY UX preserved, Continuous/Batch not forced into it: **yes**.
- Capability state (not archetype name) drives domain extensions: **yes**
  (evidence 08).

**Decision G is explicit; the three patterns fit one shared architecture
without identical layouts.**
