"""VF-DM-M3-S01 — Assembly domain primitives tests.

Covers:
  M3-S01-A — Primitive construction validation
  M3-S01-B — Domain identity — stable deterministic IDs
  M3-S01-C — WIP state representation
  M3-S01-D — Buffer enqueue/dequeue/capacity
  M3-S01-E — Quality disposition pass/fail/rework
  M3-S01-F — Domain neutrality — no TIPA coupling
"""

import pytest
from virtual_factory.assembly import (
    AssemblyPrimitive,
    Source,
    Buffer,
    Processor,
    Router,
    Sink,
    QualityGate,
    WipId,
    WipState,
    WipStatus,
    QualityDisposition,
    PrimitiveType,
)
from virtual_factory.assembly.primitives import (
    AssemblyPrimitiveError,
    BufferError,
)
from virtual_factory.assembly.wip import WipError


# ──────────────────────────────────────────────
# M3-S01-A — Primitive construction
# ──────────────────────────────────────────────

class TestPrimitiveConstruction:
    """M3-S01-A: Each primitive validates required identity/configuration."""

    def test_source_construction(self):
        s = Source(primitive_id="src-01", label="Entry")
        assert s.primitive_id == "src-01"
        assert s.primitive_type == PrimitiveType.SOURCE
        assert s.label == "Entry"

    def test_buffer_construction(self):
        b = Buffer(primitive_id="buf-01", capacity=10, label="Queue")
        assert b.primitive_id == "buf-01"
        assert b.primitive_type == PrimitiveType.BUFFER
        assert b.capacity == 10

    def test_processor_construction(self):
        p = Processor(primitive_id="proc-01", processing_time_s=2.5, label="Drill")
        assert p.primitive_id == "proc-01"
        assert p.primitive_type == PrimitiveType.PROCESSOR
        assert p.processing_time_s == 2.5

    def test_router_construction(self):
        r = Router(primitive_id="rtr-01", label="Split")
        assert r.primitive_id == "rtr-01"
        assert r.primitive_type == PrimitiveType.ROUTER

    def test_sink_construction(self):
        sk = Sink(primitive_id="sink-01", label="Output")
        assert sk.primitive_id == "sink-01"
        assert sk.primitive_type == PrimitiveType.SINK

    def test_quality_gate_construction(self):
        qg = QualityGate(primitive_id="qg-01", label="Inspect")
        assert qg.primitive_id == "qg-01"
        assert qg.primitive_type == PrimitiveType.QUALITY_GATE

    def test_empty_primitive_id_rejected(self):
        with pytest.raises(AssemblyPrimitiveError, match="non-empty"):
            Source(primitive_id="")

    def test_invalid_primitive_type_rejected(self):
        with pytest.raises(AssemblyPrimitiveError):
            AssemblyPrimitive(primitive_id="x", primitive_type="bad")  # type: ignore

    def test_buffer_capacity_must_be_positive(self):
        with pytest.raises(BufferError, match="capacity"):
            Buffer(primitive_id="b", capacity=0)

    def test_processor_negative_time_rejected(self):
        with pytest.raises(AssemblyPrimitiveError, match="processing_time_s"):
            Processor(primitive_id="p", processing_time_s=-1.0)


# ──────────────────────────────────────────────
# M3-S01-B — Domain identity
# ──────────────────────────────────────────────

class TestDomainIdentity:
    """M3-S01-B: Work items and primitives have stable deterministic IDs."""

    def test_wip_id_is_immutable(self):
        wid = WipId(id="wip-001")
        assert wid.id == "wip-001"
        with pytest.raises(Exception):
            wid.id = "other"  # type: ignore

    def test_wip_id_equality(self):
        assert WipId("a") == WipId("a")
        assert WipId("a") != WipId("b")
        # Different objects, same ID = equal
        a1 = WipId("x")
        a2 = WipId("x")
        assert a1 == a2
        assert hash(a1) == hash(a2)

    def test_primitive_identity_is_stable(self):
        s1 = Source(primitive_id="src-x")
        s2 = Source(primitive_id="src-x")
        assert s1.primitive_id == s2.primitive_id

    def test_different_primitive_types_same_id_ok(self):
        """Same ID across different primitive types is valid."""
        buf = Buffer(primitive_id="station-1")
        proc = Processor(primitive_id="station-1")
        assert buf.primitive_id == proc.primitive_id
        assert buf.primitive_type != proc.primitive_type


