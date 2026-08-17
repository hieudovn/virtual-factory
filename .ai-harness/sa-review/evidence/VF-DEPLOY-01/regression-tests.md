# VF-DEPLOY-01 — regression-tests.md

No production code was changed in this gate (deployment/config/docs only), so
the regression is expected to be identical to the accepted baseline.

## Full suite (§16)

Command:

```text
python -m pytest tests/ -q -p no:cacheprovider
```

Result:

```text
2 failed, 1554 passed in 12.94s
```

The 2 failures are the **same documented pre-existing failures** recorded at
the accepted baseline in earlier gates (see `M6-INT-01-C01.md` §6):

| Failure | Status |
|---|---|
| `TestVScenarioSwitch::test_scenario_switch_resets_state` | pre-existing, unchanged |
| `TestSelectEndpointNonMutation::test_select_does_not_mutate_runtime_state` | pre-existing, unchanged |

Both are unrelated to deployment (no production code touched).

## Targeted ASSY / observation / timing regression (§16 minimum set)

Files:

```text
test_assy_line.py test_assy_demo.py test_demo_composition.py test_demo_overview.py
test_m6_int_01.py test_m5_s01_envelope.py test_m5_s02_point_policy.py
test_m5_s03_service.py test_m5_s04_projections.py test_m5_s05_gateway.py
test_auto_timing.py test_auto_timing_runtime.py test_auto_timing_snapshot.py
test_auto_equiv_01.py
```

Result:

```text
1 failed, 496 passed in 6.91s
```

The 1 failure is the same pre-existing `TestVScenarioSwitch` failure above.
All ASSY runtime, observation/M6 (envelope, policy, service, projections,
gateway), and timing tests pass.

## Existing deployment use cases not broken (§19.14)

The existing `docker-compose.yml` (continuous process + MQTT/OPC UA + VF2) was
not modified and still validates:

```text
docker compose -f docker-compose.yml config --services
vf2-simulator
mqtt
virtual-factory-api
```
