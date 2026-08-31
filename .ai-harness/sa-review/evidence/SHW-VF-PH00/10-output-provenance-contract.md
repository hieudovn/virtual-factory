# 10 — Output Provenance Contract

Minimum machine-readable output envelope (frozen). Extends the existing
`SignalValue` / telemetry frame fields rather than replacing them.

## 10.1 Envelope fields (per emitted signal/frame)

```text
workspace_id        # e.g. SHW-WTP  (NEW — threaded from workspace manifest)
run_id              # per-run identity (existing: plant run generation)
scenario_id         # active scenario id (existing --scenario)
step                # integer step (existing)
simulation_time_s   # existing

canonical_signal_id # e.g. SHW.T102.LEVEL  (NOT a SourceMapped plant tag)
value               # existing
unit                # existing

origin_kind         # "simulation" (fixed)
fidelity            # logical_only | synthetic_reference | first_order (NEW)
data_status         # synthetic | measured | ground_truth (extends existing category/quality)

semantic_contract_version   # upstream semantic contract version (NEW)
semantic_contract_sha       # upstream semantic contract content hash (NEW)
evidence_note               # free-text provenance note (NEW)
```

## 10.2 Frozen rules

1. **`canonical_signal_id` ≠ `SourceMapped` plant tag.** The canonical id is a
   VF-internal, namespace-scoped identifier (`<workspace_id>.<asset>.<signal>`).
   Any mapping to a real plant tag (SourceMapped/SiteVerified) is a separate,
   read-only mapping artifact (see §12), never the canonical id itself.
2. **Simulation output ≠ real plant data.** `origin_kind` is always
   `simulation`; `data_status` always carries `synthetic`/`ground_truth`
   (never silently `measured`). Real plant data would be a different pipeline
   (ingest), out of scope for the simulation workspace.
3. **Provenance is additive** — the existing `SignalValue` fields
   (`name, value, unit, category, quality, timestamp_s, source`) are preserved;
   workspace fields are added in the frame/envelope layer.
4. **`semantic_contract_version` + `semantic_contract_sha`** pin the upstream
   semantic contract the run consumed (see §12). A run without a pinned contract
   must emit `semantic_contract_version="unpinned"` and an empty sha.

## 10.3 Where each field lives (current → future)

| Field | Today | Future (PH01+) |
|---|---|---|
| `workspace_id`, `fidelity`, `semantic_contract_*`, `evidence_note`, `origin_kind` | absent | add to `telemetry/telemetry_frame.py` frame dict + `observation/` envelope payload |
| `canonical_signal_id` | `SignalValue.name` (un-namespaced) | namespace-prefix at frame build (`SHW.` prefix) |
| `data_status` | `category`/`quality` | extend `OutputPolicy` categories |
| `scenario_id` | not stamped in frame | add to frame |

## 10.4 Non-goals

- No MES/PlantOS schema changes (that is a different contract).
- No change to `SignalValue` dataclass shape in PH00 — only the frame/envelope
  layer proposal is frozen.
