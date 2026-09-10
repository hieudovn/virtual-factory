# SA REVIEW INBOX

Task: VF-vNEXT-G25
Status: READY FOR SA REVIEW (Integrated Multi-Workspace Demo / MVP Acceptance)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G24 complete)
Prerequisite: G24-C01 accepted; Issue #76 (G25) current

Gate type:
ACCEPTANCE / HARDENING gate — Integrated Multi-Workspace Demo / MVP Acceptance,
per Issue #76. No new architecture. Proves both accepted Workspaces end-to-end
through the Workspace Shell backend (G23 registry + G22 RuntimeSession), records
deterministic evidence, and delivers a milestone acceptance report.

Base:
G24-C01 head = 0ca571e2a490502683cf41ae7c1b22822217d1fa
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (tests + evidence only; no production code change):
- tests/test_vnext_g25_acceptance.py (24 integrated acceptance tests:
  FLOW A TIPA, FLOW B SH-WTP, platform invariants, frozen invariants)
- .ai-harness/sa-review/evidence/VF-vNEXT-G25/ (generate_evidence.py +
  flow-a-tipa.json + flow-b-shwtp.json + invariants.json; deterministic)
- .ai-harness/sa-review/reports/VF-vNEXT-G25.md (milestone acceptance report)
- .ai-harness/regression/vnext_baseline_manifest.json (G25 gate context +
  g25_acceptance group)

FLOW A TIPA: shell opens; selector from backend registry; select TIPA uses the
selected G22 RuntimeSession; step proves six live ASSY sub-lines from that
session; reset/new-attempt/replay explicit + deterministic; switch to SH-WTP and
back does not mutate TIPA; /assy-demo labelled a separate legacy runtime.

FLOW B SH-WTP: select shwtp; runs RAW-INTAKE -> T100 -> T106 -> T108 ->
DIST-P108; live time/step/flow/tank/status; fidelity/status/assumed topology
explicit; reset/new-attempt/replay deterministic; switch to TIPA and back does
not mutate SH-WTP.

Re-proven: one platform -> many independent Workspaces; no shared
state/run_id/clock/truth; no cross-workspace runtime coupling; RuntimeSession
lifecycle reused; explicit_lagged/G4/G19 unchanged; ASSY oracle green; SH-WTP
assumptions never site truth.

Frozen boundaries preserved:
No gateway routing / production export / multi-gateway / store-and-forward;
no SH-WTP whole-plant/site-faithful; no T110/Line2; no distributed execution /
advanced coupling; no broad UI redesign; no PIM/MES change.

Authority unchanged:
vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED;
whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Regression: G25 acceptance 24 passed; full suite PASS; complete canonical vNext
baseline PASS (see report).

G25 started: YES (completed; READY FOR SA REVIEW)
Next gate started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G25.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G25/
