# Prompt for Coder — VF-2 ST04: Topology & Dependency Engine

> **Parent:** VF-2 PIM-native Simulation Runtime  
> **Task:** VF2-ST04 — Topology & Dependency Engine  
> **Prerequisite:** ST01-ST03 completed (loader, validator, registries working)

---

## Context

Build the topology engine that resolves signal dependencies from the package's process + electrical edges. This replaces VF-1's hardcoded 8-stage WTP chain with a generic graph-based dependency resolver.

---

## What You're Building

### `topology_engine.py`

```python
from simulators.vf2.models import VF2Package, VF2Topology, VF2ProcessEdge
from simulators.vf2.object_registry import ObjectRegistry
from simulators.vf2.signal_registry import SignalRegistry

@dataclass
class TopologyGraph:
    """Directed graph built from package topology + signal dependencies."""
    
    # Adjacency: {object_id: [downstream_object_ids]}
    process_flow: dict[str, list[str]]
    
    # Electrical connectivity: {feeder_id: [powered_object_ids]}
    electrical: dict[str, list[str]]
    
    # Signal dependency DAG: {signal_id: [upstream_signal_ids]}
    signal_deps: dict[str, list[str]]
    
    # Execution order (topological sort of signal_deps)
    eval_order: list[str]
    
    # Boundary endpoints (referenced in topology but not in objects[])
    boundary_endpoints: set[str]


class TopologyEngine:
    """
    Builds and queries the topology/dependency graph.
    
    Uses:
    1. Package topology.process_edges → process flow graph
    2. Package topology.electrical_edges → electrical graph
    3. Signal behavior (direction, signal_type) → dependency inference
    """
    
    def __init__(self, pkg: VF2Package, obj_reg: ObjectRegistry, sig_reg: SignalRegistry):
        ...
    
    def build(self) -> TopologyGraph:
        """
        Build the full topology graph.
        
        Steps:
        1. Process flow graph from process_edges
        2. Electrical graph from electrical_edges  
        3. Signal dependency DAG:
           - Measurement signals depend on the status of their parent object
           - Feedback signals depend on associated command/setpoint signals
           - Signals on downstream objects depend on upstream object signals
        4. Topological sort of signal deps for evaluation order
        5. Identify boundary endpoints (not in objects[])
        """
        ...
    
    def get_downstream_objects(self, object_id: str) -> list[str]:
        """Objects downstream of the given object in process flow."""
        ...
    
    def get_affected_signals(self, object_id: str, sig_reg: SignalRegistry) -> list[str]:
        """
        Return all signal IDs that would be affected if this object fails.
        
        Includes:
        - Direct signals on the object
        - Signals on downstream objects (via process flow)
        - Electrically dependent signals
        """
        ...
    
    def resolve_order(self, signal_ids: list[str]) -> list[str]:
        """
        Topological sort of signals so dependencies are evaluated first.
        """
        ...
```

### Key Logic — Signal Dependency Inference

Since PIM packages don't include explicit `depends_on` on signals, VF-2 must infer dependencies:

```python
def _infer_signal_deps(sig_reg: SignalRegistry, obj_reg: ObjectRegistry, 
                       process_flow: dict[str, list[str]]) -> dict[str, list[str]]:
    """
    Infer signal dependencies from signal types + topology.
    
    Rules:
    1. measurement signals with parent object that has a status signal
       → depends on that status signal
       e.g., FT_101.FLOW depends on PMP101A.RUN_STATUS
    
    2. feedback signals → depends on associated setpoint signal
    
    3. Signals on downstream objects (via process flow)
       → potential dependency on upstream object output signals
    
    4. Electrical load equipment → depends on feeder status
    """
    ...
```

### `tests/test_topology_engine.py`

```python
class TestTopologyEngine:
    
    def test_build_from_golden(self):
        pkg = load_package(GOLDEN)
        obj_reg = ObjectRegistry(pkg)
        sig_reg = SignalRegistry(pkg)
        engine = TopologyEngine(pkg, obj_reg, sig_reg)
        graph = engine.build()
        assert len(graph.process_flow) > 0
    
    def test_process_flow_graph(self):
        """Motor→Pump edges create correct flow graph."""
        ...
        # VF2-REF-PMP-MTR-101A → VF2-REF-PMP-101A (CONNECTED_TO)
        assert "VF2-REF-PMP-101A" in graph.process_flow.get("VF2-REF-PMP-MTR-101A", [])
    
    def test_topological_sort(self):
        """Signals must be sorted: independent first, dependent last."""
        ...
        engine = TopologyEngine(pkg, obj_reg, sig_reg)
        graph = engine.build()
        order = graph.eval_order
        assert len(order) == sig_reg.signal_count
        # If signal A depends on B, B must appear before A in order
        for sig_id, upstream_ids in graph.signal_deps.items():
            if upstream_ids:
                sig_idx = order.index(sig_id)
                for up_id in upstream_ids:
                    assert order.index(up_id) < sig_idx
    
    def test_get_downstream_objects(self):
        ...
        downstream = engine.get_downstream_objects("VF2-REF-PMP-101A")
        assert isinstance(downstream, list)
    
    def test_boundary_endpoints_identified(self):
        """Topology edges to VF2-UNIT-* or objects not in objects[] → boundary."""
        ...
        assert len(graph.boundary_endpoints) >= 1
    
    def test_empty_electrical_edges(self):
        """Golden fixture has no electrical edges → electrical dict is empty."""
        ...
        assert graph.electrical == {}
    
    def test_signal_deps_measurement_to_status(self):
        """Measurement on pump should have inferred dep on pump status."""
        ...
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `TopologyGraph.process_flow` contains edges from golden fixture |
| AC-2 | `TopologyGraph.eval_order` is a valid topological sort |
| AC-3 | `get_downstream_objects("VF2-REF-PMP-101A")` returns objects downstream |
| AC-4 | `get_affected_signals(...)` returns signal IDs for a given object |
| AC-5 | Boundary endpoints are identified (not in objects[]) |
| AC-6 | Signal dependency DAG is non-empty |
| AC-7 | All tests pass + VF-1 OK |
