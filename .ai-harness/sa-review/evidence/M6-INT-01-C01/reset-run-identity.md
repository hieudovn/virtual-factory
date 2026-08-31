# M6-INT-01-C01 — Reset / run identity

```text
run to t=6000s → poll → run_id=ASSY-SL01:R1
reset (t=0) → poll → run_id=ASSY-SL01:R2
step1 (t=100s) → poll → run_id=ASSY-SL01:R2
step2 (t=200s) → poll → run_id=ASSY-SL01:R2
step3 (t=300s) → poll → run_id=ASSY-SL01:R2
step4 (t=400s) → poll → run_id=ASSY-SL01:R2
step5 (t=500s) → poll → run_id=ASSY-SL01:R2
second reset → poll → run_id=ASSY-SL01:R3
```
