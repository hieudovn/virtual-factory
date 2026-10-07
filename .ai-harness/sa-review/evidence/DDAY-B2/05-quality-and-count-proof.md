# DDAY-B2 — 05. Quality and count proof

**Claims:** automatic quality at Inspection; deterministic PASS continues; FAIL
rejects and is never counted good; `good_count + reject_count <= total_count`.

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) → `quality_and_counts`

## Nominal configuration (`scenario: PASS`) — 8 cycles

Automatic quality results at Inspection (no manual disposition anywhere):

```
BW-FP-INS01 BTL-000001 :: disposition=PASS attempt=1
BW-FP-INS01 BTL-000002 :: disposition=PASS attempt=1
BW-FP-INS01 BTL-000003 :: disposition=PASS attempt=1
BW-FP-INS01 BTL-000004 :: disposition=PASS attempt=1
```

Downstream completion:

```
BW-FP-PAL01 BTL-000001 :: route_complete total=8 good=1 reject=0
```

| Fact | Value |
|---|---|
| `total_count` | 8 |
| `good_count` | 1 |
| `reject_count` | 0 |
| `units_on_line` | 7 |
| `simulation_time_s` | 160.0 (= 8 × 20.0 s dwell) |
| `unit_1 lifecycle` | `released` |

Unit 1 passed Inspection, then continued through Labeler → Case Packer →
Palletizer and was counted good only when it exited the last station.

## Deterministic FAIL configuration — 12 cycles

Derived deterministically by setting the Inspection checkpoint scenario to
`ALWAYS_FAIL`. There is no manual inspection result and no operator disposition:
the decision is produced by the engine's own deterministic quality resolver.

| Fact | Value |
|---|---|
| `total_count` | 12 |
| `good_count` | **0** |
| `reject_count` | **8** |
| `units_on_line` | 4 |
| Downstream completions | **0** |
| `REJECT` events | 8, all at `BW-FP-INS01` |

All eight rejected units show:

```json
{"lifecycle": "rejected", "rejected": true, "counted_good": false}
```

and the accepted carrier check confirms no rejected unit is still on a carrier
(`for position in route: carrier.wip_id not in rejected_units`). The line keeps
running: 4 further units are still progressing and 12 units were produced in 12
cycles, so ejection does not block the takt.

## Count invariant sweep

| Scenario | Cycles | total | good | reject | units on line | `good+reject<=total` | in-progress == on-line |
|---|---|---|---|---|---|---|---|
| PASS | 1 | 1 | 0 | 0 | 1 | PASS | PASS |
| PASS | 8 | 8 | 1 | 0 | 7 | PASS | PASS |
| PASS | 20 | 20 | 13 | 0 | 7 | PASS | PASS |
| ALWAYS_FAIL | 1 | 1 | 0 | 0 | 1 | PASS | PASS |
| ALWAYS_FAIL | 8 | 8 | 0 | 4 | 4 | PASS | PASS |
| ALWAYS_FAIL | 20 | 20 | 0 | 16 | 4 | PASS | PASS |

`all_invariants_hold: true`. The stronger identity
`total − good − reject == units_on_line` also holds in every sample, which shows
the counters are exact rather than approximate.

Asserted by `test_t04_*`, `test_t05_*` and the parametrised `test_t06_count_invariant`.

## Scope note

The FAIL variant used here is a **test/evidence configuration override**, not a
shipped scenario. The shipped workspace configuration stays `scenario: PASS`.
The deterministic degradation story (Capper) is B5 and is **not** implemented.
