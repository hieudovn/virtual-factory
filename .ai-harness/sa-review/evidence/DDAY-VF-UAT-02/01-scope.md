# DDAY-VF-UAT-02 scope — UAT host Run A evidence

## Authorized

1. Inspect the UAT host over SSH.
2. Record container / network / broker / MQTT cadence evidence.
3. Report to VF SA. Do not change VF product code.

## Not authorized

- Run B / VF restart before PlantOS confirms `reset_dday_receive_epoch`
- VF timestamp / contract / topology change
- Storing SSH passwords in git
- Merge of PR #101
