# DDAY-B5 — alarm / downtime sequence

- t=0.0s `SCENARIO_PHASE_CHANGED` phase=NORMAL
- t=102.0s `SCENARIO_PHASE_CHANGED` phase=DEGRADING
- t=126.0s `SCENARIO_PHASE_CHANGED` phase=WARNING
- t=126.0s `ALARM_RAISED` capper warning
- t=150.0s `SCENARIO_PHASE_CHANGED` phase=INTERMITTENT_STOP
- t=150.0s `DOWNTIME_START` capper intermittent stop
- t=170.0s `SCENARIO_PHASE_CHANGED` phase=RECOVERY
- t=170.0s `DOWNTIME_END` capper downtime ended
- t=170.0s `ALARM_CLEARED` capper warning cleared
