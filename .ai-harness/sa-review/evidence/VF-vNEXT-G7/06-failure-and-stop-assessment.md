# VF-vNEXT-G7 · Evidence 06 — Failure semantics + STOP assessment (Issue #52 F + STOP FOR SA)

## Failure semantics (G4 honesty preserved)
- A step that fails a G4 window transitions the run to `failed`; `last_result`
  and `failure` distinguish failed orchestration from successful completion.
- No rollback is claimed for participants that already advanced (the bridge only
  reports the G4 `WindowOutcome`; it never fabricates a transaction/rollback).
- Terminal runs (stopped/failed) never accept another step under the same
  historical `run_id`; restart/replay always create a fresh `run_id`.
- No hidden retry: each mutation is one explicit call.

## STOP-condition assessment
| STOP condition | Status |
|---|---|
| Generic hierarchical step requires a new synchronization/timestep policy | NOT triggered — ASSY steps reuse G4 natural boundaries only |
| ASSY must be fractionalized / dwell/index semantics changed | NOT triggered — arbitrary boundaries fail closed |
| Continuous runtime needs invented hierarchy or rewritten engine | NOT triggered — continuous not bridged; existing behavior green |
| Reset semantics cannot stay capability-scoped | NOT triggered — reset delegated via `supports_reset`; terminal runs excluded |
| Replay requires unavailable inputs to fabricate | NOT triggered — replay pins prior accepted inputs; missing scenario authority → explicit unavailable |
| Lifecycle design allows terminal run identity reuse | NOT triggered — restart/replay produce fresh `run_id` |
| A container-only scope must be made executable | NOT triggered — container resolves to descendants, never a participant |
| G2 RunContextV2 identity/provenance contract broken | NOT triggered — `RunContextV2` reused as immutable identity |
| G4 failure semantics need false rollback/transaction claims | NOT triggered |
| Requires G8 regression-baseline, G9 semantic binding, or G10 SH-WTP | NOT triggered |

No STOP condition triggered; no new lifecycle/synchronization policy invented.
