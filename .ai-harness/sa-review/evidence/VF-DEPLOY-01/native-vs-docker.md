# VF-DEPLOY-01 — native-vs-docker.md

## Method (§9)

The same accepted source (HEAD `18d253d`) was run two ways:

| Runtime | Launch | Port |
|---|---|---|
| Native | `python src\virtual_factory\main.py serve --port 8001` (env `VF_ENABLE_S04B_OVERVIEW=1`, `TIPA_ASSY_CONFIG=configs/plants/tipa_assy_demo.yaml`) | 8001 |
| Docker | `docker compose -f docker-compose.assy.yml up -d` (`virtual-factory serve --host 0.0.0.0 --port 8000`) | 8000 |

Both were restarted fresh (in-memory bridge at generation R1) and driven
identically by `equivalence_check.py` for the three scenarios:
`HAPPY_PATH` (E1), `AP06_FAIL_RETEST_PASS` (E2), `AP08_NG_REINSPECT_PASS` (E3).
The P0 observation trace was fingerprinted and diffed.

## Result — EQUIVALENT (all PASS)

`diff_fingerprints.py docker-fingerprint.json native-fingerprint.json`:

```
== AP06_FAIL_RETEST_PASS ==
  [PASS] message_type_counts
  [PASS] observation_count
  [PASS] quality_keys_distinct
  [PASS] quality_records_distinct
  [PASS] release_keys
  [PASS] release_times
  [PASS] run_ids
  [PASS] scenario
  [PASS] station_ids
  [PASS] steps_driven
  [PASS] message_keys (count=2335)
== AP08_NG_REINSPECT_PASS ==
  [PASS] message_type_counts
  [PASS] observation_count
  [PASS] quality_keys_distinct
  [PASS] quality_records_distinct
  [PASS] release_keys
  [PASS] release_times
  [PASS] run_ids
  [PASS] scenario
  [PASS] station_ids
  [PASS] steps_driven
  [PASS] message_keys (count=3494)
== HAPPY_PATH ==
  [PASS] message_type_counts
  [PASS] observation_count
  [PASS] quality_keys_distinct
  [PASS] quality_records_distinct
  [PASS] release_keys
  [PASS] release_times
  [PASS] run_ids
  [PASS] scenario
  [PASS] station_ids
  [PASS] steps_driven
  [PASS] message_keys (count=1254)

RESULT: EQUIVALENT (all PASS)
```

AP04 genealogy cardinality also matches (checked separately):

```text
AP06_FAIL_RETEST_PASS  ap04_children equal= True  parents equal= True
AP08_NG_REINSPECT_PASS ap04_children equal= True  parents equal= True
HAPPY_PATH             ap04_children equal= True  parents equal= True
```

## Scenario fingerprints (both runtimes identical)

| Scenario | steps_driven | execution | genealogy | quality | release | cumulative observations |
|---|---|---|---|---|---|---|
| HAPPY_PATH (E1) | 13 | 834 | 108 | 246 | 66 | 1254 |
| AP06_FAIL_RETEST_PASS (E2) | 8 | 1564 | 203 | 454 | 114 | 2335 |
| AP08_NG_REINSPECT_PASS (E3) | 10 | 2342 | 304 | 680 | 168 | 3494 |

## Interpretation

The **full ordered `message_keys` lists are byte-identical** between native and
Docker for all three scenarios — i.e., every single P0 fact (message type, key,
run_id, station, per-attempt quality identity, release) is emitted by Docker
exactly as by native. Containerization does not alter the accepted producer
contract.
