# Virtual Factory — Canonical UI/UX Design Guide

> **Canonical UI/UX Design Source of Truth**  
> Version 1.1 — 2026-08-11

---

## Governance Rule

This document is the canonical UI/UX design source of truth for Virtual Factory.

Milestone-specific UI specifications may specialize this guide for a particular demo,
plant, production line, or workflow, but must not redefine its core design principles
without an explicit architecture/design decision approved by SA/PO.

If a milestone-specific document conflicts with this guide, the conflict must be
reported and resolved explicitly. Do not silently introduce a new design language.

---

## AI / Agent Rule

Before designing or modifying Virtual Factory UI/UX,
read this canonical guide first.

Do not create a new visual style, interaction model,
color semantics, shopfloor representation, or motion language
unless the task explicitly requires a design-system change.

When requirements appear to conflict with this guide,
report the conflict before implementation.

---

## 1. Design Intent

Virtual Factory UI must present a manufacturing reality clearly and professionally.

The user should understand:

- where material/WIP/product is located;
- how it moves;
- which production operation is occurring;
- which station is active;
- whether production is normal, blocked, held, or released;
- what manufacturing information and data was generated;
- how physical events relate to data, quality, genealogy, alarms, and events.

The UI is not merely a dashboard.  
The physical manufacturing scene is the primary context.  
Information and analytics are layered over that physical context.

---

## 2. Design Style — Industrial Operations Cockpit

Canonical style: **Industrial Operations Cockpit**

Characteristics:

- neutral, industrial, professional, engineering-oriented;
- modern but restrained;
- information-rich without visual clutter;
- suitable for BOD, production management, engineering, and IT audiences.

Do NOT use:

- cyberpunk / excessive neon;
- heavy glassmorphism;
- game UI;
- consumer-app aesthetics;
- decorative animation;
- generic BI-dashboard-first layout;
- unnecessary 3D.

The UI should look like a modern industrial operations environment, not a futuristic entertainment interface.

---

## 3. Core UX Principles

### 3.1 Physical-First

The production reality is the primary visual layer.

Preferred hierarchy:

```
Plant / Line → Station → Carrier / WIP → State → Information
```

Do NOT build:

```
Dashboard → KPI cards → charts → small factory illustration
```

Shopfloor/physical manufacturing visualization MUST dominate the main screen.

### 3.2 Progressive Disclosure

Three information levels:

| Level | Name | Content |
|-------|------|---------|
| **L0** | Ambient | Station ID, operation label, WIP/carrier identity, main operational state, quality state |
| **L1** | Contextual Peek | Current operation, attempt, latest result, short measurement summary, active issue (hover/lightweight) |
| **L2** | Inspector | Genealogy, measurements, checklist, tests, quality history, events, timestamps, related identities (drawer/panel) |

Do NOT display every available data field at once.

### 3.3 Semantic Color

Color MUST primarily convey state and meaning. Do NOT assign arbitrary decorative colors to each station.

| Meaning | Color | Usage |
|---------|-------|-------|
| Neutral / normal | Gray / muted neutral | Idle, empty, default |
| Active / running | Restrained teal/cyan | Processing, operating |
| PASS / healthy | Green | Quality pass, completed |
| Warning / hold / pending | Amber | HOLD, retest pending, reinspect pending |
| FAIL / NG / alarm | Red | Quality failure, FAILED_FINAL |
| Released / completed | Cyan-green / bright teal | RELEASED, finished good |
| Selected object | Dedicated selection treatment | Must not conflict with quality state |

**MUST**: Never rely on color alone. Use text/icon/state label together with color.

### 3.4 State Change Over Decorative Animation

Animation exists to communicate manufacturing state changes. Do NOT animate simply to make the interface look dynamic.

Use: short movement, transition, state highlight, activity pulse, synchronized index movement.

Avoid: continuous decorative movement, excessive blinking, complex cinematic effects, unrelated particles or glowing.

### 3.5 One Source of Visual Truth

UI MUST render reality from detached projection/snapshot/read models.

The frontend must NOT invent manufacturing state.

A pallet may visually move only after the underlying simulation state indicates an index transition.

UI animation may interpolate between two valid states, but may NOT create additional manufacturing truth.

### 3.6 Physical and Information Layers Are Linked

Data MUST remain contextually related to the physical object or event that generated it.

