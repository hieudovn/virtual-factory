# SA REVIEW INBOX

Task: SHW-PIM-VF-ALIGN-01
Status: READY FOR SA REVIEW (PIM↔VF semantic handoff contract frozen)

Gate type:
Cross-project semantic-boundary alignment / documentation-contract only

Authoritative VF baseline:
main @ 3b006c5f58879eb3a9cd72aee21135b7fbbfcb24 (post PR #29 merge)

Frozen (contract-level only):
- PIM owns canonical object/signal ids + evidence maturity + state-dimension
  vocabularies; VF consumes read-only.
- VF owns runtime identity/provenance (workspace_id, run/scenario/step/time,
  runtime_signal_id, simulation state instances, fidelity, synthetic/simulated
  provenance) and never overwrites PIM semantic/evidence truth.
- Mapping: runtime_signal_id → canonical_signal_id via explicit mapping; local
  keys never renamed to canonical ids.
- semantic_binding.mode: required → fail closed on missing/mismatched/
  review-required semantic source.
- Compatibility = PIM/VF integration-review record (artifact/version/SHA ↔ VF
  consumer contract/version + status + gate).
- Orthogonal state dimensions: PIM owns dimensions+vocab; VF owns instances.
- Open gaps marked missing/unknown/review_required; no fabricated semantics.

Production code changed: NO
PIM export / workspace loader / binding validation / provenance threading: NO
PH01 started: NO
CORE provenance gate started: NO

Report:
.ai-harness/sa-review/reports/SHW-PIM-VF-ALIGN-01.md

Evidence:
.ai-harness/sa-review/evidence/SHW-PIM-VF-ALIGN-01/ (6 files: 01…06)


