# VF-vNEXT-G26 — Comprehensive Test Plan / Coverage Matrix

Gate: `VF-vNEXT-G26` (comprehensive validation & UAT readiness)
Base: `3c83176ce2a8a504637dfe674ea30b2332bc7968` (G25 head)

## Principle

- Do NOT duplicate G1–G25 tests.
- Reuse the canonical baseline / full suite as the technical safety net.
- G26 adds only the missing layers: browser functional validation, compact UAT,
  UX sanity, and demo-scale stability.

## Coverage matrix

| Layer | Owner (existing) | G26 addition |
|---|---|---|
| Workspace / structural foundation (G1) | `test_workspace_*` (baseline) | — (reused) |
| Provenance (G2), observation/alarms (G3) | baseline groups | — (reused) |
| Composition / coordinator (G4) | baseline + G25 re-prove | — (reused) |
| Federation TIPA ASSY (G5) | `test_federation_tipa_assy.py` | browser FLOW A |
| Hierarchy UI (G6) | `test_ui_hierarchy.py` | — (reused) |
| Run control / lifecycle (G7) | `test_run_control.py` | browser lifecycle controls |
| G8 baseline invariants | `test_vnext_g8_*` | — (reused) |
| Semantic binding (G9) | baseline | — (reused) |
| SH-WTP readiness/structural/connectivity (G10–G12C) | baseline groups | — (reused) |
| T108/T106 runtimes (G13/G13B) | baseline groups | browser FLOW B live values |
| Projection/federation/evaluation/readiness (G14–G16) | baseline groups | — (reused) |
| Workstream review (G17A), overlay (G18), multi-participant (G19), gateway (G20), expansion (G21) | baseline groups | — (reused) |
| Session/replay (G22) | `test_vnext_g22_session.py` | browser REPLAY determinism |
| Workspace registry selection (G23) | `test_vnext_g23_registry.py` | browser selector source |
| Multi-workspace shell UI (G24/G24-C01) | `test_vnext_g24_workspace_ui.py` | browser end-to-end + UX |
| Integrated MVP acceptance (G25) | `test_vnext_g25_acceptance.py` | — (reused) |
| MES/observation bridges, ASSY demo, auto-equivalence | baseline groups (`assy_oracle`) | ASSY oracle re-run green |
| **Browser functional validation (A)** | — | **NEW (G26)** |
| **Compact UAT (B)** | — | **NEW (G26)** |
| **UX sanity (C)** | — | **NEW (G26)** |
| **Demo stability smoke (D)** | — | **NEW (G26)** |

## Test plan for the new layers

- A. Browser functional: manual/Playwright-driven session against a live
  `python -m virtual_factory.main serve --port 8099`, exercising `/workspaces`.
- B. Compact UAT: 8 scenarios in
  `evidence/VF-vNEXT-G26/03-uat-checklist-results.md`.
- C. UX sanity: issue list in
  `evidence/VF-vNEXT-G26/04-ux-issue-list.md`.
- D. Demo stability: `evidence/VF-vNEXT-G26/stability_smoke.py` ->
  `stability-results.json` (cold start, repeated switching, 270 steps,
  reset/replay/new_attempt, bad requests, responsiveness).

## Out of scope (unchanged)

No SH-WTP whole-plan/T110/Line2; no gateway/OPC/MQTT/Kafka/REST production; no
`/assy-demo` unification; no G4/G19/coupling redesign; no PIM/MES change; no
authority broadening; no broad visual redesign; no duplicate test proliferation.
