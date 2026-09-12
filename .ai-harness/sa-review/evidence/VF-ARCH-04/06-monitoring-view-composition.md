# VF-ARCH-04 · Evidence 06 — Decision E + F: Monitoring View Composition and Inspector vs Monitoring

## 1. Decision E statement

**Monitoring is scope-centric and projection-only. It answers "Scope/Area Y ra
sao?" (what is the state of scope/area Y). A workspace/scope may have 0..N
monitoring views composed from shared widget categories, all projecting the
same ARCH-03 observation/event facts.**

## 2. Scope-centric composition

- Monitoring views are bound to a **scope** (or area = a named grouping within
  a scope), never to an individual object (that is the Inspector's job).
- A workspace/scope may declare **0..N views** (e.g., Process Overview, Line
  Overview, Quality, Alarms) — no single mandatory dashboard.
- Views are **compositions** of widget categories; the composition is domain
  content, the widget *categories* are platform primitives.
- Composition and views are **projection-only**: they cache/index but never
  mutate runtime truth (ARCH-03 §2).

## 3. Baseline widget categories (frozen as categories, not final schemas)

| Category | Renders |
|---|---|
| numeric / text | current scalar value + unit + quality |
| status / boolean | on/off, open/closed, healthy/blocked state |
| table | tabular list of values/rows |
| alarm list | projection of current alarm conditions/states (not an independent store) |
| event timeline | projection of the event stream (bounded window) |
| live chart | bounded **current-run** Live Series (not Historian) |
| gauge / level / bar | analog or level representation of a scalar |
| equipment card | compact per-equipment summary (drill-down to Inspector) |
| quality summary | aggregate quality view (capability-gated) |

These are **categories** — the concrete widget schema/layout is a later
non-decision (evidence 09).

## 4. Data authority (from ARCH-03)

- **Live chart** = bounded current-run Live Series; **never** presented as a
  durable Historian. Run boundary is explicit.
- **Event Timeline** and **Alarm List** are projections over ARCH-03 contracts.
  Mutable **Alarm Condition/State** (ack/clear lifecycle) must never rewrite the
  historical **Alarm Event** fact.
- **Alarm List is not an independent store** — it is a projection of alarm
  conditions/states with the same authority as the Inspector's Alarms tab.
- **Run Result** (finalized summary) is distinct from the live view; Monitoring
  may show it as a summary, not as a warehouse.

## 5. Capability-driven inclusion/exclusion

- Widgets/tabs appear when the corresponding capability is `available`.
- `not_applicable` → omitted or N/A (no empty fake panel).
- `not_ready`/`required-missing` → visible with explicit blocker.
- `restricted` → visible within limits.
- `degraded`/`error` → visible with degraded styling + reason.
- Never hard-coded by workspace name.

## 6. Drill-down

A Monitoring widget may drill down to an object → this opens the **Context
Inspector** for that object, preserving the origin scope/run context. The
drill-down does not change the Monitoring scope.

## 7. Decision F — Inspector vs Monitoring

| Axis | Context Inspector | Monitoring |
|---|---|---|
| Question | "Object X ra sao?" | "Scope/Area Y ra sao?" |
| Granularity | object-centric | scope/area-centric |
| Scope | one selected object (+ its context) | one selected scope/area |
| Composition | generic tabs + capability-driven domain tabs | 0..N views of widget categories |
| Data | same ARCH-03 facts, filtered to the object | same ARCH-03 facts, aggregated for the scope |
| Mutation | projection-only | projection-only |
| Truth | shares the same observation/event facts | shares the same observation/event facts |

**Same facts, different perspective.** Neither is a second store; the two must
not duplicate mutable state (ARCH-03 §8). A value shown in both must come from
the same underlying observation/event fact.

## 8. Mapping to current repo

| Frozen concept | Current precedent |
|---|---|
| Scope-centric monitoring | `index.html` Telemetry/Alarms/Trends panes (scope = whole plant) |
| Equipment cards | `assy_demo.js` Frame A sub-line cards + Frame B status cards |
| Alarm list as projection | `app.js` `APP.alarms` (projection of `/alarms`) |
| Live chart bounded | `telemetry/ring_buffer.py` (bounded store, maxlen) — concept precedent |
| Object drill-down → Inspector | `assy_demo.js` station/WIP card → `ctrlB` inspector |
| 0..N views per scope | `index.html` multiple panes; `assy_demo` Frame A + Frame B |

**Decision E (scope-centric, projection-only) and Decision F (Inspector vs
Monitoring) are explicit.**