Examples:
- AP06 test result relates visibly to AP06 and the selected WIP;
- AP04 genealogy relates to parent and child identities;
- event entries can highlight the relevant station/WIP;
- an alarm/quality exception identifies its blocking physical context.

Do NOT separate all manufacturing information into unrelated dashboards.

### 3.7 BOD View First, Technical Depth Second

Main screen SHOULD communicate production behavior within ~5-10 seconds.

One UI supports two audiences:

**Executive / BOD**:
- production is moving; assembly occurs; quality detects an issue; the line reacts; production resumes; product is released.

**Engineering / IT**:
- WIP identity; carrier identity; genealogy; quality records; measurements; checklist; events; timestamps.

Detailed exploration available through interaction, not on the main canvas.

### 3.8 Industrial Restraint

Prefer: clean geometry, structured spacing, muted industrial surfaces, restrained accents, clear hierarchy.

Avoid visual noise.

---

## 4. Visualization Technology

Preferred manufacturing scene approach:

**SVG-first 2D Shopfloor Renderer + HTML/CSS overlays**

- **SVG**: conveyor, station geometry, production flow, material paths, carriers, WIP/product tokens, feeder paths, highlights, movement transitions.
- **HTML/CSS**: inspector drawers, tables, event lists, controls, badges, detailed information panels.

SVG is preferred because it is: scalable, projector-friendly, crisp, easy to layer and interact with, well suited to deterministic 2D manufacturing visualization.

Do NOT introduce 3D or a game engine unless future requirements clearly justify it.

---

## 5. Shopfloor Visual Layers

Canonical scene layer stack:

```
L0  Background / shopfloor zone
L1  Conveyor / material paths
L2  Stations / buffers / line-in / line-out
L3  Carrier / pallet
L4  WIP / material / product
L5  Operational state
L6  Quality / alarm / exception
L7  Selection / interaction
L8  Temporary movement / event effects
```

Higher layers must NOT obscure the meaning of lower physical layers.

---

## 6. Physical Visual Grammar

### 6.1 Station

A station MUST contain: station ID, short operation label, activity/state indicator, occupied state, important exception indicator.

Do NOT turn each station into a mini-dashboard.

### 6.2 Conveyor / Production Path

The conveyor or production path MUST be visually recognizable as a physical production element.

Use: clear lane/path, indexed positions, direction indication, station anchors.

Do NOT imply continuous conveyor movement where the manufacturing logic is indexed stop-and-go.

### 6.3 Carrier / Pallet

Carrier identity and WIP identity are separate. Carrier MUST have its own visual token. Do NOT merge pallet/carrier identity into WIP identity.

### 6.4 WIP / Material / Product

Use simple industrial silhouettes or tokens. Prefer meaningful differentiation: raw/semi-finished, assembled product, finished/released product.

Do NOT require photorealistic graphics.

### 6.5 Buffer / Feeder

Represent upstream material sources as physical feeders/buffers rather than generic dashboard cards.

### 6.6 Line-In / Line-Out

The viewer SHOULD visually understand where material enters and where finished product exits.

---

## 7. Motion Language

Canonical motion vocabulary — reuse consistently:

| Term | Meaning |
|------|---------|
| `INDEX_SHIFT` | All carriers advance one position simultaneously (~400-650ms) |
| `LINE_IN` | Material/WIP enters line from feeder/buffer |
| `LINE_OUT` | Finished/released product exits line |
| `JOIN` | Assembly join: parents converge, child created |
| `WORK_PULSE` | Restrained activity pulse during processing |
| `HOLD_PULSE` | Blocking quality/production issue highlighted |
| `DATA_PULSE` | Physical event linked to information panel |

### Motion Principle

Motion communicates manufacturing behavior:

```
Normal:   STOP → WORK → READY → INDEX → STOP
Exception: WORK → FAIL → HOLD → RETEST → PASS → READY → INDEX
```

No forward visual motion while a line-level blocking HOLD is active.

---

## 8. Information Architecture

Canonical main-screen regions:

```
┌─────────────────────────────────────────────┐
│ Global Status / Context                     │
├──────────────────────────────────┬──────────┤
│                                  │ Inspector│
│   Physical Shopfloor Canvas      │ Drawer   │
│                                  │          │
├──────────────────────────────────┤          │
│ Context / Event Rail             │          │
├──────────────────────────────────┴──────────┤
│ Demo / Runtime Controls                     │
└─────────────────────────────────────────────┘
```

