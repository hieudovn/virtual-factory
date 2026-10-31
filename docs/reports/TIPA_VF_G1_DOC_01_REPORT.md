# TIPA-VF-G1-DOC-01 — SA Source-of-Truth Publication Report

**SA authorization:** Roadmap/G1A direction approved by PO 2026-10-31; [#123](https://github.com/hieudovn/virtual-factory/issues/123); cross-consumer G1B/G1C is DRAFT [#124](https://github.com/hieudovn/virtual-factory/issues/124).  
**Workflow:** SA remote design via proposed governance PR [#131](https://github.com/hieudovn/virtual-factory/pull/131), issue #130.  
**Baseline:** prior `main@04fb9413bd5af3c4f0457047267a60b3ea4e94fe`; stacked branch base `sa/governance/remote-design-v1@6ca569b4362235edd4d05e61feccba7ddadcbb4b`.  
**Execution:** documentation/contract only, no runtime/config/PM harness changes.  
**Canonical proof:** branch, PR, changed files, CI status and merge decisions are documented in [#125](https://github.com/hieudovn/virtual-factory/issues/125) and PR metadata, not invented in this pre-commit report.

## Artifacts
- Approved roadmap `docs/plans/TIPA_VF_DIGITAL_TWIN_ROADMAP_V1.md`.
- G1A detailed architecture `docs/architecture/TIPA_VF_G1A_FACTORY_ORCHESTRATION_DESIGN_V1.md`; approved *direction*, new detail stays SA draft pending schema/fixture Design Lock.
- G1B/C proposal `docs/design/TIPA_VF_G1B_G1C_DESIGN_DRAFT_V1.md`; requires MES/QMS/PlantOS SA approval and desktop visual signoff.
- This report and an explicit SA design-task manifest under `.ai-harness/sa-design/tasks/`.

## Cross-check and risk
- The inherited `discrete/` and six-line ASSY runtime exist in `main`; FactoryRunContext/MaterialLedger/external-input adapter are design targets, not current code.
- #126 read-only ASSY feasibility and #129 cross-consumer compatibility are queued; no test execution from this SA documentation commit.
- #127/#128 code slices remain BLOCKED until G1 Design Lock. W3 F0/F1 scope preserved. Synthetic facts not physical TIPA certification.
- This is a **stacked PR**: must only merge into main after governance PR #131 completes and head/base are reverified/retargeted as needed. Do not auto-merge.
