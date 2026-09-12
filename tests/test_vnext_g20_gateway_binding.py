"""VF-vNEXT-G20 — Generic Gateway / Workstation Observation Binding tests.

Proves (Issue #71 required): N scopes bind to one gateway; one scope may bind
to multiple gateways (no one-gateway-per-scope invariant); scope/runtime truth
is unchanged by gateway observation; messages preserve source scope identity and
independent/idempotent identity; duplicate/invalid bindings fail closed;
deterministic serialization independent of declaration order; gateway identity
does not impersonate PIM/Scope identity; existing ASSY MES bridge + G19/G18/G14/
G15 behavior remains unchanged.
"""

from __future__ import annotations

import pytest

from virtual_factory.integration.binding import (
    GATEWAY_BINDING_SCHEMA,
    GatewayBindingError,
    GatewayBindingTable,
    GatewayScopeBinding,
    GatewayWorkstation,
    build_assy_gateway_binding,
    collect_executable_scope_paths,
)
from virtual_factory.observation import (
    ObservationEnvelope,
    ObservationType,
    make_idempotency_key,
)


def _gw(gateway_id, kind="gateway"):
    return GatewayWorkstation(gateway_id=gateway_id, kind=kind)


def _binding(binding_id, gateway_id, scope_path, domain="assy"):
    return GatewayScopeBinding(
        binding_id=binding_id,
        gateway_id=gateway_id,
        scope_path=scope_path,
        domain=domain,
    )


ASSY_SCOPES = frozenset(
    f"TIPA/ASSY/ASSY-SL{i:02d}" for i in range(1, 7)
)


class TestFanIn:
    def test_six_scopes_bind_to_one_gateway(self):
        table = build_assy_gateway_binding()
        assert table.gateway_ids == ("ASSY-GW-01",)
        assert table.binding_count == 6
        scopes = table.scopes_for_gateway("ASSY-GW-01")
        assert len(scopes) == 6
        assert set(scopes) == ASSY_SCOPES


class TestFanOut:
    def test_one_scope_may_bind_to_multiple_gateways(self):
        table = GatewayBindingTable(
            table_id="t",
            version="1",
            gateways=(_gw("GW-A"), _gw("GW-B")),
            bindings=(
                _binding("b1", "GW-A", "TIPA/ASSY/ASSY-SL01"),
                _binding("b2", "GW-B", "TIPA/ASSY/ASSY-SL01"),
            ),
            known_scope_paths=frozenset({"TIPA/ASSY/ASSY-SL01"}),
        )
        assert table.gateways_for_scope("TIPA/ASSY/ASSY-SL01") == ("GW-A", "GW-B")


class TestRuntimeTruthUnchanged:
    def test_assy_workspace_scope_paths_unchanged_by_binding(self):
        from virtual_factory.federation.tipa_workspace import (
            SUB_LINE_IDS,
            sub_line_path,
        )
        expected = {sub_line_path(sid).as_string() for sid in SUB_LINE_IDS}
        assert expected == ASSY_SCOPES
        table = build_assy_gateway_binding()
        assert set(table.known_scope_paths) == expected

    def test_binding_is_read_only_declaration(self):
        table = build_assy_gateway_binding()
        # Frozen dataclass: no mutation methods; serialization is deterministic.
        assert isinstance(table, GatewayBindingTable)
        s1 = table.serialize()
        s2 = table.serialize()
        assert s1 == s2

    def test_collect_executable_scope_paths_matches_fixture(self):
        from virtual_factory.federation.tipa_workspace import build_tipa_workspace
        paths = collect_executable_scope_paths(build_tipa_workspace())
        assert paths == ASSY_SCOPES


