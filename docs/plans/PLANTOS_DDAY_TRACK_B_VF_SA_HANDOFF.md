# HANDOFF — Virtual Factory Track B for PlantOS / FactoriX IIoT D-Day

**Role for next session:** Virtual Factory Solution Architect / Simulation Architect / Integration Authority  
**Date:** 2026-10-03  
**Program:** PlantOS + Virtual Factory Integrated D-Day  
**Track:** B — Virtual Factory simulation plant and data source  
**Parallel track:** Track A — FactoriX IIoT / PlantOS product experience  
**Status:** READY FOR VF SA EXECUTION  
**Important:** This handoff authorizes planning, contract reconciliation, simulation design, configuration work, test design and bounded VF implementation planning. It does **not** authorize PlantOS UAT deployment, migration, Shift OEE, PLC field work, or unrelated VF scope expansion.

---

## 1. Mission

Build the Virtual Factory side of the D-Day program so that PlantOS / FactoriX IIoT can consume a credible, deterministic, reusable simulated factory.

The target is **not** to build a perfect digital twin of an entire plant.

The target is:

1. model a full factory at a basic operational level;
2. model one production line in significantly more detail;
3. generate realistic realtime telemetry and historian-worthy data;
4. generate deterministic operational abnormalities/events;
5. provide stable IDs and a clean semantic contract for PlantOS;
6. allow PlantOS Track A to build UI/UX in parallel using the same contract;
7. make physical PLC integration later a source replacement/augmentation problem, not a prerequisite.

Core split:

```text
Virtual Factory
= deterministic simulated plant
+ raw operational facts
+ repeatable scenarios

PlantOS / FactoriX IIoT
= operational application
+ semantic context
+ historian
+ calculated signals
+ KPI / analytics
```

VF must not become a duplicate MES or PlantOS KPI engine.

---

## 2. D-Day product story that VF must enable

The final integrated demo must support this operational flow:

```text
Plant Overview
    ↓
detect abnormal production line
    ↓
Production Line View
    ↓
localize abnormal station/asset
    ↓
Asset Performance / Condition
    ↓
Historian investigation
    ↓
explain KPI / energy / productivity impact
```

VF therefore must generate enough evidence for:

- plant/area/line status;
- detailed station state;
- throughput and cycle behavior;
- quality outcomes;
- downtime;
- energy;
- selected asset condition signals;
- alarms/events;
- deterministic degradation and recovery.

The demo must tell one coherent operational story, not present unrelated random tags.

---

## 3. D-Day simulation strategy

Use a two-tier simulation model.

### Tier 1 — Full factory, basic model

Purpose:

- give PlantOS a complete factory hierarchy;
- create a credible "living factory";
- populate Plant Overview;
- provide several areas/lines/assets;
- generate basic realtime/historian/alarm/energy context.

Expected logical factory structure:

```text
FACTORY
│
├── Raw Material / Feeding
├── Production Line 1       ← detailed hero line
├── Production Line 2       ← basic
├── Packaging               ← basic
└── Utilities               ← basic
```

Tier-1 nodes do **not** require high-fidelity physics.

Minimum useful behavior:

- RUNNING / IDLE / STOPPED / FAULT;
- a few meaningful process/operating values;
- power / energy;
- basic condition signals;
- basic alarm/event;
- historian-worthy changing values.

Goal:

> PlantOS opens and immediately looks like a real operating factory, not a tag viewer.

### Tier 2 — One detailed production line

One line is the D-Day hero model.

It must support:

- station/machine structure;
- machine state;
- cycle and speed;
- total/good/reject count;
- downtime;
- quality;
- energy;
- selected condition/process signals;
- alarm/event;
- product/shift/demo context;
- raw facts needed by PlantOS for productivity/KPI/OEE where valid.

Do not attempt to simulate every factory line at this depth.

---

## 4. Current Virtual Factory repository truth

Repository:

`https://github.com/hieudovn/virtual-factory`

Verified current branch:

`main @ f5261c8ca18cd4e01779c0274b55270ba028b4e5`

Important: VF is **not starting from zero**.

Current repository already has:

- configuration/model-driven simulation architecture;
- graph-based plant model;
- measurable industrial telemetry separated from hidden truth;
- MQTT;
- OPC UA;
- REST / WebSocket monitoring path;
- CSV / JSONL export;
- alarm/event support;
- deterministic scenario support;
- asset hierarchy capability;
- analytics/fault lifecycle foundation;
- maintenance/event structures;
- discrete assembly simulation.

### Existing discrete assembly model

Current config:

`configs/plants/tipa_assy_demo.yaml`

