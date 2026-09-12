# VF-SHW-X3 evidence summary

Overall: **SHW_X3_PHYSICAL_BOUNDS_AND_TWO_PI_VERIFIED**

| section | verdict |
|---|---|
| 01 | X3_SURFACE_MATERIALIZED_16_SCOPES_TWO_PI |
| 02 | PLANT_WATER_IDENTITY_CLOSED_FROM_TICK_ZERO |
| 03 | RESERVATIONS_ARE_CAPACITY_TOKENS_NOT_WATER |
| 04 | TWO_PI_ACTUATOR_RESPONSE_AND_ARBITRATION_VERIFIED |
| 05 | PUMP_ENVELOPE_FEASIBLE_WITH_EXPLICIT_UNITS |
| 06 | MUTATIONS_VIOLATE_THE_PHYSICAL_ENVELOPE |
| 07 | X3_CANONICAL_WITH_X2_AND_G21_COMPATIBILITY |
| 10 | ENERGY_INTEGRATED_FROM_ACHIEVED_PUMPED_THROUGHPUT |
| 11 | ACTUATOR_TRACKING_AND_RELEASE_SLEW_VERIFIED |

Key machine-derived numbers:

- water: invalid ticks 0, worst residual 2.000e-12 m3 (tick 432), created water 0.000e+00 m3
- control: last PI-owned window tick 5400, flow error 0.0000% of SP, level error 0.0366 m, backwash at tick 3356 with the integral held
- pumps: total energy 4.207 MJ; DIST loss conversion configured 79266.06 s^2/m^5 vs expected 79266.06 s^2/m^5
- identity: canonical model whole_plant_x3 at 1.0 s, X2 compatible at 60.0 s, G21 scopes 5
- setpoint sweep: flow 0.00600 -> 0.00900 m3/s (valve 48.00 -> 72.00 %), level 2.2305 -> 2.6269 m (pump 58.21 -> 67.09 %)
- C01-1 actuator tracking: SA counterexample 90.0 % -> stop 0.0 % (tracked 0.0 %) -> release step 0.000 pp (limit 10.0 pp/s); protective epilogues 6; runtime slew violations 0
- C01-2 realized energy: total 4.207016 MJ (idle 0.102650 MJ, pumped 4.104366 MJ); capacity-basis substitution differs by up to 1.763154 MJ
- acceptance: 9/9 criteria PASS (X3C01-1, X3C01-2 + the X3-1..X3-7 regression re-assertions, evaluated by .ai-harness/scripts/evaluate_acceptance.py against the VF-SHW-X3-C01 contract; rules x3c01.actuator_tracking / x3c01.energy_from_actual_flow / x3.*)

Every number above is produced by `generate_evidence.py` from the committed model at
the reported head; no value is transcribed by hand.
