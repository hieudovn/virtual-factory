# 07 — Topology, Routing, and Layout Contracts

**Date:** 2026-08-05

---

## 1. Principle: Three Separate Contracts

```
SimulationTopology  ─── WHAT exists (nodes, connections)
RoutingSpec         ─── HOW entities flow (rules, eligibility)
LayoutSpec          ─── WHERE it appears (x, y, icons, styling)
```

These share stable IDs but are separate, immutable specifications.

---

## 2. SimulationTopology

```yaml
# Example: TIPA-oriented but generic structure
topology:
  model_id: "tipa_final_assembly_v1"
  version: "1.0.0"
  groups:
    - id: "line_1"
      display_name: "Assembly Line 1"
      nodes: ["AP01", "AP02", "AP03"]
  nodes:
    - id: "SOURCE_SSO2_A"
      type: source
      display_name: "SSO2 Source A"
      output_ports: ["out_1"]
    - id: "BUF_SHARED_1"
      type: buffer
      display_name: "Shared Buffer 1"
      capacity: 10
      input_ports: ["in_1"]
      output_ports: ["out_1"]
    - id: "AP01"
      type: workstation
      display_name: "Assembly Process 01"
      process_time_s: 30.0
      input_ports: ["in_1"]
      output_ports: ["out_pass", "out_fail"]
    - id: "CP01"
      type: checkpoint
      display_name: "Checkpoint 01"
      test_time_s: 5.0
      pass_rate: 0.95
      input_ports: ["in_1"]
      output_ports: ["out_pass", "out_fail"]
    - id: "SINK_OUTPUT"
      type: sink
      display_name: "Finished Goods"
      input_ports: ["in_1"]
  connections:
    - from: "SOURCE_SSO2_A"
      to: "BUF_SHARED_1"
    - from: "BUF_SHARED_1"
      to: "AP01"
    - from: "AP01"
      to: "CP01"
    - from: "CP01"
      to: "SINK_OUTPUT"
      port: "out_pass"
```

---

## 3. RoutingSpec

```yaml
routing:
  model_id: "tipa_final_assembly_v1"
  version: "1.0.0"
  routes:
    - id: "ROUTE_AP01_PASS"
      from_node: "CP01"
      from_port: "out_pass"
      to_node: "SINK_OUTPUT"
      priority: 1
      condition: "quality == 'passed'"
    - id: "ROUTE_AP01_FAIL"
      from_node: "CP01"
      from_port: "out_fail"
      to_node: "AP01"
      to_port: "in_1"
      priority: 1
      condition: "quality == 'failed' and rework_count < 3"
    - id: "ROUTE_AP01_SCRAP"
      from_node: "CP01"
      from_port: "out_fail"
      to_node: "SINK_SCRAP"
      priority: 2
      condition: "quality == 'failed' and rework_count >= 3"
    - id: "LINE_IN_AP01"
      from_node: "SOURCE_LINE_IN"
      to_node: "AP01"
      priority: 0
      trigger: "manual"
    - id: "LINE_OUT_AP01"
      from_node: "AP01"
      to_node: "SINK_LINE_OUT"
      priority: 0
      trigger: "manual"
```

**Rules:**
- Routes are evaluated in priority order (lower = first).
- First matching condition wins.
- `trigger: manual` means only via user command, never automatic.
- Cycle protection: `rework_count < N` on rework routes.

---

## 4. LayoutSpec

```yaml
layout:
  layout_id: "tipa_final_assembly_v1"
  version: "1.0.0"
  canvas:
    width: 1400
    height: 800
  lanes:
    - id: "lane_ap01_ap03"
      label: "AP01–AP03"
      y: 100
      height: 180
    - id: "lane_ap04_ap06"
      label: "AP04–AP06"
      y: 350
      height: 180
  nodes:
    - id: "SOURCE_SSO2_A"
      x: 50
      y: 190
      icon: "source"
    - id: "AP01"
      x: 300
      y: 140
      width: 120
      height: 80
      icon: "workstation"
      label_position: "top"
    - id: "CP01"
      x: 480
      y: 140
      width: 100
      height: 60
      icon: "checkpoint"
  edges:
    - from: "SOURCE_SSO2_A"
      to: "BUF_SHARED_1"
      path: "straight"
      style: "solid"
    - from: "CP01"
      to: "AP01"
      path: "curved_back"
      style: "dashed"
      label: "rework"
```

**Rules:**
- Layout may be fixed for MVP (hard-coded in `layouts/tipa-final-assembly-v1.js`).
- Visual edge must not define execution routing.
- Node IDs must match topology IDs.
- Layout version independent of topology/routing version.

---

## 5. Validation

| Contract | Validation Rules |
|----------|-----------------|
| Topology | All connection endpoints exist as nodes. Ports match node type. No orphan nodes. |
| Routing | All route endpoints exist in topology. Conditions reference valid entity attributes. No infinite rework loops. |
| Layout | All layout node IDs exist in topology. Coordinates within canvas bounds. No overlapping nodes at same position. |
