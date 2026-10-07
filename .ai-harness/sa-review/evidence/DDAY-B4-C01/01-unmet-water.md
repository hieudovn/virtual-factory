# DDAY-B4-C01 — 01. Unmet water demand

**Defect (SA-verified on PR #101):** `_apply_draw()` took
`drawn = min(pending, tank)` then unconditionally set `_pending_draw_m3 = 0.0`.
If the tank could not satisfy the Filler request, the unmet remainder
disappeared.

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) →
`unmet_water`; smoke [`smoke_unmet_water.py`](./smoke_unmet_water.py).

## 1. Pre-fix code path (B4 head `0f9606b`)

```
807:     def _apply_draw(self) -> None:
808:         if self._pending_draw_m3 <= 0.0:
809:             return
810:         drawn = min(self._pending_draw_m3, self._tank_volume_m3)
811:         self._tank_volume_m3 -= drawn
812:         self._water_draw_total_m3 += drawn
813:         self._pending_draw_m3 = 0.0
```

A 0.01 m³ request against an empty tank therefore ended as
`pending = 0`, `draw = 0`, `request lost`. The nominal 4000-step trajectory
never starved, so B4-11 did not see the edge.

## 2. The correction

Smallest change: keep the unpaid remainder on the pending ledger and publish
it.

```
drawn = min(pending, available)
pending -= drawn
```

New raw facts on `balances.water`:

| Field | Meaning |
|---|---|
| `unmet_water_demand_m3` | still-unpaid Filler request |
| `water_request_total_m3` | `draw + unmet` |

Identity that now holds under starvation and after later refill:

```
request = draw + unmet
```

No starvation/interlock engine. No B2/B3 line-semantic change. Production
still records product water from real `STATION_COMPLETE` events; the ledger
simply no longer throws away the corresponding draw.

## 3. Post-fix proof

Empty tank, request 0.01 m³, then 0.004 m³, then 0.02 m³ inventory:

| Step | unmet | draw | request | tank |
|---|---|---|---|---|
| starve | 0.01 | 0.00 | 0.01 | 0.00 |
| partial | 0.006 | 0.004 | 0.01 | 0.00 |
| paid | 0.00 | 0.01 | 0.01 | 0.014 |

Live smoke: `python .ai-harness/sa-review/evidence/DDAY-B4-C01/smoke_unmet_water.py` → exit 0.

A second test freezes the treatment latch and drives real fill completions
through `step()`: product water appears, draw stays 0, unmet equals
`product / process_efficiency`, and later inventory clears the ledger.
