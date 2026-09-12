# VF-ARCH-05 · Evidence 07 — Decision G: UI preservation boundary

## 1. Decision statement

**The accepted ASSY UX remains unchanged until implementation migration. This
gate freezes only the preservation boundary — no frontend implementation.**

## 2. Preservation mapping (unchanged until migration)

| ASSY UX element | Preserved | Source |
|---|---|---|
| Frame A/B hierarchy + navigation precedent | unchanged | `ui/static/assy_demo.js` (`openFrameB`/`closeFrameB`, Frame-A top-bar router) |
| Line / sub-line visual center | unchanged | `assy_demo.js` line layout canvas, sub-line cards |
| Station / WIP interaction | unchanged | `ctrlB.selectWip`, station cards |
| Context Inspector domain extensions (quality/genealogy/checklist/retest/reinspect) | unchanged | `ctrlB` inspector bindings, OPS-03 capability-driven binding |
| Platform shell / run-control integration (ARCH-04) | unchanged | `/assy-demo/reset|step|…`, ARCH-04 Floating Control contract |

## 3. What migration may later change (implementation phase, NOT now)

- Re-host the same Frame A/B content inside the shared ARCH-04 shell/content
  region (context strip, breadcrumb) — **without** altering the ASSY domain
  presentation itself.
- Feed the Frame A/B context from the migrated structural path
  `TIPA/ASSY/ASSY-SLnn` instead of the standalone demo's local selection — the
  visible sub-line cards remain the same.

## 4. What migration must NOT change

- Frame A six-card overview / Frame B per-sub-line detail interaction model;
- station/WIP inspector tabs and capability-driven domain extensions;
- quality/genealogy/checklist/retest/reinspect surfaces;
- the run-control integration contract frozen in ARCH-04 (context-aware,
  command-semantics preserving).

## 5. No frontend implementation in this gate

No component code, no CSS, no framework migration, no new routes. The UI
preservation boundary is descriptive only.

**Decision G is explicit.**