Shopfloor scene SHOULD occupy ~65-70% of primary visual attention.

---

## 9. Global Status

Compact, always visible. Typical content:

- Plant/line name;
- Simulation/operating time;
- Dwell/cycle (where semantically valid);
- Line state;
- Scenario;
- Playback speed;
- Small production summary.

When a blocking state exists, it takes precedence: e.g., `QUALITY HOLD — AP06 — MTR-0002`.

---

## 10. Inspector Model

Right-side inspector drawer. Read-only (unless future module defines control behavior).

**WIP sections**: Overview, Genealogy, Quality, Measurements/Data, Checklist/Tests, Events.

**Station sections**: Operation, Current WIP, Current activity, Quality state, Recent events.

Avoid modal dialogs that hide the shopfloor unnecessarily.

---

## 11. Event Rail

Concise, contextual events. Example:

```
12:14:02  AP04  MTR-0002 CREATED
12:16:04  AP06  FAIL
12:18:04  AP06  PASS #2
12:18:06  LINE  INDEX
```

Events MUST NOT resemble raw application logs. Selecting an event SHOULD highlight the related physical object.

---

## 12. Quality / Alarm Taxonomy

Do NOT mix manufacturing quality state with system alarm severity.

**Quality**: PASS, FAIL, NG, HOLD, RETEST, REINSPECT, FAILED_FINAL

**System/technical** (future): INFO, WARNING, ALARM

Keep these semantic families distinct.

---

## 13. Data Presentation

On the shopfloor canvas: only small data indicators (e.g., `CHECK COMPLETE`, `TEST PASS`, `3 MEASUREMENTS`, `QUALITY HOLD`).

Detailed values belong in the inspector.

For simulated data, MUST clearly indicate: **DEMO / SYNTHETIC DATA**. Do NOT imply simulated values are customer engineering specifications.

---

## 14. Genealogy UX

Compact representation, no full graph engine required:

```
Parent A ─┐
          ├── Join Operation ── Child
Parent B ─┘
```

Shopfloor highlights: join station, child, upstream feeder/parents. Detailed genealogy in inspector.

---

## 15. Visual Foundation

### Typography

Modern sans-serif. Suggested hierarchy:

| Level | Size | Usage |
|-------|------|-------|
| Screen/line title | 22-28px | Main heading |
| Section title | 16-18px | Panel headers |
| Station ID | 16-18px | Position labels |
| Station label | 11-13px | Operation descriptions |
| WIP ID / data | 12-14px | Identity, values |
| Metadata | 10-12px | Timestamps, secondary |

Use tabular numerals or light monospace for measurements, timestamps, IDs.

### Spacing

8px-based system: 4 (micro), 8 (base), 12 (compact), 16 (standard), 24 (section), 32 (major).

### Borders / Radius

Thin borders, 4-8px radius. Avoid excessive pill shapes.

### Elevation

Minimal shadows. Prefer hierarchy from surface contrast, spacing, borders, selection treatment.

---

## 16. Responsiveness / Viewports

**Primary**: 1920×1080 — must look professional on projector/display.  
**Secondary**: ~1366×768.

Requirements:
- Main production story visible without unusual zoom;
- Station IDs readable;
- Inspector does not destroy shopfloor readability;
- No unnecessary full-page scrolling for primary production scene.

Mobile is NOT a primary target unless explicitly required by a future milestone.

---

## 17. Interaction Model

| Action | Behavior |
|--------|----------|
| **Hover** | Lightweight contextual information |
| **Click/Select** | Persistent selection + inspector update |
| **Select WIP** | Highlight WIP, carrier, current station, optionally genealogy context |
| **Select Station** | Show operation, current WIP, state, recent events |
| **Select Event** | Highlight relevant physical object/context |

Avoid nested popovers and excessive transient panels.

---

## 18. Accessibility / Readability

- Do NOT encode state using color alone — use text/icon/label;
- Maintain useful contrast;
- Critical information MUST remain readable on projector;
- Avoid excessively small text;
- Important state changes MUST be visually obvious without precise mouse interaction.

---

## 19. Design Component Taxonomy

