# DDAY-B5 — production / FG impact

Capper hero window:

- NORMAL: total=0 good=0 fg=0 cycle_time=20.0
- DEGRADING: total=5 good=0 fg=0 cycle_time=25.0
- WARNING: total=6 good=0 fg=0 cycle_time=31.0
- INTERMITTENT_STOP: total=6 good=0 fg=0 cycle_time=20.0
- RECOVERY: total=6 good=0 fg=0 cycle_time=20.0

Compressor secondary window:

- t=1 NORMAL: total=0 good=0 fg=0
- t=240 DEGRADING: total=9 good=2 fg=2
- t=264 LOW_PRESSURE_WARNING: total=10 good=3 fg=3
- t=284 UNDERSUPPLY: total=11 good=4 fg=4
- t=304 RECOVERY: total=11 good=4 fg=4

UNDERSUPPLY freezes line counts and FG receipts. FG follows actual good output.
