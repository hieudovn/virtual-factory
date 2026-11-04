# TIPA VF G1A SA-C01 — Design correction report

**SA authority:** [#147](https://github.com/hieudovn/virtual-factory/issues/147); source failure [#133](https://github.com/hieudovn/virtual-factory/issues/133), [PR #146](https://github.com/hieudovn/virtual-factory/pull/146) at `11e35fa99dbfd2b3a9d37d2d25ccbc7471cdd263` / CI `41756813688` FAILED (2 fixture tests, 1880 others pass). **Baseline:** VF `main@2d876fd4bb9ce060dd72cc5b2db0dd959b09ef9e`.

## Design decision
Preserve DD-01 decimal-string quantities and unchanged module-manifest/schema. T01/T02 source fixtures each had 5 ports `"capacity": 20` (JSON integer), invalid against schema. Replace each with `"capacity": "20"` (base-10 decimal string); exactly 10 field-value changes. Keep all event/order/parent/quality oracles unchanged. Prevent silent numeric coercion or broad schema acceptance.

## Paths
- `docs/design/tipa-g1/fixtures/T01_TWO_PRODUCERS_JOIN.json`: five port capacities corrected.
- `docs/design/tipa-g1/fixtures/T02_UPSTREAM_STARVATION.json`: five port capacities corrected.
- `.ai-harness/sa-design/tasks/TIPA-VF-G1A-SA-C01.json`: SA design scope manifest.
- `docs/reports/TIPA_VF_G1A_SA_C01_REPORT.md`: correction evidence and handoff.

## Verification boundary
Structural precommit check: both JSON documents parsed; exactly 5 capacity fields matched original numeric 20 per fixture and were converted to string "20"; other parsed fields were retained. Remote exact-head SA Design Gate, full VF CI, post-merge tests **must be checked on the PR**; not claimed at document creation. No simulation runtime changed.

## PM resume handoff
After PO-authorized merge and post-merge verification, return to same #133 branch/PR #146 with a non-force, non-rewriting merge of corrected main into the work branch, SA-approved baseline reconciliation, identical regression tests and exact-head evidence. The original red CI remains a valuable pre-correction regression demonstration. Until then #127/#128 blocked.
