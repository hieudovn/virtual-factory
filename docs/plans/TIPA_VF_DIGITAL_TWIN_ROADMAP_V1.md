# TIPA Virtual Factory — Manufacturing Digital Twin Roadmap v1.0

**Decision status:** PO/SA APPROVED ROADMAP / P0 PRODUCT TARGET (Issue [#123](https://github.com/hieudovn/virtual-factory/issues/123), 2026-10-31).  
**Implementation status:** NOT IMPLEMENTED. The current repo main baseline was `04fb9413bd5af3c4f0457047267a60b3ea4e94fe`.  
**Related:** #124 is G1B/G1C DESIGN DRAFT; #125 is SA publication; governance PR #131.  
**System of record:** this document is source controlled; approval refers to the *direction/roadmap*, not every future technical detail or deployment.

## 1. Product objective / P0 exit definition
Produce a deterministic, re-playable whole-TIPA Manufacturing Digital Twin capable of serving:
1. **Factory/Area/Line MES** development: Facility→Workshop→Area→Line→Equipment and shop-floor topology, schedule/WO/shift execution, production output/Finished, time-based machine and line status, downtime, WIP/inventory, buffers, process and material genealogy, resource constraints, KPIs and traceability.
2. **QMS P0 demo** development: incoming material IQC, inspection/test evidence, specification/revision, instrument/calibration, per-attempt retest/reinspection, suspect batches, explicit hold/disposition authority, equipment/test impact lineage, Quality Release separate from Finished.
3. **PlantOS/IIoT** observations and events for realistic monitoring/analytics, keeping synthetic provenance and isolation from live TIPA IoT namespaces.
4. One integrated factory run: independent Area/Line modules with physically and causally consistent material, resource and event interaction. Standalone mode remains supported.

**Non-goals P0:** scientifically validated as-built plant; 110 high-fidelity station engines; full Workshop-3 automotive physical route; broad 3D/PLC actuation; production QMS decisions; writes into TIPA source MQTT, MES .63 or live PlantOS without separate approval.

## 2. Bounded fidelity/coverage

| Manufacturing element | P0 target | What must be observable |
|---|---|---|
| Facility / Workshop 1, 2, 3 | F0/F1 | hierarchy, capacity, shift, run, status, WIP/output quality summary |
| Incoming material / IQC | F1 | suppliers/lots, inspection attempts, accepted/held/rejected, receipt to buffer |
| Stator Core / Winding | F1/F2 | operations, batches, input/output WIP, yield, stations and events |
| S2 Varnish / Drying | F2 + selective F3 | batch recipe/profile, temperature/time excursion, test evidence |
| Housing / End Cover | F1 | machining/painting aggregates, genealogy & eligible inventory |
| SSO2 | F2/F3 | stator assembly, parent WIP transfer, quality, buffers |
| Rotor Casting / Shaft / R2 | F1/F2 | material lots, machining/join, capacity, scrap, Rotor supply |
| RSO2 Balance | F2/F3 | measured imbalance, correction, FAIL/RETEST/PASS attempts |
| ASSY SL01–06 | F3 reuse | AP01–AP11, conveyor/operations, AP04 two-parent join, AP06 electrical, AP08 vision, AP11 final QC |
| Measuring instruments / calibration | selective F3 | device identity, calibration effective time, measurement linkage, drift/impact candidates |
| Workshop-3 automotive | F0/F1 | separate identity and bounded aggregate production/quality, not made-up detailed physical route |

F0 = definition/hierarchy only; F1 = bounded aggregate flow; F2 = operation/batch/lot/resource flow; F3 = selected equipment/process/test evidence. A higher fidelity element may feed a lower fidelity aggregate via typed MaterialPorts and observed quantity conversions. All fidelity choices and synthetic approximations must be declared.

The environmental permit **process.pdf** and 110-step SA process register provide reference and completeness checklist, NOT verified as-built layout, BOM, cycle times, safety limits, QA specifications or PLC identity. Unverified assumptions marked `PENDING_TIPA` or `SYNTHETIC_ASSUMPTION`. Do not turn Workshop 3 into a fabricated detailed route.

## 3. Approved stages and gates

| Gate | Responsible | Major deliverables | Exit / decision |
|---|---|---|---|
| G0 | VF SA | Main-as-built audit, reuse/gap inventory | Review complete only; no runtime test claimed |
| G1A | VF SA | Factory/module interface, clock, material ledger, process graph, event/genealogy, ASSY external-input design, fixture oracles | SA/PO design lock; schemas + tests specified, with detailed design separately reviewed |
| G1B | VF SA + consumer SAs | C1/C2/C2b/C3/C4/C5 projection boundary, identity/effective-time, hold authority, mapping matrix | MES/QMS/PlantOS SA sign-off before consumer writes |
| G1C | VF SA/UX + PO | Desktop end-user flows, 9 golden scenarios, data/read models, visual specifications | SA/PO accepts desktop design; no PM self-certification |
| G2A | PM after G1 Design Lock | Shared FactoryRunContext, Event Scheduler, module protocol, atomic Material Ledger, generic 2-producer/1-consumer | Deterministic material/event invariants and regression |
| G2B | PM | TIPA Facility F0/F1, workshops, shifts, WO, operation/line state and rollups | Whole-factory coherent operational envelope |
| G3-S / G3-R / G3-A | Parallelizable PM bounded slices | Stator/SSO2, Rotor/RSO2, ASSY external-input adapter | Local-module contract tests; standalone regressions |
| G3-W3 | PM | Independent W3 F0/F1 aggregate | Facility context, isolated identity and data |
| G3-INT | PM + SA review | One factory run with material join and causal starvation | No phantom WIP; single event timeline; full lineage |
| G4 | PM + QMS SA | Instruments/calibration, quality attempts, suspect trace | SC-04/05/07 proof; effective-hold authority explicit |
| G5 | PM + SA/PO visual | Versioned IIoT/MES/QMS projections, desktop read models/UX | No duplicate business writers; approved views |
| G6 | SA/PO acceptance | Isolated integrated UAT, evidence, replay/observability, regressions | End-to-end scenarios and exact-head/seed/config report |

**Dependencies:** G1A before G2A; G2A before G2B and G3; G3-S/R/A may be developed independently in bounded branches after port contract design; G3-INT needs all three plus shared Material Ledger; G4 data model may develop in parallel but QMS acceptance requires full integrated run. UI prototypes can be developed in parallel after G1C read models, final visual UAT by SA/PO.

## 4. Mandatory scenarios and acceptance oracles
- **SC-01 healthy:** certified synthetic raw/incoming lots → W1/2 streams → qualified SSO2+RSO2 → AP04 two-parent join → AP06/AP08/AP11 → Finished. Genealogy traverses every committed parent and records all source provenance. Finished alone must not infer Quality Release.
- **SC-02 starvation:** shaft/casting capacity outage reduces qualified Rotor → RSO2 input buffer depletion → AP04 waits for material and ASSY throughput falls. Disable every internal ASSY phantom producer in integrated mode.
- **SC-03 varnish excursion:** controlled batch profile outside synthetic temperature/time specification yields measured evidence, suspect material and inspection; not automatically whole-batch NG.
- **SC-04 rotor balance:** FAIL → physical correction → new PASS attempt; preserve both immutable readings and instrument attribution.
- **SC-05 AP06:** FAIL resistance attempt → PASS retest with exactly 3 measurements per attempt where supported; never overwrite initial attempt.
- **SC-06 AP08:** NG → reinspect; observation/quality disposition separation.
- **SC-07 calibration:** retrospective out-of-tolerance device maps to candidate measurements and WIPs by **effective measurement timestamp**, not simply recent deliveries; never auto-NG.
- **SC-08 integrity:** duplicate/late/unmapped identity/invalid source or timestamp rejected, quarantined or idempotently reconciled, not treated as zero or PASS.
- **SC-09 hold-vs-machine:** quality hold/containment does not become equipment breakdown/downtime or fabricate OEE loss.

**G6 mandatory full demonstration:** SC-01, SC-02, SC-04, SC-05, SC-07. Others require contract/targeted integrated checks in P0.

## 5. Roles and governance
- **SA/Lead Designer:** decide design, policies, architecture, interface schemas, scenario fixtures, author source-controlled docs/contract specifications under SA Remote Design Workflow.
- **Consumer SAs:** own MES/QMS/PlantOS ingress, writer authority, data acceptance and source-to-target field mapping. Conflicting owner requires cross-SA decision, not PM improvisation.
- **PM/executor:** code/tests/smoke/deploy only on issue-specific, versioned, SA-approved contract; no architecture reinterpretation, no merge without exact-head SA authorization.
- **SA + PO:** approve user journeys and visual match (design source of truth); PM tests are evidence, not self-approved UX.
- **No direct main pushes; no automatic merge/deploy.** Preflight and CI before any authoritative claims.

## 6. Existing verified reusable implementation vs target (as of reviewed main)
Reuse `virtual_factory.discrete` heap/clock as a reference deterministic scheduler; reuse `assembly.AssyLineRuntime`, six-subline composition and C4 `tipa-assy-demo-v1.1` MES projection; reuse Bottled Water F1/F3 patterns and export adapter. Current `AssyDemoComposition` local upstream seed/replenish and independent subline clock are **not an integrated factory model**. SH-WTP whole-plant open PRs are reference designs, **not implementation in main**. A G0 source review is not an executed test.

## 7. Detailed references
- **Decision/acceptance authority:** [#123](https://github.com/hieudovn/virtual-factory/issues/123).
- **Cross-application draft:** [#124](https://github.com/hieudovn/virtual-factory/issues/124).
- **Report and execution slices:** [#125](https://github.com/hieudovn/virtual-factory/issues/125), [#126](https://github.com/hieudovn/virtual-factory/issues/126), [#127](https://github.com/hieudovn/virtual-factory/issues/127), [#128](https://github.com/hieudovn/virtual-factory/issues/128), [#129](https://github.com/hieudovn/virtual-factory/issues/129).