# ──────────────────────────────────────────────
# M3-S01-C — WIP state
# ──────────────────────────────────────────────

class TestWipState:
    """M3-S01-C: WIP state represents location, lifecycle, progression."""

    def test_initial_state(self):
        wid = WipId("w-1")
        ws = WipState(wip_id=wid)
        assert ws.wip_id == wid
        assert ws.status == WipStatus.CREATED
        assert ws.location == ""
        assert ws.step_count == 0

    def test_advance_transitions_state(self):
        ws = WipState(wip_id=WipId("w-1"))
        ws.advance("buf-01", WipStatus.QUEUED)
        assert ws.location == "buf-01"
        assert ws.status == WipStatus.QUEUED
        assert ws.step_count == 1

    def test_multiple_advances(self):
        ws = WipState(wip_id=WipId("w-1"))
        ws.advance("buf-01", WipStatus.QUEUED)
        ws.advance("proc-01", WipStatus.PROCESSING)
        ws.advance("qg-01", WipStatus.INSPECTING)
        assert ws.location == "qg-01"
        assert ws.status == WipStatus.INSPECTING
        assert ws.step_count == 3

    def test_cannot_advance_from_completed(self):
        ws = WipState(wip_id=WipId("w-1"))
        ws.advance("sink-01", WipStatus.COMPLETED)
        with pytest.raises(WipError, match="terminal"):
            ws.advance("other", WipStatus.QUEUED)

    def test_full_lifecycle(self):
        """CREATED → QUEUED → PROCESSING → INSPECTING → COMPLETED."""
        ws = WipState(wip_id=WipId("lifecycle-1"))
        assert ws.status == WipStatus.CREATED

        ws.advance("buf", WipStatus.QUEUED)
        ws.advance("proc", WipStatus.PROCESSING)
        ws.advance("qg", WipStatus.INSPECTING)
        ws.advance("sink", WipStatus.COMPLETED)
        assert ws.step_count == 4
        assert ws.status == WipStatus.COMPLETED

    def test_rework_path(self):
        """CREATED → PROCESSING → INSPECTING → REWORK."""
        ws = WipState(wip_id=WipId("rework-1"))
        ws.advance("proc", WipStatus.PROCESSING)
        ws.advance("qg", WipStatus.INSPECTING)
        ws.advance("rework", WipStatus.REWORK)
        assert ws.status == WipStatus.REWORK
        # REWORK is not terminal — can advance again
        ws.advance("proc", WipStatus.PROCESSING)
        assert ws.status == WipStatus.PROCESSING


# ──────────────────────────────────────────────
# M3-S01-D — Buffer semantics
# ──────────────────────────────────────────────

class TestBuffer:
    """M3-S01-D: Buffer enqueue/dequeue/capacity invariants."""

    def test_default_capacity(self):
        b = Buffer(primitive_id="buf")
        assert b.capacity == 256

    def test_custom_capacity(self):
        b = Buffer(primitive_id="buf", capacity=5)
        assert b.capacity == 5

    def test_capacity_must_be_positive(self):
        with pytest.raises(BufferError):
            Buffer(primitive_id="b", capacity=0)
        with pytest.raises(BufferError):
            Buffer(primitive_id="b", capacity=-1)

    def test_buffer_immutable(self):
        b = Buffer(primitive_id="buf", capacity=10)
        with pytest.raises(Exception):
            b.capacity = 20  # type: ignore


# ──────────────────────────────────────────────
# M3-S01-E — Quality disposition
# ──────────────────────────────────────────────