```
VFOperationsShell
├── GlobalStatusBar
├── ShopfloorScene
│   ├── MaterialFeed
│   ├── BufferNode
│   ├── ConveyorLane
│   ├── StationNode
│   ├── CarrierToken
│   ├── WipToken
│   ├── ProductToken
│   ├── FlowConnector
│   ├── JoinIndicator
│   └── LineOutput
├── ContextOverlay
│   ├── StateBadge
│   ├── QualityBadge
│   ├── ActivityIndicator
│   ├── HoldIndicator
│   └── DataAvailableIndicator
├── InspectorDrawer
│   ├── ObjectOverview
│   ├── GenealogyView
│   ├── MeasurementView
│   ├── ChecklistView
│   ├── QualityHistory
│   └── EventHistory
├── EventRail
└── ControlBar
```

Implementation technology and naming may vary. Conceptual responsibilities SHOULD remain stable.

---

## 20. Production Hierarchy / Parallel Sub-line Visualization

When a production line contains multiple parallel execution paths (sub-lines), use hierarchical visualization rather than rendering every sub-line at full station detail.

### Principles

1. **Production hierarchy**: `Plant → Production Line → Sub-line / Parallel Execution Path → Station → WIP / Event`. A Production Line is NOT the same as a Sub-line. Parallel execution paths inside one line SHOULD NOT be called independent lines.

2. **Distinguish concepts**:
   - **Production Line** — a main physical line (e.g., SSO2, RSO2, ASSY).
   - **Sub-line** — one parallel execution path within a production line.
   - **Process Definition** — reusable manufacturing logic (stations, routing, quality).
   - **Process Variant** — specialization of a process definition (e.g., different input variant, test profile).
   - **Runtime Instance** — one executing instance with its own state.

3. **Line overview**: When parallel sub-lines exist, provide a line-level overview showing all sub-lines with high-level state. Do NOT overload with station-level detail.

4. **Drill-down**: Selecting a sub-line drills into the detailed shopfloor visualization.

5. **Variant styling**: Variants MAY be visually distinguishable through labels, icons, neutral badges, or grouping. Variant styling MUST NOT consume semantic state colors.

6. **Avoid flattening**: UI terminology MUST follow the domain/physical hierarchy. Do not flatten sub-lines into top-level production lines.

7. **Context hierarchy**: Identity SHOULD distinguish `plant → line → sub_line → station → wip` when parallel sub-lines exist.

---

## 21. TIPA M6-S04B Pilot

M6-S04B is the first full pilot of this design system.

TIPA-specific flow: `SSO2 → PRE-ASSY → AP01 ... AP04 ... AP11 → Finished`. RSO2 feeds AP04.

Key demo states: normal multi-WIP, synchronized index, AP04 join, AP06 test, quality HOLD, retest PASS, AP08 visual quality, final release.

TIPA-specific station semantics belong in milestone/domain specifications. This canonical guide does NOT depend on TIPA-specific AP names.

---

## 22. Design Authority & Change Control

Changes that materially alter the following MUST be explicitly reviewed by SA/PO:

- Physical-first principle;
- Industrial Operations Cockpit style;
- Semantic color system;
- Progressive disclosure;
- Shopfloor scene architecture;
- Visualization technology direction;
- Motion semantics;
- Interaction model.

Minor visual improvements that preserve these principles MAY be made without redesigning the guide.

---

## 23. Relation to Milestone Documents

Milestone-specific documents MAY define: plant layout, production line topology, station semantics, customer-specific terminology, demo storyboard, required screens, temporary constraints.

They SHOULD reference this canonical guide:

```text
UI/UX design authority:
docs/ui/VIRTUAL_FACTORY_UI_UX_DESIGN_GUIDE.md
```

Do NOT duplicate the full canonical design guide into milestone files.

---

## 24. Document Quality

This guide MUST be:

- clear enough for an AI coding agent;
- clear enough for a UX designer;
- clear enough for a frontend engineer;
- avoid excessive prose where rules can be explicit;
- use MUST / SHOULD / MAY consistently;
- be implementation-aware but not framework-specific.

Figma is a design artifact. This Markdown guide in the repo is the canonical design authority.

---

## Document History

| Date | Author | Change |
|------|--------|--------|
| 2026-08-11 | PM | v1.1 — Added Section 20: Multi-Line / Repeated-Process Visualization |
| 2026-08-11 | PM | Initial canonical version 1.0 |