Existing assembly runtime includes:

```text
PRE-ASSY
→ AP01
→ AP02
→ AP03
→ ...
→ AP11
```

The config also has:

- deterministic timing;
- fixed random seed;
- configurable station durations;
- quality/retry/NG paths;
- upstream WIP generation;
- production identity;
- multiple ASSY sub-lines.

Existing production identity includes:

```text
TIPA
└── ASSY
    ├── ASSY-SL01
    ├── ASSY-SL02
    ├── ASSY-SL03
    ├── ASSY-SL04
    ├── ASSY-SL05
    └── ASSY-SL06
```

There is already an exception target configured for `ASSY-SL03`.

### Architecture principle already present in VF

Preserve these existing VF rules:

- plant behavior is configuration-driven;
- engine does not hard-code plant-specific IDs;
- sensors publish measured industrial values;
- hidden internal truth is not exposed in industrial mode;
- protocol gateways publish measurable industrial signals;
- deterministic scenarios are preferred for repeatable validation/demo.

Do not violate these principles just to make D-Day faster.

---

## 5. Key architectural decision: reuse, do not fork concepts

The earlier D-Day planning used illustrative names such as:

- `FX-DEMO-01`;
- `ST01...ST06`.

These were conceptual examples only.

They are **not canonical VF IDs**.

VF SA must first decide whether D-Day should use:

### Option A — Extend/reuse current ASSY discrete model

Use when:

- the current AP01–AP11 runtime is sufficient for PlantOS showcase;
- a generic presentation can be achieved by configuration/labels;
- the existing station/quality/production mechanics save time.

### Option B — Create a new generic FactoriX D-Day plant config

Use only if needed because:

- customer-specific TIPA semantics should not be exposed in a generic showcase;
- the full-factory context needs areas beyond the current ASSY line;
- the demo needs utilities/raw material/packaging topology not cleanly expressible with current config.

If Option B is chosen:

- reuse existing VF engine/schema;
- reuse existing discrete runtime concepts;
- do not fork a second engine;
- do not duplicate station/quality/state concepts under different semantics.

Decision must be explicit and documented.

---

## 6. PlantOS integration boundary

PlantOS current core hierarchy remains:

```text
Plant
→ Area
→ Asset
→ Signal
```

D-Day does **not** add a first-class Line entity.

VF line/sub-line must map into PlantOS using bounded semantics such as:

- Area with `role=production_line`;
- Asset for station/machine where appropriate;
- metadata/process configuration for display/grouping.

VF must expose stable enough identity so that PlantOS Track A can develop against mock data before VF is complete.

---

## 7. Contract-first working model

Track A and Track B run in parallel.

Required sequence:

```text
Signal / semantic contract frozen
          ↓
PlantOS mock fixtures      VF implementation
          ↓                     ↓
UI screens ready           first real payload
          └──────────┬──────────┘
                     ↓
              source replacement
                     ↓
            integrated verification
```

Important rule:

> Track A should not wait for VF to be finished.

Therefore VF SA must prioritize early delivery of:

1. stable topology IDs;
2. signal dictionary;
3. sample payloads;
4. event schema;
5. deterministic scenario definition.

These are more urgent than polishing all simulation details.

---

## 8. Raw fact families VF must provide

### A. Machine state

Minimum:

- operating state;
- run/idle/stop/fault distinction;
- timestamped state transition;
- current state.

Required truth rules:

- STOPPED != FAULT;
- IDLE != automatically downtime;
- UNKNOWN != STOPPED.

### B. Production

Minimum detailed-line facts:

- total_count;
- good_count;
- reject_count;
- cycle_time;
- actual production rate;
- target rate/context if available.

Invariant:

`good_count + reject_count <= total_count`

Do not silently reset counters during one demo run.

### C. Downtime

VF should provide enough timestamped state/event facts for PlantOS to calculate or aggregate downtime.

Minimum event logic:

`asset/station | start | end | reason/state | planned? | scenario_id`

### D. Energy

Minimum:

- active power;
- cumulative energy.

Prefer VF to provide raw power and/or cumulative energy.

PlantOS should calculate energy/unit where practical.

### E. Condition

The hero abnormal machine should have a small but convincing set such as:

- motor current;
- load;
- bearing temperature;
- vibration RMS.

These signals must move coherently with the abnormal scenario.

### F. Quality

Minimum:

- PASS / FAIL / NG result;
- reject count;
- retry/rework path where current discrete runtime supports it.

Do not equate asset condition with product quality.

### G. Alarm / event

Need event evidence for:

