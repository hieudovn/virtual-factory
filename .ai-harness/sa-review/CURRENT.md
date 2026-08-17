# SA REVIEW INBOX

Task: VF-DEPLOY-01
Status: READY FOR SA REVIEW

VF Accepted Contract Baseline: f72cc9564b251c3812c2b6070bddd37e479d5ea5
VF Accepted Demo Build: 494c12e265d297a389e4463848b9c0b6aafed0b1
Baseline: 18d253d632ee9c939a206e28c27fcebdea61af50
Head: 6e68ec9 (deployment implementation/evidence head)

Report:
.ai-harness/sa-review/reports/VF-DEPLOY-01.md

Evidence:
.ai-harness/sa-review/evidence/VF-DEPLOY-01/

Production code changed: NO
Simulation semantics changed: NO
VF producer contract changed: NO
MES integration added: NO
Docker result: PASS

Summary:
Added docker-compose.assy.yml (Option A — separate file, generic Dockerfile
reused unchanged) running `virtual-factory serve --host 0.0.0.0 --port 8000`
with VF_ENABLE_S04B_OVERVIEW=1 and TIPA_ASSY_CONFIG container path. Real
healthcheck on /health; container reaches healthy; all 6 required ASSY
endpoints 200; 6 sub-lines (SL01-SL06) exposed; runtime control
(reset/step/mode/select/scenario) 200. Native vs Docker equivalence
E1-E4: fingerprints EQUIVALENT (all PASS) including full ordered message_keys
(1254/2335/3494). Restart and down/up return clean healthy state (ephemeral).
Regression: 1554 passed + 2 pre-existing failures (unchanged); targeted
ASSY/observation/timing 496 passed + 1 pre-existing. Existing compose intact.
Docs: docs/deployment/assy-docker.md. Future MES E2E shared network
documented (one-line external network change), not connected. No MES
integration added.

