# 11 — SH WTP Placement Options

Compare the four candidate locations. No restructure in PH00 — recommendation
only.

## 11.1 Options

| Criterion | A: `workspaces/shw-wtp/` | B: `configs/workspaces/shw-wtp/` | C: `configs/plants` + `configs/scenarios` + metadata | D: `examples/song-hong-wtp/` |
|---|---|---|---|---|
| Fit with current repo | LOW (new top-level concept; no `workspaces/` root exists) | MEDIUM-HIGH (colocated under existing `configs/` root) | HIGH (reuses exact current mechanism) | LOW (examples/ is for demo fixtures) |
| Migration cost | HIGH (new packaging/path-resolution convention) | LOW-MEDIUM (additive dir under `configs/`) | LOWEST (zero new convention) | MEDIUM (moves WTP from `simulators/` into `examples/`) |
| Risk to existing workspaces | MEDIUM (new top-level may confuse tooling) | LOW | LOWEST | LOW |
| Discoverability | HIGH (first-class `workspaces/`) | HIGH (all config in one tree) | MEDIUM (flat files, no grouping) | LOW |
| Test isolation | HIGH | HIGH (per-workspace subtree) | MEDIUM (convention only) | LOW |
| Scalability | HIGH | HIGH | MEDIUM | LOW |

## 11.2 Recommendation

**`configs/workspaces/shw-wtp/`** as the workspace container, with this layout
(proposal only):

```text
configs/workspaces/
  shw-wtp/
    workspace.yaml                 # frozen manifest (§06)
    plant.yaml                     # loadable PlantConfig (plant.id=PLANT-SHW)
    scenarios/
      normal_operation.yaml
      ...
    semantic_sources/
      pim_contract.ref.yaml        # artifact+version+commit_sha+compatibility (§12)
      state_templates.ref.yaml
```

Rationale:
1. **Reuses the existing `--config`/`--scenario` mechanism** — `virtual-factory
   run --config configs/workspaces/shw-wtp/plant.yaml --scenario
   configs/workspaces/shw-wtp/scenarios/normal_operation.yaml` works with zero
   new top-level and zero packaging change.
2. **Groups plant + scenarios + manifest + semantic pins in one discoverable
   subtree**, giving the workspace concept a concrete home without inventing a
   new root.
3. **Lowest migration risk** — `configs/` already holds plants/scenarios/models;
   a `workspaces/` subdir is a pure additive extension.
4. **Scalable** — future `configs/workspaces/compressor-benchmark/`,
   `configs/workspaces/tipa-assy/` can mirror it (ASSY migration is deferred
   and optional).

## 11.3 Rejected alternatives (with reason)

- **A `workspaces/shw-wtp/`** — deferred: a first-class top-level is the
  long-term target governance, but promoting it now would require a
  CORE/DOMAIN-MODEL gate (path resolution, packaging, docs). Recommend
  revisiting only after ≥2 workspaces prove the `configs/workspaces/` pattern.
- **C flat files** — insufficient: it cannot hold the manifest + semantic pins +
  workspace-scoped scenarios as a unit, so it fails the isolation requirement.
- **D `examples/song-hong-wtp/`** — rejected: `examples/` is for fixtures; a
  production workspace must not live next to demo snippets, and the §9 draft
  path does not even exist in the repo.

## 11.4 Constraint

No `simulators/wtp` or `simulators/vf2` content is moved, imported, or
re-implemented in PH00. Their future relationship to `configs/workspaces/` is
an SA decision (see §14 risks).
