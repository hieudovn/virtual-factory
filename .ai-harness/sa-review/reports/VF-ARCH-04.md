# VF-ARCH-04 — Freeze product/UI interaction architecture: shell, context, monitoring and capability-driven composition

| Field | Value |
|---|---|
| Task ID | `VF-ARCH-04` (GitHub Issue #43) |
| Parent | Issue #39 `VF-vNEXT-ARCH` (umbrella architecture program) |
| Prerequisite | ARCH-03 / Issue #42 CLOSED by SA as `completed` |
| Repository | `hieudovn/virtual-factory` |
| Gate type | Architecture / design gate — documentation & evidence only (no production implementation) |
| Architecture baseline | ARCH-01 @ `41903e18…` + ARCH-02 @ `40454487…` + ARCH-03 @ `392401bd…` |
| Production baseline | canonical `main` lineage (`f5261c8…`; unchanged) |
| Production code changed | **NO** (only `.ai-harness/`) |
| ARCH-05 started | **NO** |

## 1. Objective

Freeze the product/UI interaction architecture so many workspaces / nested
scopes / archetypes share one platform shell without forcing one identical
screen model. Target principle: **Unified architecture ≠ identical layout.**

```
Platform Shell (chrome, context strip, global nav, health surface)
  ├─ Floating Simulation Control (run control primitive)
  ├─ Context Inspector (object-centric, projection-only)
  ├─ Monitoring View Composition (scope-centric, 0..N views)
  └─ Content region ← archetype-specific domain experience
```

## 2. Repo-first discovery (evidence 01)

Verified seams: generic continuous SCADA shell (`index.html`/`app.js`/
`editor.js`, routes `/`, `/telemetry/latest`, `/alarms`, `/start`, `/stop`,
`/step`, `/reset`, `/api/fault`, …), accepted ASSY Discrete Experience
(`assy_demo.html`/`js`/`css`: `vf-topbar` context strip, Frame A sub-line cards,
Frame B per-sub-line detail, Context Inspector `ctrlB`, capability-driven OPS-03
binding), MES demo (`demo_assy_mes.html`), and `runtime_service.py`. Every seam
classified into: reusable platform primitive / ASSY-discrete domain UX /
generic-legacy platform capability / demo-only / implementation detail.

## 3. Frozen decisions (evidence 02–09)

| Decision | Frozen contract |
|---|---|
| **A — Platform Shell** | One shared chrome (context strip, global nav, breadcrumb/hierarchy, run/scenario visibility, floating control slot, health surface, workspace/scope switching). **Anti-responsibilities**: never owns domain truth, never duplicates monitoring state, never a God UI, never hosts domain/plant controls, never hard-codes by name, never imposes identical layout. |
| **B — Hierarchy + context** | Workspace→Scope→Object path + run/scenario; tree = structure, graph = connectivity; container vs executable scope; federated child independently addressable; selected object ≠ selected scope; no name hard-coding. |
| **C — Floating Simulation Control** | Minimal run-control primitive: Time, Run/Pause, Step, Reset, Speed + compact run/scenario context. **Excludes** scenario editor, replay editor, domain process controls, plant-control actions. Bound to active scope/run; commands via ARCH-02 interfaces. |
| **D — Context Inspector** | Object-centric, projection-only. Generic tabs: Overview, State, Signals, current-run Live Trend, Events/Alarms, Actions, Evidence/Provenance + capability-driven domain extensions. Not a second domain state store. |
| **E — Monitoring** | Scope-centric, projection-only, 0..N views per scope. Widget categories: numeric/text, status/boolean, table, alarm list, event timeline, live chart, gauge/level/bar, equipment card, quality summary. Live chart ≠ Historian; Alarm List ≠ independent store. |
| **F — Inspector vs Monitoring** | "Object X ra sao?" vs "Scope/Area Y ra sao?" — same facts, different perspective, no duplicate mutable state. |
| **G — Archetype patterns** | Discrete (line/sub-line/station/WIP), Continuous (process/equipment/instrument, monitoring/analysis), Batch (recipe/phase/material). Patterns, not mandatory layouts. |
| **H — Capability-driven UI** | `available`/`not_applicable`/`not_ready`/`restricted`/`degraded`/`error`/`required-missing` → UI matrix. Never hard-coded by workspace name. |
| **I — Health/readiness** | UI displays + shows blockers + navigates; never invents score, upgrades, hides blocker, or becomes evaluator. |
| **J — Action authority** | simulation / runtime-model / plant-operational labels; no implied plant control; all mutations via ARCH-02 interfaces. |
| **K — ASSY preservation** | Accepted ASSY UX = reference Discrete Experience; maps to Shell/Inspector/Monitoring without loss or rewrite assumptions; unchanged until ARCH-05. |
| **L — SH WTP mapping** | Continuous conceptual mapping (area/equipment/instrument; process/control/balance/quality) — illustrative only, no invented site truth. |

## 4. STOP-condition assessment (evidence 09 §3)

None triggered: ASSY UX preserves without conflict; one shell supports all three
archetypes as patterns; no workspace-name hard-coding (capability-driven
precedent already exists); no second authority invented (ARCH-03 provider +
aggregation remain the authority); no framework migration; plant-control
deferred; ARCH-05 NOT started.

## 5. Non-decisions (deferred)

Frontend component code; CSS/theme; framework migration; dashboard
persistence/layout engine; final widget schemas; real Historian; alarm workflow
engine; TIPA/ASSY runtime migration; SH WTP runtime/domain models; semantic
loader/binding; real plant-control authorization; snapshot/checkpoint/replay
editor; advanced RBAC; production provenance storage.

## 6. Acceptance

| Criterion | Result |
|---|---|
| Platform Shell responsibilities explicit and bounded | PASS (02) |
| Hierarchy/context model explicit, consistent with ARCH-01 | PASS (03) |
| Floating Simulation Control explicit and minimal | PASS (04) |
| Context Inspector object-centric and projection-only | PASS (05) |
| Monitoring scope-centric and projection-only | PASS (06) |
| Inspector vs Monitoring distinction explicit | PASS (06 §7) |
| Continuous/Discrete/Batch fit one architecture without identical layouts | PASS (07) |
| Capability/readiness drives UI honestly, no workspace-name hard-coding | PASS (08) |
| Action authority distinction explicit | PASS (08 §3) |
| ASSY maps without loss/rewrite assumptions | PASS (09 §1) |
| SH WTP maps conceptually without invented site truth | PASS (09 §2) |
| Later migration/implementation concerns deferred | PASS (09 §4) |
| No production code changed | PASS (only `.ai-harness/`) |

## 7. Evidence

`.ai-harness/sa-review/evidence/VF-ARCH-04/` — 9 files (01…09).

## 8. Final status

```text
VF-ARCH-04 — READY FOR SA REVIEW
```

PM does not self-certify COMPLETE/CLOSED. ARCH-05 is NOT started; all
implementation non-decisions remain deferred.
