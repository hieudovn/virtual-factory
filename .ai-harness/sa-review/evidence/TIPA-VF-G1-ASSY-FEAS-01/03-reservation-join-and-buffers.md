# 03 — Reservation, AP04 consumption, buffers and failure modes

## Reservation ledger

There is **no reservation ledger** in ASSY. `AssyLineConfig` declares
`ap04_required_parent_sources = ("SSO2", "RSO2")`
(`src/virtual_factory/assembly/line_runtime.py:161`), and the YAML loader copies
it (`line_runtime.py:272`), but `_execute_ap04_join` never reads that field.

AP04 consumes a Rotor by popping the first insertion-order key:

```python
if not self._rso2_wips:
    raise AssyLineError("AP04 JOIN: no RSO2 WIP available")
rso2_key = next(iter(self._rso2_wips))
rso2_wip = self._rso2_wips.pop(rso2_key)
```

(`line_runtime.py:1712-1719`)

There is no eligibility check, no quantity check, no reservation owner, no
version check, no expiry and no atomic all-or-nothing multi-parent
reservation. The SSO2 parent is whatever WIP happens to be at AP04; it is not
debit-committed from an upstream inventory.

## Parent identity and child creation

`_execute_ap04_join(parent_a_wip_id)` uses the supplied SSO2 ID verbatim and
the popped RSO2 ID as the two genealogy parents
(`line_runtime.py:1718-1740`). Therefore an external ID would be preserved **if
it could be registered**. Today it cannot be registered: see `02` and the probe
`Unknown WIP: EXT-SSO2-0001`.

The join mutates genealogy, child WIP and parent lifecycle in ordinary Python
memory. There is no transaction, no rollback, and no outbox. If an exception
occurs after `pop()` but before the child/genealogy is fully written, the Rotor
is lost.

## Buffer limits

- SSO2 input queue: `AssyDemoContext.sso2_ids` is an unbounded Python list
  (`demo_composition.py:127`).
- RSO2 buffer: `AssyLineRuntime._rso2_wips` is an unbounded dict
  (`line_runtime.py:500`); the public size property is `len()` only
  (`line_runtime.py:552-554`).
- There is no capacity, FIFO policy, allowed material type or qualified-status
  check.

## Failure modes observed in the current runtime

| Scenario | Current behaviour | Evidence |
|---|---|---|
| No RSO2 at AP04 | Raises `AssyLineError("AP04 JOIN: no RSO2 WIP available")`; no `WAITING_FOR_MATERIAL` event; step call aborts | Probe 06; `line_runtime.py:1712-1716` |
| No SSO2 at PRE-ASSY | No WIP enters; AP04 is never reached; there is no explicit upstream wait state | `introduce_to_assy` only called with registered WIP; `demo_composition.py:139-149` |
| Two sub-lines need one Rotor | Impossible to express: each context owns an independent `_rso2_wips` dict (six distinct objects in probe 06); both can join against their own local Rotor | Probe 06 |
| Late external Rotor | No injection API; `produce_rso2_wip()` takes no ID/time/argument | `line_runtime.py:617`; probe 06 |
| Buffer overflow | No limit, so no overflow detection | `line_runtime.py:500,552` |
| Replay after failed join | No ledger/transaction; partially popped Rotor is not restored | `line_runtime.py:1712-1740` |

## Consequence for G3-A

The smallest correct integrated join is **not** the current method signature. It
needs a bounded additive seam that:

1. registers an externally supplied SSO2/RSO2 with its original ID and
   provenance;
2. reserves both parents before AP04 starts;
3. commits consumption + child + genealogy atomically or returns a
   deterministic `WAITING_FOR_MATERIAL`;
4. leaves the legacy method and its defaults unchanged.

That is `NEEDS_LOCAL_EXTENSION`; it is not safe to claim the existing AP04 join
already supports integrated material flow.
