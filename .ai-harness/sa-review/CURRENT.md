# SA REVIEW INBOX

Task: DDAY-VF-UAT-01-C01 — durable Bottled Water MQTT runtime (no UAT deploy)
Status: implementation pushed for SA review; machine status is derived by `run_task_gate.py`. No deploy. No merge.

Authority:
SA Issue hieudovn/virtual-factory#119 plus VF SA TIME-OWNERSHIP ALIGNMENT (2026-10-07T00:15:46Z)
User order: durable CLI + compose artifact; report DURABLE RUNTIME READY FOR VF SA REVIEW then STOP
PR: hieudovn/virtual-factory#101 (base main, head sa/dday-track-b-20261003)

Baselines:
UAT-01 recon: 485af9ac24c66f69db29ef308a144cfebe1e054b
origin/main: f5261c8ca18cd4e01779c0274b55270ba028b4e5
contract_version: dday-bw-b1-v2
dictionary_sha256: cbe389ec7d3c022a78b7853044f08ba148a7b8a41e374931973683c8886b07ca

What this slice does:
- Adds `virtual-factory dday-bw-runtime` (bottled-water-dday / dday-bw-runtime-fr1).
- Adds compose artifact `deploy/dday-vf-uat.compose.yml` (not executed).
- ACKs final STOPPED, fail-closed MQTT, allows repeated deterministic source timestamps.

NOT authorized: UAT deploy, reservation/warmup, PlantOS, TDengine writes, public MQTT, merge, PlantOS PM handoff.
The PM does not self-certify COMPLETE / CLOSED / SA APPROVED / NEXT SLICE AUTHORIZED.