- warning;
- stop/trip where relevant;
- quality exception;
- recovery/reset if part of the scenario.

Alarm truth must remain distinct from simply changing a signal value.

---

## 9. Deterministic hero abnormal scenario

D-Day requires one repeatable abnormal scenario.

Recommended pattern:

```text
NORMAL
  ↓
DEGRADING
  ↓
WARNING
  ↓
INTERMITTENT STOP
  ↓
RECOVERY
```

Suggested causal pattern:

```text
load ↑
  ↓
motor current ↑
  ↓
vibration ↑
  ↓
bearing temperature ↑
  ↓
cycle time ↑
  ↓
throughput ↓
  ↓
energy/unit ↑
  ↓
warning
  ↓
intermittent stop / downtime
```

The exact hero station is **not pre-frozen**.

VF SA must choose the best existing AP station based on current runtime mechanics.

Selection criteria:

- can host a machine/drive/motor concept credibly;
- can affect cycle/throughput;
- can produce or be extended to produce energy/condition signals;
- does not require large engine changes;
- supports a clear before/during/after historian story.

If no current AP station can do this cleanly, propose the smallest configuration-driven extension.

Do not create a completely new station model only to match the example.

---

## 10. Recommended D-Day scenario controls

The simulation should support a controlled way to:

- start normal state;
- trigger degradation;
- advance to warning;
- trigger intermittent stop;
- recover;
- reset the full scenario.

Preferred properties:

- deterministic;
- scriptable;
- repeatable across rehearsals;
- same IDs and same event order;
- optionally adjustable speed multiplier;
- scenario ID included in evidence/logging.

Avoid purely random failure timing for the main D-Day story.

Random noise may still exist inside realistic bounds.

---

## 11. Historian-oriented data behavior

VF data must be useful not just in realtime but in PlantOS Historian.

Important characteristics:

- values change over time;
- related signals move with believable causal lag;
- timestamps are valid;
- no pathological same-timestamp overwrite pattern;
- units are explicit;
- signal cadence is known;
- state/event transitions are distinguishable from analog trends.

Suggested D-Day cadence ranges:

| Signal family | Guidance |
|---|---|
| state | on change + current/heartbeat |
| motor current/load | 1–2 s |
| vibration RMS | 1–2 s |
| power | 1–2 s |
| temperature | 2–5 s |
| cumulative energy | 2–5 s |
| counts | on change or ~1 s |
| alarm/event | event driven |

These are demo guidance, not universal plant standards.

---

## 12. Provenance

VF → PlantOS data must identify source provenance logically.

Minimum source classes:

- `SIMULATED_RAW`;
- later `PHYSICAL_RAW` where applicable;
- `CALCULATED` belongs to PlantOS;
- `CONFIGURED_TARGET` for target/context values.

Do not label a PlantOS calculated KPI as raw simulated telemetry.

Do not expose hidden benchmark truth as industrial telemetry just because it is convenient.

---

## 13. What VF must NOT calculate just to make the dashboard work

VF should not become the canonical producer of:

- OEE;
- Availability;
- Performance KPI;
- Quality KPI percentage;
- energy/unit;
- utilization;
- generic health score;
- shift KPI aggregation.

VF may provide raw facts needed to calculate them.

PlantOS Track A owns the operational KPI layer, subject to current capability.

If PlantOS cannot yet calculate a KPI truthfully, the integrated demo should show unavailable/partial status rather than pushing a fake value from VF.

---

## 14. Track B work packages

### B1 — Existing capability audit

Deliver:

- what the current discrete ASSY runtime already produces;
- current protocols;
- exact signal/event names;
- which simulation mechanics are reusable;
- gaps against D-Day contract.

### B2 — Factory topology & ID freeze

Deliver:

- chosen D-Day factory structure;
- whether TIPA ASSY is reused directly or a generic config is created;
- stable plant/area/line/station/asset IDs;
- mapping-ready hierarchy.

### B3 — Signal dictionary & sample payloads

Deliver machine-readable dictionary:

`signal_id | asset/station | semantic role | datatype | unit | cadence | provenance | publish path`

Also deliver sample payloads for:

- analog measurement;
- machine state;
- count;
- quality;
- alarm/event;
- downtime transition.

### B4 — Living Factory basic model

Implement enough data for:

- full-factory Plant Overview;
- multiple areas;
- basic operational status;
- energy;
- alarms;
- historian.

### B5 — Detailed hero line

Implement:

- station state;
- cycle;
- counts;
- quality;
- downtime;
- energy;
- condition signals.

### B6 — Deterministic abnormal scenario

Implement and prove:

