# SA REVIEW INBOX

Task: VF-REPO-LINEAGE-01
Status: IN PROGRESS — reconciling accepted ASSY lineage into canonical main

Reconciliation objective:
Merge the accepted six-sub-line ASSY + MES v1.1 lineage
(origin/docs/m6-s01-tipa-baseline) back into canonical main, preserving BOTH:
- main's single-sub-line MES-01 customer demo (assembly/demo_assy_mes/,
  /demo-assy-mes/* endpoints, demo_assy_mes.html) — PRESERVED;
- the six-sub-line TIPA ASSY + MES v1.1 evidence contract
  (assembly/{line_runtime,demo_controller,assy_mes_bridge,...},
  /assy-demo/* endpoints, tipa_assy_demo.yaml, docker-compose.assy.yml) — PRESERVED.

Refs:
- current main: fda1db44b17a7f61da2393e00cdf20bb7998b7ea
- accepted ASSY lineage: 240d8db5eff481f1d4d8810d275214077031e72a
- merge-base: 17a1d9ecafb170fa94e8d01a1f12d84e79982773
- reconciliation branch: feature/vf-repo-lineage-01

Conflict classification (3-way merge):
- .ai-harness/sa-review/CURRENT.md — add/add (governance artifact; combined)
- observation/projections/mes.py — mechanical; baseline is a strict superset
  (MES-01 mappings ⊆ MES-02/03 + M6-INT-01 + MES-03 mappings)
- ui/api.py — mechanical; disjoint endpoint blocks (/demo-assy-mes/* ∪ /assy-demo/*)

Production code changed: YES (reconciliation merge only; both lineages preserved)
No accepted ASSY/MES behavior removed.

Related (not started): SHW-VF-PH00 remains BLOCKED pending this reconciliation.

Report:
.ai-harness/sa-review/reports/VF-REPO-LINEAGE-01.md

Evidence:
.ai-harness/sa-review/evidence/VF-REPO-LINEAGE-01/


