# VF-ARCH-06 · Evidence 08 — Decision H: vNext implementation roadmap

## 1. Decision statement

**The ordered implementation roadmap is frozen; each gate is one authorization
slice, dependency-ordered, and no gate begins here.**

## 2. Ordered roadmap (dependency-preserving)

```
G1  Workspace / Scope Foundation
G2  Runtime Context + Provenance v2
G3  Observation / Event / Alarm implementation alignment
G4  Composition Graph + Coordinator + Typed Ports
G5  TIPA Workspace / ASSY federation migration
G6  Shared hierarchical UI primitives
G7  Hierarchical Scenario / Run Control
G8  VF Platform vNext Regression Baseline
G9  Semantic Binding vNext
G10 Resume SH WTP runtime roadmap
```

## 3. Dependency rationale (repo-first)

| Gate | Depends on | Why (frozen evidence) |
|---|---|---|
| G1 Workspace/Scope Foundation | ARCH-01/ARCH-02 | no `Workspace`/`Scope` class exists today (evidence 01); `configs/workspaces/` absent (B9) |
| G2 Runtime Context + Provenance v2 | G1 | provenance threading needs workspace identity (B8: dedicated CORE gate, not folded into PH01) |
| G3 Observation/Event/Alarm alignment | G1, G2 | projection contracts (ARCH-03) sit on identity + provenance |
| G4 Composition Graph + Coordinator + Typed Ports | G1 | coordinator/composition over scopes (ARCH-02) |
| G5 TIPA/ASSY federation | G1–G4 | ASSY migration (ARCH-05) needs foundation + coordinator |
| G6 Shared hierarchical UI primitives | G1, G3 | UI hierarchy (ARCH-04) needs structural identity + projection facts |
| G7 Hierarchical Scenario/Run Control | G4, G5 | scenario/run control across scopes (ARCH-02 command levels) |
| G8 VF Platform vNext Regression Baseline | G1–G7 | regression baseline proves foundation + ASSY + continuous together |
| G9 Semantic Binding vNext | G1, G2, G8 | binding needs identity + provenance + proven foundation (B8, ALIGN-01) |
| G10 Resume SH WTP runtime | G1–G9 | SH WTP resumes only after foundation + binding + regression baseline |

One-gate-at-a-time governance: no gate may begin until its predecessor's
acceptance evidence is SA-accepted; overlapping so much that sequential
governance becomes meaningless is a critical risk (evidence 10).

## 4. ASSY regression protection (cross-cutting)

G1–G10 must run the **ASSY regression oracle** (ARCH-05 evidence 06, including
the C01 functional-semantics oracle) + **continuous/compressor baseline tests**
before being accepted. Shared-infrastructure changes (G1–G4, G6–G9) must not
break ASSY (ARCH-05 decision J fail-safe).

## 5. What the roadmap does NOT do here

No gate is started; no tests are written; no names/boundaries are implemented.
Gate names may be refined at implementation time as long as dependency logic and
one-gate-at-a-time governance are preserved (Issue #45 permission).

**Decision H is explicit and dependency-aware.**
