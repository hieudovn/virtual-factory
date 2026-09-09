# SA REVIEW INBOX

Task: VF-vNEXT-G21
Status: READY FOR SA REVIEW (SH-WTP Functional Simulation Expansion)
Parent: Implementation phase (umbrella #39 VF-vNEXT-ARCH; gates G1-G20-C01 complete)
Prerequisite: Issue #71 (G20-C01) accepted; Issue #72 (G21) current

Gate type:
IMPLEMENTATION gate — SH-WTP Functional Simulation Expansion, per Issue #72.
Additive 5-scope plant slice (RAW-INTAKE -> T100 -> T106 -> T108 -> DIST-P108).
No gateway routing, no MQTT/Kafka/REST, no PIM/T110/whole-plant/site-faithful.

Base:
G20-C01 head = 65a2581ef825a79f8f088c0bc7672b249e96c942
Production base SHA: canonical main @ f5261c8 (inspected; not merged)

Implemented (additive, isolated):
- src/virtual_factory/shwtp/expansion.py (PlantSliceScope + 5 participant
  adapters + build_shwtp_plant_slice; reuses T106/T108 runtimes, G18 overlay,
  G4 coordinator, explicit_lagged)
- tests/test_vnext_g21_shwtp_expansion.py (21 tests)
- .ai-harness/regression/vnext_baseline_manifest.json (G21 gate context +
  g21_shwtp_expansion group)

Frozen boundaries preserved:
TIPA ASSY behavior; G20/G19/G18/G14/G15; reference connectivity graph; T106/T108
standalone runtimes; PIM pins. No gateway routing, no MQTT/Kafka/REST, no T110
runtime, no whole-plant/site-faithful claim, no G4 redesign.

Authority unchanged:
vf_runtime_authorization NOT_AUTHORIZED; site_authorized_execution NOT_AUTHORIZED;
whole_plant_runtime NOT_AUTHORIZED / NOT_IMPLEMENTED.

Regression: G21 21 passed; full suite 2398 passed; complete canonical vNext
baseline PASS (see report).

G21 started: YES (completed; READY FOR SA REVIEW)
Next gate started: NO

Report:
.ai-harness/sa-review/reports/VF-vNEXT-G21.md

Evidence:
.ai-harness/sa-review/evidence/VF-vNEXT-G21/01-shwtp-expansion.md
