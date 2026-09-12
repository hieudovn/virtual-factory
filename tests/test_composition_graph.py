"""VF-vNEXT-G4 — composition graph tests.

Proves (Issue #49): graph is separate from containment; cycles allowed (no DAG);
deterministic enumeration independent of declaration order; dangling/duplicate/
cross-workspace endpoints fail closed; fan-out deterministic.
"""

from __future__ import annotations

import pytest

from virtual_factory.composition import (
    BoundaryPort,
    CompositionBinding,
    CompositionError,
    CompositionGraph,
    PortCategory,
    PortDirection,
    PortRef,
)
from virtual_factory.workspace import StructuralPath

_W = "W"
_A = StructuralPath(("W", "AREA", "A"))
_B = StructuralPath(("W", "AREA", "B"))
_C = StructuralPath(("W", "AREA", "C"))


def _out(scope, port_id) -> BoundaryPort:
    return BoundaryPort(PortRef(scope, port_id), PortDirection.OUT, PortCategory.MATERIAL)


def _in(scope, port_id) -> BoundaryPort:
    return BoundaryPort(PortRef(scope, port_id), PortDirection.IN, PortCategory.MATERIAL)


def _ports():
    return [
        _out(_A, "out"),
        _in(_A, "in"),
        _out(_B, "out"),
        _in(_B, "in"),
        _out(_C, "out"),
        _in(_C, "in"),
    ]


def _binding(edge_id, src, tgt) -> CompositionBinding:
    return CompositionBinding(edge_id, PortRef(*src), PortRef(*tgt))


def test_deterministic_enumeration_independent_of_declaration_order() -> None:
    b1 = _binding("e1", (_A, "out"), (_B, "in"))
    b2 = _binding("e2", (_B, "out"), (_A, "in"))
    g1 = CompositionGraph(_W, bindings=[b1, b2], ports=_ports())
    g2 = CompositionGraph(_W, bindings=[b2, b1], ports=reversed(_ports()))
    assert [b.as_tuple() for b in g1.bindings] == [b.as_tuple() for b in g2.bindings]


def test_cycles_are_allowed() -> None:
    b1 = _binding("e1", (_A, "out"), (_B, "in"))
    b2 = _binding("e2", (_B, "out"), (_A, "in"))
    graph = CompositionGraph(_W, bindings=[b1, b2], ports=_ports())
    assert len(graph.bindings) == 2  # cycle is not an error


def test_dangling_endpoint_fails_closed() -> None:
    with pytest.raises(CompositionError):
        CompositionGraph(
            _W,
            bindings=[_binding("e1", (_A, "out"), (_B, "missing"))],
            ports=_ports(),
        )


def test_duplicate_edge_id_fails_closed() -> None:
    with pytest.raises(CompositionError):
        CompositionGraph(
            _W,
            bindings=[
                _binding("e1", (_A, "out"), (_B, "in")),
                _binding("e1", (_B, "out"), (_A, "in")),
            ],
            ports=_ports(),
        )


def test_duplicate_logical_binding_fails_closed() -> None:
    with pytest.raises(CompositionError):
        CompositionGraph(
            _W,
            bindings=[
                _binding("e1", (_A, "out"), (_B, "in")),
                _binding("e2", (_A, "out"), (_B, "in")),
            ],
            ports=_ports(),
        )


def test_cross_workspace_binding_fails_closed() -> None:
    foreign = StructuralPath(("W2", "AREA", "X"))
    ports = _ports() + [
        _out(foreign, "out"),
        _in(foreign, "in"),
    ]
    with pytest.raises(CompositionError):
        CompositionGraph(
            _W,
            bindings=[_binding("e1", (_A, "out"), (foreign, "in"))],
            ports=ports,
        )


def test_nodes_are_deterministic() -> None:
    g = CompositionGraph(
        _W,
        bindings=[
            _binding("e2", (_B, "out"), (_A, "in")),
            _binding("e1", (_A, "out"), (_B, "in")),
        ],
        ports=_ports(),
    )
    assert [n.as_string() for n in g.nodes()] == [
        "W/AREA/A#in",
        "W/AREA/A#out",
        "W/AREA/B#in",
        "W/AREA/B#out",
    ]


def test_fan_out_is_deterministic() -> None:
    g = CompositionGraph(
        _W,
        bindings=[
            _binding("e1", (_A, "out"), (_B, "in")),
            _binding("e2", (_A, "out"), (_C, "in")),
        ],
        ports=_ports(),
    )
    outbound = g.outbound(PortRef(_A, "out"))
    assert [b.edge_id for b in outbound] == ["e1", "e2"]


def test_disconnected_nodes_allowed() -> None:
    # A port that participates in no binding is fine.
    g = CompositionGraph(
        _W,
        bindings=[_binding("e1", (_A, "out"), (_B, "in"))],
        ports=_ports(),
    )
    assert g.has_binding(PortRef(_A, "out"), PortRef(_B, "in"))
    assert not g.has_binding(PortRef(_C, "out"), PortRef(_B, "in"))