class TestMessageProvenance:
    def test_envelope_provenance_preserved_through_resolution(self):
        envelope = ObservationEnvelope(
            observation_id="obs-1",
            idempotency_key=make_idempotency_key(
                "run-1", "evt-1", "point-1"
            ),
            observation_type=ObservationType.EVENT,
            run_id="run-1",
            model_id="model-1",
            simulation_time_s=120.0,
            source_domain="assy",
            source_path="TIPA/ASSY/ASSY-SL01",
        )
        table = build_assy_gateway_binding()
        gateways = table.gateways_for_scope(envelope.source_path)
        assert gateways == ("ASSY-GW-01",)
        # The envelope itself is untouched by binding resolution.
        assert envelope.source_domain == "assy"
        assert envelope.source_path == "TIPA/ASSY/ASSY-SL01"
        assert envelope.run_id == "run-1"
        assert envelope.simulation_time_s == 120.0

    def test_messages_are_independently_identifiable_and_idempotent(self):
        k1 = make_idempotency_key("run-1", "evt-1", "point-1")
        k2 = make_idempotency_key("run-1", "evt-2", "point-1")
        assert k1 != k2
        # Deterministic idempotency: same inputs -> same key.
        assert make_idempotency_key("run-1", "evt-1", "point-1") == k1


class TestFailClosed:
    def test_unknown_scope_fails_closed(self):
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable(
                table_id="t", version="1",
                gateways=(_gw("GW-A"),),
                bindings=(_binding("b1", "GW-A", "TIPA/ASSY/UNKNOWN"),),
                known_scope_paths=frozenset({"TIPA/ASSY/ASSY-SL01"}),
            )

    def test_unknown_gateway_fails_closed(self):
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable(
                table_id="t", version="1",
                gateways=(_gw("GW-A"),),
                bindings=(_binding("b1", "GW-B", "TIPA/ASSY/ASSY-SL01"),),
                known_scope_paths=frozenset({"TIPA/ASSY/ASSY-SL01"}),
            )

    def test_duplicate_binding_id_fails_closed(self):
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable(
                table_id="t", version="1",
                gateways=(_gw("GW-A"),),
                bindings=(
                    _binding("b1", "GW-A", "TIPA/ASSY/ASSY-SL01"),
                    _binding("b1", "GW-A", "TIPA/ASSY/ASSY-SL02"),
                ),
                known_scope_paths=ASSY_SCOPES,
            )

    def test_duplicate_logical_binding_fails_closed(self):
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable(
                table_id="t", version="1",
                gateways=(_gw("GW-A"),),
                bindings=(
                    _binding("b1", "GW-A", "TIPA/ASSY/ASSY-SL01"),
                    _binding("b2", "GW-A", "TIPA/ASSY/ASSY-SL01"),
                ),
                known_scope_paths=ASSY_SCOPES,
            )

    def test_duplicate_gateway_id_fails_closed(self):
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable(
                table_id="t", version="1",
                gateways=(_gw("GW-A"), _gw("GW-A")),
                bindings=(),
                known_scope_paths=ASSY_SCOPES,
            )


class TestGatewayIdentity:
    def test_gateway_id_must_not_impersonate_scope_path(self):
        with pytest.raises(GatewayBindingError):
            GatewayWorkstation(gateway_id="TIPA/ASSY/ASSY-SL01")

    def test_gateway_id_must_not_impersonate_pim_id(self):
        for bad in ("PROC-SHW-X", "UNIT-SHW-Y", "REL-SHW-F01", "SIG-Z"):
            with pytest.raises(GatewayBindingError):
                GatewayWorkstation(gateway_id=bad)

    def test_valid_gateway_id_is_distinct_from_scope_and_pim(self):
        gw = GatewayWorkstation(gateway_id="ASSY-GW-01", kind="workstation")
        assert gw.gateway_id == "ASSY-GW-01"
        assert gw.kind == "workstation"
        # Not a structural path, not a PIM prefix.
        assert "/" not in gw.gateway_id
        assert not gw.gateway_id.startswith(("PROC-", "UNIT-", "REL-", "SIG-"))


