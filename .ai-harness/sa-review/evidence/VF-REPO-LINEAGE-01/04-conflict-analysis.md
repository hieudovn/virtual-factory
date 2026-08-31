# 04 — Conflict Analysis

`git merge-tree --write-tree main docs/m6-s01-tipa-baseline` reported exactly 3
conflicts. Each is analyzed below. **None is a semantic conflict** — all are
mechanical and resolve deterministically by union/superset.

## Conflict 1 — `src/virtual_factory/observation/projections/mes.py` (content)

- **HEAD (main)** added: `LINE_OUT`, `WIP_ENTERED`, `DOWNTIME_START`,
  `DOWNTIME_END` (event→execution_event) and `oee_summary` (semantic→oee_summary),
  with a MES-01 comment.
- **baseline** added the **same four mappings** (with a richer MES-02 comment)
  plus `CHECKLIST_CONFIRMED` (MES-03), `release` (M6-INT-01), and
  `measurement_result` (MES-03).
- **Analysis:** baseline is a strict superset of main's additions. No mapping
  differs semantically; only the comment text differs (MES-01 vs MES-02 wording).
- **Resolution:** take baseline (`git checkout --theirs`). All MES-01 mappings
  remain present.

## Conflict 2 — `src/virtual_factory/ui/api.py` (content)

- **HEAD (main)** appended the MES-01 block: `_demo_controller`,
  `_get_demo_controller()` (imports `assembly.demo_assy_mes.controller`),
  and endpoints `/demo-assy-mes`, `/demo-assy-mes/{reset,start,pause,step,jam,
  recover,snapshot,messages}` + `demo_assy_mes.html` page.
- **baseline** appended the six-sub-line block: `_assy_controller`,
  `_get_assy_controller()` (imports `assembly.demo_controller` +
  `observation_bridge` + `assy_mes_bridge`), and endpoints `/assy-demo`,
  `/assy-demo/{static,reset,step,observations,snapshot,jam,recover,
  run-to-terminal,mes-messages,mes-trace,version,operation-command,
  station-action,run-mode,select,overview,sub-lines,sub-line/{id}}` +
  `assy_demo.html` page.
- **Analysis:** disjoint URL namespaces and disjoint lazy-singleton controllers.
  No shared symbol, no shared route, no import collision.
- **Resolution:** keep BOTH blocks (union). Verified: no residual conflict
  markers; both `_get_demo_controller` and `_get_assy_controller` present;
  `ast.parse` clean.

## Conflict 3 — `.ai-harness/sa-review/CURRENT.md` (add/add)

- **HEAD (main):** MES-01 SA inbox.
- **baseline:** MES-03 SA inbox.
- **Analysis:** governance artifact only; no runtime impact.
- **Resolution:** combined inbox documenting the reconciliation and current
  authoritative state.

## Semantic-conflict assessment (Issue #25 STOP conditions)

| STOP condition | Assessment |
|---|---|
| Non-trivial semantic conflict between lineages | **NO** — disjoint packages, disjoint API prefixes, superset mappings |
| Uncertain accepted behavior provenance | **NO** — PR #22/#23/#24 merge SHAs verified |
| Reconciliation drops an accepted feature | **NO** — both `demo_assy_mes` and six-sub-line preserved |
| Full regression cannot be green without unrelated production changes | **NO** — see §06 (regression) |
| Requires force-push/history rewrite of main | **NO** — normal two-parent merge |
| Ambiguity over which commits were SA-accepted | **NO** — Issue #25 explicitly lists PRs #22/#23/#24 |

**Conclusion: no STOP condition triggered. Reconciliation is safe and proceeds.**