class TestQualityDisposition:
    """M3-S01-E: Generic quality outcomes without TIPA coupling."""

    def test_pass_is_terminal(self):
        assert QualityDisposition.PASS.is_terminal

    def test_scrap_is_terminal(self):
        assert QualityDisposition.SCRAP.is_terminal

    def test_fail_is_not_terminal(self):
        assert not QualityDisposition.FAIL.is_terminal

    def test_rework_is_not_terminal(self):
        assert not QualityDisposition.REWORK.is_terminal

    def test_rework_requires_rework(self):
        assert QualityDisposition.REWORK.requires_rework

    def test_pass_does_not_require_rework(self):
        assert not QualityDisposition.PASS.requires_rework

    def test_all_dispositions_distinct(self):
        values = set(QualityDisposition)
        assert len(values) == 4
        assert QualityDisposition.PASS in values
        assert QualityDisposition.FAIL in values
        assert QualityDisposition.REWORK in values
        assert QualityDisposition.SCRAP in values


# ──────────────────────────────────────────────
# M3-S01-F — Domain neutrality
# ──────────────────────────────────────────────

class TestDomainNeutrality:
    """M3-S01-F: Primitives instantiable with generic IDs, no TIPA coupling."""

    def test_generic_factory_flow_ids(self):
        """Primitives use generic IDs, not AP01-AP06."""
        primitives = [
            Source(primitive_id="inbound"),
            Buffer(primitive_id="staging", capacity=50),
            Processor(primitive_id="workstation-1", processing_time_s=3.0),
            Router(primitive_id="dispatcher"),
            QualityGate(primitive_id="qc-check"),
            Sink(primitive_id="outbound"),
        ]
        ids = {p.primitive_id for p in primitives}
        assert "AP01" not in ids
        assert "AP02" not in ids
        assert "TIPA" not in ids

    def test_wip_ids_are_generic(self):
        wids = [WipId(f"part-{i:04d}") for i in range(5)]
        assert len(wids) == 5
        assert all(isinstance(w, WipId) for w in wids)

    def test_no_tipa_names_in_any_enum(self):
        """No TIPA-specific names in any assembly enum."""
        for status in WipStatus:
            assert "TIPA" not in status.value
            assert "AP0" not in status.value

        for disp in QualityDisposition:
            assert "TIPA" not in disp.value
            assert "AP0" not in disp.value

        for pt in PrimitiveType:
            assert "TIPA" not in pt.value
            assert "AP0" not in pt.value


# ──────────────────────────────────────────────
# M3-S01-G — Assembly module import integrity
# ──────────────────────────────────────────────

class TestPackageIntegrity:
    """M3-S01-G: Package structure, no M2 coupling."""

    def test_package_exports_all_symbols(self):
        from virtual_factory.assembly import __all__
        # M3 symbols
        expected_m3 = {
            "AssemblyPrimitive", "Source", "Buffer", "Processor",
            "Router", "Sink", "QualityGate", "PrimitiveType",
            "WipId", "WipState", "WipStatus", "QualityDisposition",
        }
        # Verify all M3 symbols are present
        assert expected_m3 <= set(__all__), \
            f"Missing M3 symbols: {expected_m3 - set(__all__)}"
        assert "AssyLineRuntime" in __all__, "M6-S02 AssyLineRuntime missing"
        assert "ConveyorLine" in __all__, "M6-S02 ConveyorLine missing"

    def test_assembly_does_not_import_discrete(self):
        """Assembly package must not import from discrete runtime."""
        import ast, inspect
        import virtual_factory.assembly.primitives as pmod
        import virtual_factory.assembly.wip as wmod
        import virtual_factory.assembly.quality as qmod

        for mod in (pmod, wmod, qmod):
            source = inspect.getsource(mod)
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module_name = (
                        node.module if isinstance(node, ast.ImportFrom)
                        else node.names[0].name
                    )
                    assert "discrete" not in (module_name or ""), \
                        f"{mod.__name__} imports discrete: {module_name}"
