# DDAY-B5-C02 — compressor-targeted classification

Context: `{'downtime_code': 'DT-AIR', 'failure_code': 'FAIL-AIR', 'top_level_downtime_code': None}`

Stamped compressor events:

- `SCENARIO_PHASE_CHANGED` phase=LOW_PRESSURE_WARNING dt=DT-AIR fail=FAIL-AIR
- `ALARM_RAISED` compressor low pressure dt=DT-AIR fail=FAIL-AIR
- `SCENARIO_PHASE_CHANGED` phase=UNDERSUPPLY dt=DT-AIR fail=FAIL-AIR
- `ALARM_CLEARED` compressor pressure restored dt=DT-AIR fail=FAIL-AIR
