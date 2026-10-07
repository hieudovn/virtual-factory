# DDAY-VF-UAT-01 — known limitations (recon)

- Deployment remains BLOCKED. No VF container was started.
- Live `plantos-net` / EMQX / EDGE-DDAY-01 / TDengine were not independently inspected (no Docker/SSH from this agent).
- TDengine max source timestamp is UNKNOWN; SA lower bound t≥610 s is cited, not measured.
- `MqttGateway` cannot set broker username/password; credentialed EMQX would be a new blocker.
- Proposed launcher/warmup are design only.
- Warmup-by-stepping past existing historian coverage will skip unpublished Capper/Compressor hero windows.
- Frozen PlantOS FR2 simulated-history/aggregate fixtures were not mutated (no UAT writes).
- PR #101 is not merged. PlantOS PM is not handed this slice.