- NORMAL;
- DEGRADING;
- WARNING;
- STOP;
- RECOVERY.

### B7 — PlantOS integration proof

Demonstrate:

- first actual payload reaches PlantOS-compatible ingestion path;
- stable IDs resolve;
- current value;
- historian data;
- events;
- no semantic duplication.

Do not attempt full UI acceptance — that is Track A.

---

## 15. First authorized slice

Use PlantOS Issue:

**#38 — DDAY-WP2-CONTRACT-01 — Reconcile VF Living Factory Contract**

This is currently the primary cross-workstream contract/mapping task.

The immediate VF SA responsibility is to provide evidence for that issue, specifically:

1. exact publishable signals emitted by the current discrete ASSY runtime;
2. units/datatype/cadence;
3. current output protocols;
4. mapping candidate to PlantOS Plant/Area/Asset/Signal;
5. reusable event contracts;
6. best hero AP station recommendation;
7. minimal gaps/extensions.

Do not jump immediately to building a new factory model before this audit is complete.

---

## 16. Explicit non-scope for Track B at this stage

Do not expand into:

- ERP simulation;
- full MES;
- complete scheduling;
- purchasing;
- warehouse;
- complex BOM/routing;
- manpower optimization;
- maintenance management workflow;
- exact physics for every asset;
- broad AI/PdM development;
- new 3D visualization;
- production PLC integration.

D-Day goal is an operational IIoT showcase, not a complete manufacturing software stack.

---

## 17. Definition of Track B ready

VF Track B is considered D-Day ready when:

1. one factory topology is stable;
2. one detailed production line is stable;
3. IDs are deterministic;
4. signal dictionary is frozen;
5. PlantOS can ingest the agreed raw facts;
6. realtime values change credibly;
7. historian has useful multi-signal data;
8. hero abnormal scenario is repeatable;
9. downtime/quality/energy/condition impacts are coherent;
10. hidden truth remains hidden from industrial mode;
11. no duplicate KPI semantics are introduced;
12. recovery/reset works for repeated demo rehearsal.

---

## 18. Required report format back to SA

VF SA should report in this order:

### A. Current repo truth
- branch/SHA;
- reusable modules/configs;
- actual current signal/event outputs.

### B. Architecture decision
- reuse TIPA ASSY vs new generic D-Day config;
- rationale;
- no-duplication analysis.

### C. D-Day factory model
- hierarchy;
- detailed line;
- selected hero abnormal station.

### D. Signal/data contract
- dictionary;
- units;
- cadence;
- provenance;
- protocol.

### E. Gap analysis
Classify each item:

- ALREADY EXISTS;
- CONFIG/MAPPING ONLY;
- SMALL EXTENSION;
- HIGH-RISK / POST-D-DAY.

### F. Implementation plan
Prefer 4–6 bounded slices, not dozens of microtasks.

### G. Evidence
- config paths;
- sample payloads;
- tests;
- runtime screenshots/logs only where they prove a specific claim.

---

## 19. Governance

Apply risk-tier discipline.

### LOW
- labels;
- names;
- demo config values;
- non-semantic docs.

Light review.

### MEDIUM
- new D-Day plant config;
- signal mapping;
- new station data output;
- scenario configuration;
- PlantOS adapter changes.

Focused tests + runtime evidence.

### HIGH
- simulation engine changes;
- timestamp semantics;
- persistence/history semantics;
- protocol behavior affecting existing users;
- major new event model;
- changes that expose hidden truth.

Full harness / architecture review.

Rules:

- repository is source of truth;
- no silent scope expansion;
- evidence required;
- existing engine concepts before new concepts;
- config before hard-coded behavior;
- industrial telemetry != hidden ground truth;
- raw facts != KPI calculations.

---

## 20. Coordination contract with Track A

Track A will proceed independently on:

- FactoriX branding/shell;
- Plant Overview;
- Production Line View;
- Asset Condition;
- Asset Performance;
- Energy;
- Productivity;
- KPI Monitoring;
- Historian UX.

Track A may use mock data before VF is ready.

Therefore VF Track B must communicate contract changes early.

Once signal IDs/schema are frozen:

`CONTRACT CHANGE => explicit SA review`

Do not casually rename signals/IDs after Track A starts binding fixtures to the agreed contract.

---

## 21. Success principle

The desired result is not:

> “Virtual Factory has many simulation features.”

The desired result is:

> “PlantOS can show a believable factory, detect an operational problem, drill into the affected line and asset, prove it with historian data, and explain the operational impact — using VF as a deterministic raw-data source.”

That is the Track B mission.
