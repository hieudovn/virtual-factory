# DDAY-VF-UI-DEPLOY — scope

Authority: SA Issue #121. Parent #118.

## Authorized

1. Deploy the existing Bottled Water visual skin on UAT as **FactoriX Sim**.
2. Public routes `/factorix-sim` and `/factorix-sim/overview`, with `/bottled-water-demo` aliases.
3. Bind HTTP to the same `BottledWaterFactory` already owned by `dday-bw-runtime`.
4. Recreate `virtual-factory-dday` once the HTTP listener is required (evidenced).
5. Keep MQTT client-id, topics, contract, and PlantOS path unchanged.

## Not authorized

- Rebuild the simulator or 8-station skin
- Rename workspace/source/topic/contract IDs for branding
- A second independent `BottledWaterFactory`
- Public MQTT or TDengine
- PlantOS KPI/OEE inside FactoriX Sim
- PlantOS production code change
- Issue #91
- Merge to main

## Conservative interpretation

A separate UI process that constructs its own factory would be a second truth.
HTTP is an optional listener on the MQTT process (`factory_autorun=False`).

Overview HTML/JS stay at the accepted C01 frozen hashes. FactoriX Sim chrome
is applied at HTML serve time.
