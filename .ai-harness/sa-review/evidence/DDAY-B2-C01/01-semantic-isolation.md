# DDAY-B2-C01 — 01. Semantic isolation (C01-A)

**Defect (SA-verified):** generic `introduce_unit()` assigned the legacy
`WipLifecycle.IN_ASSY` value, and `line_facts()` publishes `ws.lifecycle.value`
as `manufacturing_status` — so a Bottled Water unit could expose `in_assy`
outward.

**Machine evidence:** [`machine-evidence.json`](./machine-evidence.json) →
`semantic_isolation`; raw transcripts
[`prefix-reproduction.txt`](./prefix-reproduction.txt),
[`postfix-proof.txt`](./postfix-proof.txt); probe
[`reproduction_probe.py`](./reproduction_probe.py).

## 1. Pre-fix reproduction (run before any correction)

Reachable through public API only — `produce_unit()` + `introduce_unit()`:

```
=== A. entry state via public API (produce_unit + introduce_unit) ===
position: BW-FP-BLW01
unit_id: BTL-000001
manufacturing_status: 'in_assy'
lifecycle enum value: in_assy
leaks 'assy' (case-insensitive): True

=== C. full case-insensitive scan of the outward surfaces ===
entry-facts hits: ["in_assy"]
```

A second, independent window exists: any unit whose current station has not yet
completed (for example a station that overruns its dwell, or a non-auto
completion mode) stays at the entry lifecycle while it is occupied and visible.

## 2. The correction

`WipLifecycle` gains an additional member; the legacy value is neither removed
nor renamed:

```python
class WipLifecycle(str, enum.Enum):
    CREATED = "created"
    IN_ASSY = "in_assy"      # legacy profile only - unchanged
    IN_LINE = "in_line"      # C01: domain-neutral generic entry state
    ...
```

`introduce_unit()` — the generic route — now assigns `IN_LINE`, while
`introduce_to_assy()` (legacy) still assigns `IN_ASSY`. That is the whole
semantic change: two lines in `line_runtime.py`.

## 3. Post-fix proof — every state of the generic route

| Route stage | Published status | Legacy token? |
|---|---|---|
| entry (`produce_unit` + `introduce_unit`) | `in_line` | no |
| in progress (station not yet complete, MANUAL mode) | `in_line` | no |
| station completion | `completed_station` | no |
| route completion (exited at the Palletizer) | `released` | no |
| rejected at Inspection | `rejected` | no |

Case-insensitive leak sweep over every generic outward surface (raw facts, trace
events, station contracts, unit identities, every station status):

| State | Strings scanned | Findings |
|---|---|---|
| entry | 139 | **0** |
| in progress | 143 | **0** |
| station completion | 290 | **0** |
| reject | 372 | **0** |

Patterns: `assy`, `tipa`, `sso2`, `rso2`, `ap05_jam`, `\bap\d{2}\b`, all
case-insensitive — so `in_assy`, `PRE-ASSY` and `ASSY-SLxx` are all caught, not
just uppercase literals.

## 4. Legacy behaviour preserved

| Check | Value |
|---|---|
| Legacy config profile | `is_generic = false` |
| Legacy `introduce_to_assy()` lifecycle | `in_assy` — unchanged |
| `WipLifecycle.IN_ASSY.value` | `in_assy` — unchanged |
| `WipLifecycle.IN_LINE` is a distinct member | true (not a rename) |
| Legacy regression (575 tests) | PASS, unmodified |
| Full suite (1666 tests) | PASS |

## 5. T12 coverage strengthened

The B2 leakage test previously matched exact uppercase literals. It now matches
case-insensitively, so semantic variants such as `in_assy` fail the test — which
is exactly what the pre-fix state would have produced. Two further tests were
added: neutral status at every generic stage, and legacy lifecycle unchanged.

Asserted by `test_t12_no_legacy_domain_leakage_in_outward_surfaces`,
`test_c01_a_generic_outward_lifecycle_is_domain_neutral`,
`test_c01_a_legacy_lifecycle_semantics_are_unchanged`, and by the
`SMOKE-BW-ISO` smoke check.
