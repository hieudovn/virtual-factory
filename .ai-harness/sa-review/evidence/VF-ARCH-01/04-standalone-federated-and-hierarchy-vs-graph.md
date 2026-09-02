# 04 — Standalone / Federated Contract & Hierarchy-vs-Graph Contract

## 4.1 Standalone vs federated scope (Issue #40 §D)

The contract for a reusable subsystem such as ASSY, already demonstrated by
`AssyDemoComposition` + `AssyLineRuntime`:

1. **Same domain/runtime semantics in both modes.** A scope's domain behavior
   does not change when it is hosted standalone vs federated under a parent.
   In the repo, `AssyLineRuntime` is the same class and semantics whether one
   sub-line is run alone or six are composed.
2. **Parent supplies host/composition context, not business-logic rewrite.**
   The parent (`AssyDemoComposition` / a future ASSY scope under TIPA) supplies
   identity, config normalization, feed policy (DEMO-only), and selection — it
   does not rewrite `AssyLineRuntime` business semantics.
3. **Child retains its own local runtime/config boundary.** Each
   `AssyDemoContext` owns a deep-copied config and an isolated `AssyLineRuntime`;
   runtime state is not shared across contexts.
4. **Parent orchestration is not child domain authority.** The composition
   layer steps contexts according to a demo policy; it does not become the
   authority over AP/WIP/quality semantics (which stay in the runtime +
   station contracts).

Frozen consequence: **standalone and federated execution of a scope MUST be the
same domain runtime**, differing only in hosting context. No second runtime /
composition engine may be introduced to make a scope federate.

## 4.2 Hierarchy vs graph (Issue #40 §E)

| Axis | Hierarchy (containment) | Graph (connectivity) |
|---|---|---|
| Purpose | Management, navigation, addressing, deployment grouping | Process, material, energy, information, utility, dependency, coordination connectivity |
| Shape | Tree — one containment parent per node | Graph — many edges, no single-parent constraint |
| Examples (repo) | TIPA → ASSY → ASSY-SL01..06; workspace → scope → object | `core/plant_graph.py` `PlantGraph` nodes+edges; `tipa.py` flow edges (SSO2 → buffer → AP01..06 → quality → sink/rework); PIM `FLOWS_TO`/process relationships |
| Identity | Scope path (`workspace/…/scope`) | Edge endpoints reference object/scope ids; no path authority |
| Cardinality | 1 parent per node | N edges per node |

Frozen rules:

1. A scope has **exactly one containment parent** and **zero or more graph
   relationships**.
2. Containment and connectivity are **independent axes**; a graph edge does not
   imply containment, and containment does not imply a process edge.
3. Graph connectivity is not modeled as nested hierarchy (no "child = downstream").
4. **This gate freezes only the structural distinction.** Graph edge kinds and
   port payloads are NOT implemented here (deferred to ARCH-02+).

## 4.3 Runtime-state isolation by scope (Issue #40 frozen intent)

- Internal runtime state is isolated per scope (per `AssyDemoContext` today).
- Cross-scope interaction will later occur **only through declared
  contracts/ports**; this gate defines the structural boundary (scope isolation)
  but does **not** implement ports or synchronization.
