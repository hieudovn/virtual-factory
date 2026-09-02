# SA REVIEW INBOX

Task: SHW-PIM-VF-ALIGN-01-C01
Status: READY FOR SA REVIEW (ALIGN-01 C01 corrections applied: semantic
overreach removed, fail-closed mapping ambiguity closed)

Gate type:
Cross-project semantic-boundary alignment / documentation-contract only
(ALIGN-01 correction gate C01)

Authoritative VF baseline:
main @ 3b006c5f58879eb3a9cd72aee21135b7fbbfcb24 (post PR #29 merge)
ALIGN-01 review head @ b9062356b4dd30451e27c5d073075497b9e1745d

Frozen (contract-level only):
- PIM owns canonical object/signal ids + evidence maturity + state-dimension
  vocabularies; VF consumes read-only.
- VF owns runtime identity/provenance (workspace_id, run/scenario/step/time,
  runtime_signal_id, simulation state instances, fidelity, synthetic/simulated
  provenance) and never overwrites PIM semantic/evidence truth.
- Mapping: runtime_signal_id → canonical_signal_id via explicit mapping; local
  keys never renamed to canonical ids.
- semantic_binding.mode: required → fail closed. For kind: required, ONLY
  status: mapped with exactly one valid PIM-owned canonical target is
  acceptable; unmapped / review_required / missing target / ambiguous-multiple
  target MUST fail closed. Optional simulation-only mappings may stay
  local/unmapped only when explicitly non-published and non-canonical.
- Compatibility = PIM/VF integration-review record (artifact/version/SHA ↔ VF
  consumer contract/version + status + gate).
- Orthogonal state dimensions: PIM owns dimensions+vocab; VF owns instances.
- Open gaps marked missing/unknown/review_required; no fabricated semantics.
- C01: observability/state/evidence value lists are NON-NORMATIVE examples
  (no PIM ontology/vocabulary invented); SourceMapped ≠ SiteVerified ≠ site
  truth; canonical ids are PIM-owned stable identity within the applicable
  semantic contract/namespace (no identifier scheme chosen); no VF-side
  document supersedes/replaces a PIM/upstream artifact.

Production code changed: NO
PIM export / workspace loader / binding validation / provenance threading: NO
PH01 started: NO
CORE provenance gate started: NO

Report:
.ai-harness/sa-review/reports/SHW-PIM-VF-ALIGN-01.md

Evidence:
.ai-harness/sa-review/evidence/SHW-PIM-VF-ALIGN-01/ (6 files: 01…06)



