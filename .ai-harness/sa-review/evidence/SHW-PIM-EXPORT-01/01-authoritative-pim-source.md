# 01 — Authoritative PIM Source (proven)

SHW-PIM-EXPORT-01 Priority 1: resolve and prove the authoritative PIM
source-of-truth for the Song Hong Water Treatment Plant (SH WTP).

## 1.1 Resolution result: PROVEN

The authoritative PIM source resolves to a **separate public repository** owned
by the same GitHub org as the VF repo:

```text
Repository:  https://github.com/hieudovn/plant-intelligence-model
Branch/ref:  main
HEAD:        d241da61a6166df8359f892141609add75aec5b5
Commit date: 2026-08-29 10:02:55 +0700
Subject:     "dev: point vite proxy to backend port 8010 (avoid :8000 conflict)"
```

Remote verification (machine-derived):

```text
$ git ls-remote https://github.com/hieudovn/plant-intelligence-model.git
d241da61a6166df8359f892141609add75aec5b5        HEAD
d241da61a6166df8359f892141609add75aec5b5        refs/heads/main
```

## 1.2 Authority context (PIM-side, not a VF copy/stub)

- PIM `README.md` describes the product as "an Asset & Process Knowledge Graph
  platform" and "semantic backbone / dynamic knowledge network"; it lists
  **Virtual Factory** as a downstream consumer ("simulation and digital twin
  runtime") — i.e. PIM is the upstream semantic authority, VF is a consumer.
- PIM `PROJECT_CONSTITUTION.md` defines the product boundary: PIM is a
  "semantic plant model engine"; "Visualization is a projection of the model,
  not the source of truth."
- The SH WTP package header (`examples/song-hong-wtp/README.md`) carries the
  mandatory statement: "**PIM defines. VF simulates.** PlantOS observes, stores,
  monitors, and analyzes operations."

These establish PIM-side semantic authority distinct from any VF-side stub.

## 1.3 Uniqueness of the source (no competing PIM source)

- The VF repository references exactly one PIM repo by name
  (`plant-intelligence-model`) in `docs/prompts/vf2-st01-coder-prompt.md` and
  `docs/vf2-st00-schema-alignment.md`.
- No other PIM repository/system is referenced anywhere in the VF repo.
- `PlantOS` is referenced only as a downstream integration consumer (not a PIM
  source). `simulators/wtp` (VF-1) and `simulators/vf2` (VF-2) are VF-side
  legacy runtimes, not PIM sources.
- Conclusion: exactly one candidate PIM source exists → no competing-source
  STOP condition.

## 1.4 SH WTP content present in the PIM repo

The PIM repo contains a dedicated SH WTP semantic model package:

```text
examples/song-hong-wtp/
  plant_config/   (canonical_id_rules.md, contract_principles.md,
                   evidence_policy.yaml, model_scope.md, system_boundary.md,
                   responsibility_matrix.md, first_simulation_slice.md,
                   gap_register.yaml)
  model_fixture/  (model.yaml, gap_register.yaml)
  contracts/      (vf_readiness_contract_draft.yaml,
                   plantos_monitoring_contract_draft.yaml,
                   contract_gap_register.md)
  vf_readiness/   (vf_object_class_mapping.yaml,
                   vf_readiness_profile_schema_draft.yaml, policies)
  seed/           (plant_skeleton.yaml, signal_catalog_ph02.yaml,
                   first_vf_readiness_slice_t106_t108_t110.yaml,
                   plant_wide_skeleton_ph03.yaml)
  planning/       (SHW-PIM-PH01/PH02 plans, SHW-VF-PH01-logical-simulation-plan)
  reports/        (SHW-G00, SHW-PIM-PH01/PH02/PH03, SHW-CONTRACT-PH01,
                   SHW-TERM-AUDIT-01, SHW-UI-PH01..04, SHW-VFREADINESS-PH01,
                   SHW-KG-PH01, SHW-W01/W02, SHW-NEXT-READINESS-01, ...)
```

The exact artifact inventory + hashes are pinned in `02-export-artifact-inventory.md`
and `03-version-hash-pinning.md`.

## 1.5 Source-resolution preflight (Issue #33 minimum proof) — all satisfied

| Required proof element | Evidence |
|---|---|
| authoritative repository/system/source location | `hieudovn/plant-intelligence-model` (GitHub, public) |
| exact branch/ref/version | `main` @ `d241da61…` |
| owner/authority context (PIM-side, not VF copy/stub) | PIM README + PROJECT_CONSTITUTION + "PIM defines. VF simulates." |
| exact artifact(s) intended for export | `examples/song-hong-wtp/` (inventory in evidence 02) |
| exact version/hash/SHA mechanism | git SHA + per-file SHA-256 content hash (evidence 03) |
