# VF-vNEXT-G25 — Integrated Multi-Workspace Demo / MVP Acceptance

Gate: `VF-vNEXT-G25` (acceptance / hardening)
Issue: #76
Base: `0ca571e2a490502683cf41ae7c1b22822217d1fa` (G24-C01 head)
Model: Pro
Status: READY FOR SA REVIEW

---

## 1. Purpose

Acceptance / hardening gate for the integrated multi-workspace MVP. It does NOT
open new architecture: it drives the two accepted Workspaces end-to-end through
the Workspace Shell backend (`WorkspaceMonitor` over the G23
`WorkspaceRuntimeRegistry` + G22 `RuntimeSession`), re-proves the platform
invariants, and records deterministic evidence.

## 2. FLOW A — TIPA (accepted)

- Open the shell; the workspace selector is sourced from the backend registry
  (`GET /vnext/workspaces` -> `["TIPA", "shwtp"]`).
- Select TIPA -> the selected **G22 RuntimeSession** drives the view
  (`runtime_kind = "selected_g22_session"`).
- Step xN -> **six live ASSY sub-lines** read from that session's own execution
  bridge (`ASSY-SL01..SL06`: simulation time, conveyor state, WIP/motor counts,
  RSO2 buffer).
- `reset` -> same run identity, fresh state (t = 0, trace cleared);
  `new_attempt` -> fresh run identity; `replay` -> fresh run identity with
  **deterministic** re-execution (trace-equivalent).
- Switch to SH-WTP and back -> the TIPA session is **not mutated**
  (same run_id, step_count, trace).
- `/assy-demo` remains labelled a **separate legacy demo runtime**
  (`shares_session: false`, `shares_identity: false`).

## 3. FLOW B — SH-WTP (accepted)

- Select shwtp -> the accepted G21 5-scope slice is displayed in order:
  `RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108`.
- Step xN -> live time/step/trace plus live flow/tank values (T106 input/output
  flow, T108 volume/level).
- Fidelity/status/assumed topology stay **explicit** per scope; the view sets
  `site_truth: false` and lists the scenario-assumed scopes/links.
- `reset` -> same run identity, fresh state; `new_attempt` -> fresh run
  identity; `replay` -> **deterministic** (trace- and tank-volume-equivalent).
- Switch to TIPA and back -> the SH-WTP session is **not mutated**.

## 4. Re-proven platform invariants

| Invariant | Evidence |
|---|---|
| one platform -> many independent Workspaces | registry enumerates `TIPA`, `shwtp`; separate sessions |
| no shared state / run_id / clock / truth | distinct run_ids; independent step counters and sim clocks |
| no cross-workspace runtime coupling | advancing one workspace never moves the other; registry metadata has no composition/binding |
| RuntimeSession lifecycle reused | identical `advance/reset/new_attempt/replay` semantics for both workspaces |
| `explicit_lagged` / G4 / G19 unchanged | constants + G4 coordinator + G19 synthetic federation still build and run |
| ASSY oracle green | `tests/test_assy_demo.py`, `test_auto_equiv_01.py` green in full suite |
| SH-WTP assumptions never site truth | `site_truth: false`; assumed scopes explicit; PIM remains authoritative |

## 5. MVP CAN do (accepted)

- One platform hosting two independent Workspaces (TIPA ASSY six sub-lines;
  SH-WTP G21 five-scope slice).
- Registry-driven workspace selection surfaced on the FastAPI + static UI shell.
- Read-only monitoring of both workspaces with live per-scope values and trace.
- Workspace-scoped run control (`step/reset/stop/new_attempt/replay`) with
  deterministic replay.
- Explicit separation of assumed/scenario topology from authoritative truth.

## 6. Deferred (NOT in this MVP)

- Gateway routing; production OPC/MQTT/Kafka/REST export; multi-gateway;
  store-and-forward.
- SH-WTP whole-plant / site-faithful fidelity; T110 / Line2.
- Distributed execution; advanced coupling policy beyond `explicit_lagged`.
- Broad UI redesign; PIM/MES changes.
- Unifying the `/assy-demo` legacy demo controller with the shell session
  (would be a large redesign).

## 7. Authority still NOT_AUTHORIZED

- `vf_runtime_authorization = NOT_AUTHORIZED`
- `site_authorized_execution = NOT_AUTHORIZED`
- `whole_plant_runtime = NOT_AUTHORIZED / NOT_IMPLEMENTED`

No authority broadening occurred in this gate.

## 8. Deliverables

1. `tests/test_vnext_g25_acceptance.py` — integrated acceptance tests for both
   flows + platform invariants + re-prove checks (24 tests).
2. `.ai-harness/sa-review/evidence/VF-vNEXT-G25/` — deterministic traces:
   `generate_evidence.py`, `flow-a-tipa.json`, `flow-b-shwtp.json`,
   `invariants.json` (byte-identical across runs).
3. This milestone acceptance report.
4. Small fixes only: none required (no production code changed in this gate).
5. Full canonical regression + full suite green.

## 9. Regression

- G25 acceptance: 24 passed.
- Full suite: PASS (see trace `g25_baseline.json`).
- Complete canonical vNext baseline
  (g1_workspace ... g24_workspace_shell, g25_acceptance, full_suite,
  checks_compile, checks_static_lint_type, checks_changed_files,
  checks_preflight): PASS.

## 10. Evidence

- `.ai-harness/sa-review/evidence/VF-vNEXT-G25/`
