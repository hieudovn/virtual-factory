# DDAY-FR1 — freeze Bottled Water D-Day runtime profile

## Status

Machine status is derived by the full canonical task gate.

The PM does not self-certify `COMPLETE`, `CLOSED`, `SA APPROVED`, or `NEXT SLICE AUTHORIZED`.

## Task Interpretation

| Field | Value |
|---|---|
| Task ID | `DDAY-FR1` |
| Authority | SA Issue `#117` |
| Parent program | PlantOS `#54` DDAY-FINAL-01 — VF SA reviews; do not hand to PlantOS PM |
| PR | `#101` |
| Baseline | accepted C03 head `320d82fb2fb3339461553e258b09ebee6689615a` |
| Contract | `dday-bw-b1-v2` |
| Scope | One explicit mixed-cadence D-Day runtime profile for 22 measurements |
| Out of scope | merge, deploy, PlantOS handoff, new engine, topology/scenario/UI edits |

## Correction

Replace every-signal-every-snapshot live publishing with FAST 1 s / MEDIUM 5 s / SLOW 10 s / COUNT on-change+heartbeat / EVENT event-driven transport, without changing `map_snapshot()` purity or accepted VF semantics.

## Governance refresh (SA 2026-10-05)

VF SA conditional accept: regenerate `.ai-harness/sa-review/evidence/DDAY-FR1/machine-evidence.json` so `head` equals the reviewed implementation SHA `dd6cfe466832b4c167f49861d27f718291f78699`. Bounded-run figures are unchanged (511 / 8.517 msg/s / 0 reject). No runtime code change.

NOT authorized: merge of PR #101, B7 deploy, PlantOS #49/#54, or PlantOS PM handoff.
