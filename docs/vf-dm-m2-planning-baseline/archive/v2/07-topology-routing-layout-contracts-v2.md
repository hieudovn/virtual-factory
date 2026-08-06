# 07-v2 — Topology, Routing, and Layout Contracts (Corrected)

**Date:** 2026-08-05  
**Replaces:** `07-topology-routing-layout-contracts.md`  
**Corrections:** F-007, F-008, F-009

---

## 1. Five Separate Contracts (C-007)

```
SimulationTopology     — structural nodes, ports, connections (WHAT exists)
ProcessDefinition      — operation behavior, capacity, timing (HOW it works)
ScenarioParameters     — time distributions, quality, faults (WHAT scenario)
RoutingSpec            — eligibility rules, priorities (WHERE entities flow)
LayoutSpec             — coordinates, icons, styling (WHERE it appears)
```

Only `SimulationTopology`, `RoutingSpec`, and `LayoutSpec` share stable node/connection IDs.

---

## 2. SimulationTopology (structural only)

```yaml
topology:
  model_id: "tipa_final_assembly_v1"
  version: "1.0.0"
  nodes:
    - id: "SOURCE_SSO2_A"
      type: source
      display_name: "SSO2 Source A"
      output_ports: ["out_1"]
    - id: "AP01"
      type: workstation
      display_name: "Assembly Process 01"
      input_ports: ["in_1"]
      output_ports: ["out_pass", "out_fail"]
    - id: "CP01"
      type: checkpoint
      display_name: "Checkpoint 01"
      input_ports: ["in_1"]
      output_ports: ["out_pass", "out_fail"]
  connections:
    - id: "CONN_001"
      from: "SOURCE_SSO2_A"
      to: "BUF_SHARED_1"
    - id: "CONN_002"
      from: "BUF_SHARED_1"
      to: "AP01"
```

**Excluded from topology:** `process_time_s`, `test_time_s`, `pass_rate`, `capacity`, `failure_rate`, `repair_time_s`. These belong to `ProcessDefinition` and `ScenarioParameters`.

---

## 3. ProcessDefinition

```yaml
process_definition:
  model_id: "tipa_final_assembly_v1"
  version: "1.0.0"
  nodes:
    AP01:
      process_time_s: 30.0
      capacity: 1
    CP01:
      test_time_s: 5.0
```

---

## 4. ScenarioParameters

```yaml
scenario:
  scenario_id: "baseline_001"
  version: "1.0.0"
  quality:
    CP01:
      pass_rate: 0.95                    # PLACEHOLDER
  breakdowns:
    AP01:
      mtbf_s: 3600.0                     # PLACEHOLDER
      repair_time_s: 300.0               # PLACEHOLDER
```

All values marked PLACEHOLDER until customer confirmation.

---

## 5. RoutingSpec (safe conditions — C-008)

### Condition Vocabulary (closed set for MVP)

```yaml
# Supported condition kinds:
#   quality_is: {value}          — entity.quality_status matches
#   rework_lt: {n}               — entity.rework_count < n
#   rework_gte: {n}              — entity.rework_count >= n
#   always                       — unconditional
#   manual                       — user-triggered only

routing:
  routes:
    - id: "ROUTE_AP01_PASS"
      from_node: "CP01"
      from_port: "out_pass"
      to_node: "SINK_OUTPUT"
      priority: 1
      conditions:                    # ALL must match (AND)
        - kind: quality_is
          value: "passed"
    
    - id: "ROUTE_AP01_REWORK"
      from_node: "CP01"
      from_port: "out_fail"
      to_node: "AP01"
      priority: 1
      conditions:
        - kind: quality_is
          value: "failed"
        - kind: rework_lt
          value: 3
    
    - id: "ROUTE_AP01_SCRAP"
      from_node: "CP01"
      from_port: "out_fail"
      to_node: "SINK_SCRAP"
      priority: 2
      conditions:
        - kind: quality_is
          value: "failed"
        - kind: rework_gte
          value: 3
```

**No `eval()`, no arbitrary expressions.** Conditions are validated against a closed vocabulary.

---

## 6. LayoutSpec (stable edge bindings — C-009)

```yaml
layout:
  layout_id: "tipa_final_assembly_v1"
  version: "1.0.0"
  edges:
    - id: "VIS_EDGE_001"              # Visual edge has its own ID
      from_node: "AP01"
      to_node: "CP01"
      path: "straight"
      style: "solid"
      bindings:                        # Read-only projection bindings
        topology_connection_id: "CONN_003"
        route_ids: ["ROUTE_AP01_PASS"]
```

**Rules:**
- Every visual edge has a stable `id`.
- `bindings` are read-only — for UI projection only.
- Layout cannot define routing behavior.
- If `bindings.route_ids` is set, UI can highlight active routes.