class TestDeterminism:
    def test_serialization_independent_of_declaration_order(self):
        a = GatewayBindingTable(
            table_id="t", version="1",
            gateways=(_gw("GW-B"), _gw("GW-A")),
            bindings=(
                _binding("b2", "GW-A", "TIPA/ASSY/ASSY-SL02"),
                _binding("b1", "GW-A", "TIPA/ASSY/ASSY-SL01"),
            ),
            known_scope_paths=ASSY_SCOPES,
        )
        b = GatewayBindingTable(
            table_id="t", version="1",
            gateways=(_gw("GW-A"), _gw("GW-B")),
            bindings=(
                _binding("b1", "GW-A", "TIPA/ASSY/ASSY-SL01"),
                _binding("b2", "GW-A", "TIPA/ASSY/ASSY-SL02"),
            ),
            known_scope_paths=ASSY_SCOPES,
        )
        assert a.serialize() == b.serialize()
        assert a.gateway_ids == b.gateway_ids == ("GW-A", "GW-B")

    def test_round_trip_serialization(self):
        table = build_assy_gateway_binding()
        restored = GatewayBindingTable.from_dict(
            table.serialize(), known_scope_paths=table.known_scope_paths,
        )
        assert restored.serialize() == table.serialize()
        assert restored.serialize()["schema"] == GATEWAY_BINDING_SCHEMA

    def test_from_dict_wrong_schema_fails_closed(self):
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable.from_dict({"schema": "wrong"})


class TestFromDictAuthority:
    """G20-C01: serialized known_scope_paths is inspection metadata only;
    reconstruction authority must come from the caller / actual Workspace."""

    def test_tampered_scope_list_does_not_authorize_unknown_scope(self):
        table = build_assy_gateway_binding()
        data = table.serialize()
        # Tamper the serialized inspection metadata to claim an arbitrary scope.
        data["known_scope_paths"] = ["TIPA/ASSY/FAKE"]
        # The tampered field is ignored: reconstruction against an authoritative
        # set that lacks the bound scopes fails closed.
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable.from_dict(
                data, known_scope_paths=frozenset({"TIPA/ASSY/OTHER"}),
            )
        # And a correct authoritative set reconstructs fine, ignoring FAKE.
        restored = GatewayBindingTable.from_dict(
            data, known_scope_paths=ASSY_SCOPES,
        )
        assert set(restored.known_scope_paths) == ASSY_SCOPES

    def test_reconstruction_requires_authoritative_scope_set(self):
        data = build_assy_gateway_binding().serialize()
        # Bindings present but no authoritative set -> fail closed.
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable.from_dict(data)
        # Wrong authoritative set -> fail closed.
        with pytest.raises(GatewayBindingError):
            GatewayBindingTable.from_dict(
                data, known_scope_paths=frozenset({"TIPA/ASSY/OTHER"}),
            )

    def test_deterministic_trusted_round_trip(self):
        table = build_assy_gateway_binding()
        restored = GatewayBindingTable.from_dict(
            table.serialize(), known_scope_paths=table.known_scope_paths,
        )
        assert restored.serialize() == table.serialize()
        assert restored.binding_count == 6


class TestGatewayTopologyNotExecutionOrContainment:
    def test_no_execution_order_or_containment_field(self):
        data = build_assy_gateway_binding().serialize()
        assert "execution_order" not in data
        assert "containment" not in data
        for b in data["bindings"]:
            assert "order" not in b
            assert "parent" not in b


class TestG19G18G14G15Unchanged:
    def test_frozen_constants_unchanged(self):
        from virtual_factory.shwtp import SHWTP_FEDERATION_COUPLING_POLICY
        from virtual_factory.federation.generic import (
            GENERIC_FEDERATION_COUPLING_POLICY,
        )
        assert SHWTP_FEDERATION_COUPLING_POLICY == "explicit_lagged"
        assert GENERIC_FEDERATION_COUPLING_POLICY == "explicit_lagged"

    def test_g14a_projection_unchanged(self):
        from virtual_factory.shwtp import build_shwtp_f01_projection
        proj = build_shwtp_f01_projection()
        assert len(proj.ports) == 2
        assert len(proj.graph.bindings) == 1

    def test_g18_overlay_unchanged(self):
        from virtual_factory.shwtp.overlay import build_shwtp_t108_dist_p108_overlay
        overlay = build_shwtp_t108_dist_p108_overlay()
        assert overlay.edge_count == 1
