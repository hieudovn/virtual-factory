# 15 — Baseline Reconciliation (SHW-VF-PH00-C01, Correction A)

**Result: MATERIAL ARCHITECTURE DIVERGENCE FOUND → STOP FOR SA.**

## 1. Identity of the three heads

| Concept | SHA | Where it lives |
|---|---|---|
| PH00 audit HEAD | `240d8db5eff481f1d4d8810d275214077031e72a` | tip of `origin/docs/m6-s01-tipa-baseline` (post MES-03 merge) |
| PH00 correction commit | `6ace752b1ec7351dae30bc087503cd1ff8dad463` | `feature/shw-vf-ph00` (PH00 deliverables only) |
| current `main` HEAD (observed at SA review + re-verified now) | `fda1db44b17a7f61da2393e00cdf20bb7998b7ea` | `origin/main` |

## 2. Merge base & lineage

- **merge-base(`240d8db`, `fda1db44`) = `17a1d9ecafb170fa94e8d01a1f12d84e79982773`**
  (`Merge branch 'docs/tipa-demo-timeline-2026-08'`, on `chore/ai-pm-execution-harness`).
- `git merge-base --is-ancestor 240d8db fda1db44` → exit **1** (audit HEAD is NOT an ancestor of main).
- `git merge-base --is-ancestor fda1db44 240d8db` → exit **1** (main is NOT an ancestor of audit HEAD).

**Lineage relationship: the two heads have DIVERGED from a common ancestor `17a1d9ec`; neither contains the other.**

