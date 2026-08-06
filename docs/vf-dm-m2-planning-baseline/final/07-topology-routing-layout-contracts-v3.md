# 07-v3 — Topology, Routing, Layout Contracts (Final)

**Date:** 2026-08-05  
**Replaces:** `07-...-v2.md`  
**Corrections:** V2-F07

---

## 1. Five Contracts (unchanged)

```
SimulationTopology     — structural nodes, ports, connections
ProcessDefinition      — operation behavior, capacity, timing
ScenarioParameters     — time distributions, quality, faults
RoutingSpec            — eligibility rules, priorities
LayoutSpec             — coordinates, icons, styling
```

All reference stable topology node IDs.

---

## 2. SimulationTopology (unchanged structure)

Nodes have stable `id` fields. Connections reference node IDs + port names.

---

## 3. RoutingSpec — Safe Conditions (unchanged)

Closed vocabulary:
- `quality_is: {value}`
- `rework_lt: {n}`
- `rework_gte: {n}`
- `always`
- `manual`

No `eval()`. No arbitrary expressions.

---

## 4. LayoutSpec — Edge Bindings (corrected example)

```yaml
layout:
  edges:
    - id: "VIS_EDGE_PASS"
      from_node: "CP01"
      to_node: "SINK_OUTPUT"
      path: "straight"
      style: "solid"
      bindings:
        topology_connection_id: "CONN_005"
        route_ids: ["ROUTE_AP01_PASS"]    # Matches CP01→SINK_OUTPUT route

    - id: "VIS_EDGE_REWORK"
      from_node: "CP01"
      to_node: "AP01"
      path: "curved_back"
      style: "dashed"
      label: "rework"
      bindings:
        topology_connection_id: "CONN_006"
        route_ids: ["ROUTE_AP01_REWORK"]  # Matches CP01→AP01 rework route
```

Route bindings now correctly match the actual execution routes they represent.