### What is on `main` but not on the audit baseline
- `fda1db44` — `VF-DM-DEMO-ASSY-MES-01: deterministic ASSY customer demo for MES (#22)`
  (merges PR #22; carries the single-sub-line `src/virtual_factory/assembly/demo_assy_mes/` runner).

### What is on the audit baseline but not on `main` (TIPA ASSY six-sub-line lineage)
- The full TIPA ASSY six-sub-line stack merged via PRs #23/#24 and prior TIPA gates:
  `c3c8bb6` (MES-02 #23), `240d8db` (MES-03 #24), plus `248e70d` (TIPA-DEMO-LIVE-01),
  `6e68ec9` (VF-DEPLOY-01), `08cc410`/`5b2a766` (VF-CONTRACT-FINALITY-01),
  `18d253d` (MES-INT-02A-VF), etc.

## 3. Why `240d8db` was used as the PH00 audit HEAD

At PH00 execution the working checkout was detached at `240d8db` — the tip of
`docs/m6-s01-tipa-baseline`, which is the SA-authorized integration branch for
the TIPA ASSY + MES contract lineage (MES-02 → PR #23, MES-03 → PR #24 both
merged into this branch). PH00 inventoried that state because it contains the
six-sub-line TIPA ASSY runtime, `tipa_assy_demo.yaml`, the `/assy-demo` API and
the MES contract v1.1 bridge — the fullest expression of the platform's
simulation families.

## 4. Delta `240d8db` ↔ `fda1db44` (architecture-relevant paths only)

Command: `git diff --name-status 240d8db5eff481f1d4d8810d275214077031e72a fda1db44b17a7f61da2393e00cdf20bb7998b7ea -- src/ configs/ simulators/ examples/ deploy/ pyproject.toml Dockerfile docker-compose*.yml`

Material changes (from `main`'s perspective):

| Path | Status on `main` | Meaning |
|---|---|---|
| `src/virtual_factory/assembly/demo_assy_mes/` (10 modules) | present | MES-01 single-sub-line runner |
| `src/virtual_factory/assembly/{line_runtime,demo_controller,demo_composition,demo_snapshot,assy_mes_bridge,observation_bridge,quality_records,operation_execution,station_contracts,genealogy,sub_line_identity,upstream,carrier,conveyor,auto_timing}.py` | **absent** | six-sub-line stack is NOT on `main` |
| `configs/plants/tipa_assy_demo.yaml` | **absent** | six-sub-line plant config NOT on `main` |
| `docker-compose.assy.yml` | **absent** | ASSY Docker compose NOT on `main` |
| `src/virtual_factory/ui/api.py` | modified (−250/+41) | MES-01 API; no six-sub-line `/assy-demo` surface |
| `src/virtual_factory/ui/static/assy_demo.*` → `demo_assy_mes.html` | replaced | different ASSY UI |
| `src/virtual_factory/observation/projections/mes.py` | modified | drops MES-02/03 mappings (`CHECKLIST_CONFIRMED`, `measurement_result`, `release`) — MES-01 projection only |
| `Dockerfile` | modified | drops `SOURCE_SHA`/`VF_SOURCE_SHA` bake (MES-02 addition absent) |
| `pyproject.toml` | modified | drops `jsonschema>=4.0` dev dep |

**Unchanged between the two heads:** `configs/` (other than `tipa_assy_demo.yaml`),
`simulators/` (wtp + vf2), `examples/`, `deploy/`, the continuous/compressor
engine + `ModelRegistry` + `equipment/` domain models, `core/`, `discrete/`.

## 5. Impact on each PH00 architecture finding

| PH00 finding | Delta verdict | Explanation |
|---|---|---|
| Runtime families | **CHANGED — material** | `main` has 3 families: continuous engine, `demo_assy_mes` (single-sub-line ASSY), discrete kernel. The six-sub-line TIPA ASSY family audited in PH00 (line_runtime/demo_controller/assy_mes_bridge) does NOT exist on `main`. |
| Runtime entrypoints | **CHANGED — material** | `main`'s ASSY entrypoint is `demo_assy_mes` (MES-01 runner); the `/assy-demo` API + `DemoController` + `docker-compose.assy.yml` entrypoint is not on `main`. |
| Engine dispatch | UNCHANGED | `core/engine_factory.resolve_engine_kind` identical (only `continuous_process`); `plant.type` still ignored. |
| Workspace absence/presence | UNCHANGED | no workspace concept on either head. |
| ASSY architecture | **CHANGED — material** | PH00 audited the six-sub-line stack (hard-coded `assembly/tipa.py` topology, `/assy-demo`, MES v1.1). `main` has the older MES-01 `demo_assy_mes/` package with a different topology/model. |
| Continuous/compressor reuse | UNCHANGED | `continuous_mvp_01` + `compressor_train_benchmark_01` + generic `ModelRegistry` identical. |
| `simulators/wtp` (VF-1) | UNCHANGED | identical on both heads. |
| `simulators/vf2` (VF-2) | UNCHANGED | identical on both heads. |
| `ModelRegistry` | UNCHANGED | identical (15 model types). |
| Output/provenance architecture | **CHANGED — partial** | MES projection (`mes.py`) differs (MES-01 vs MES-02/03 mappings); the MES-02/03 evidence surface (`mes.checklist_result`, `mes.measurement_result`, `mes.release`) is absent on `main`. Telemetry/CSV/MQTT/OPC-UA base architecture unchanged. |
| SH WTP placement recommendation | UNCHANGED (recommendation stands) | `configs/workspaces/shw-wtp/` is config-level and independent of the ASSY lineage conflict; but it can only be validated against whichever lineage the SA declares authoritative. |

## 6. Verdict

Per gate §3 / §17:

> "If ANY material architecture finding changed: STOP FOR SA. Do NOT silently
> rewrite PH00 around it."
> "STOP FOR SA if: current main materially invalidates a PH00 architectural
> finding; authoritative VF baseline cannot be reconciled."

The delta between the PH00 audit HEAD (`240d8db`) and current `main`
(`fda1db44`) **materially invalidates the PH00 runtime-family / runtime-entrypoint /
ASSY-architecture / output-provenance findings**: the six-sub-line TIPA ASSY
that PH00 audited is not present on `main`; `main` carries the older MES-01
`demo_assy_mes/` single-sub-line implementation instead.

The two lineages share merge-base `17a1d9ec` and have not been reconciled.
PH00 was audited against `docs/m6-s01-tipa-baseline` (the SA-authorized TIPA
ASSY integration branch); `main` is a diverged lineage.

**ACTION: STOP FOR SA.**
- PH00 findings are NOT rewritten around `main`.
- Contract corrections (B–I) are NOT applied — they must not be layered onto an
  un-reconciled baseline.
- SA must decide: which lineage is authoritative for SH WTP preflight
  (re-audit PH00 against `main`, or continue on `docs/m6-s01-tipa-baseline`),
  and how/whether the TIPA ASSY six-sub-line work will be reconciled into `main`.
