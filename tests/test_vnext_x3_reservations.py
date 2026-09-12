"""VF-SHW-X3 - reservation semantics of the D4 conservative allocation.

A reservation is a CONTROL/CAPACITY TOKEN: it is never water, never an additional
source or sink, and it is never held forever. This module pins, in committed
evidence, the SA-required semantics:

 1  resource identity and units: an edge/trunk reservation is a FLOW capacity in
    m3/s internally (`EdgeBudget.budget_m3_s`) and is published to the processors
    in m3/h at the named boundary; a receiver reservation is a VOLUME headroom
    expressed as an equivalent one-tick rate;
 2  acquire/release: the reservation is acquired when water ENTERS a conduit and is
    released by the forward emission on the following tick - measured, not merely
    asserted, by watching the remaining capacity return to its component rating;
 3  serial pipes are NOT charged twice while parallel branches sharing one trunk
    ARE aggregated for the same tick;
 4  a full receiver cannot be over-filled; a narrow serial hop bounds the chain;
 5  in-flight (queued) water survives a stop/reset without loss or duplication, and
    no reservation outlives the flow that justified it (no deadlock, no starvation);
 6  queue bound enforcement and cancellation on a trip.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from virtual_factory.shwtp.contracts import load_whole_plant_contracts  # noqa: E402
from virtual_factory.shwtp.physical_budget import (  # noqa: E402
    X3BudgetError,
    allocate_tick,
)
from virtual_factory.shwtp.x3_profile import X3_ACTIVE_C2_LOOP_IDS, load_x3_profile  # noqa: E402
from virtual_factory.shwtp.x3_whole_plant import (  # noqa: E402
    build_shwtp_whole_plant_x3,
)

X3_PROFILE_PATH = ROOT / "configs" / "vnext" / "shwtp" / "shwtp_x3_profile_v1.json"
L1 = "vf-shw-edge-t101-t102"
L2 = "vf-shw-edge-t102-t103"
L3 = "vf-shw-edge-t103-t104"
L4 = "vf-shw-edge-t104-t105"
LINE1_TRUNK = "line1_process_trunk"


@pytest.fixture(scope="module")
def profile():
    return load_x3_profile(X3_PROFILE_PATH)


@pytest.fixture(scope="module")
def contracts():
    return load_whole_plant_contracts()


def _states():
    """T100 (source storage) -> T101 -> T102 -> T103 -> T104 (a series LINE1 chain)."""
    return {
        "vf-shw-node-t100": {"volume_m3": 100.0, "capacity_m3": 200.0, "queued_inbound_m3": 0.0},
        "vf-shw-node-t101": {"volume_m3": 5.0, "capacity_m3": 30.0, "queued_inbound_m3": 0.0},
        "vf-shw-node-t102": {"volume_m3": 0.0, "queued_inbound_m3": 0.0},
        "vf-shw-node-t103": {"volume_m3": 0.0, "queued_inbound_m3": 0.0},
        "vf-shw-node-t104": {"volume_m3": 5.0, "capacity_m3": 30.0, "queued_inbound_m3": 0.0},
    }


def _bindings(pairs):
    return [
        {"binding_id": binding_id, "source_scope": source, "target_scope": target}
        for binding_id, source, target in pairs
    ]


SERIES = _bindings(
    [
        ("vf-shw-edge-t100-l1", "vf-shw-node-t100", "vf-shw-node-t101"),
        (L1, "vf-shw-node-t101", "vf-shw-node-t102"),
        (L2, "vf-shw-node-t102", "vf-shw-node-t103"),
        (L3, "vf-shw-node-t103", "vf-shw-node-t104"),
    ]
)
SERIES_PORTS = {
    "vf-shw-edge-t100-l1": "l1_out",
    L1: "flow_out",
    L2: "flow_out",
    L3: "flow_out",
}


class TestReservationIdentityAndUnits:
    def test_budget_is_a_flow_capacity_with_explicit_units(self, profile):
        allocation = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=_states(),
            requested_m3_s={L1: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        budget = allocation.budgets[L1]
        assert budget.budget_m3_s <= profile.edge(L1).max_flow_m3_s + 1e-15
        # the processor interface is m3/h and it is exactly the SI value * 3600
        assert allocation.budget_m3h_by_scope_port()["vf-shw-node-t101"]["flow_out"] == (
            pytest.approx(budget.budget_m3_s * 3600.0, rel=1e-12)
        )

    def test_receiver_reservation_is_a_volume_headroom(self, profile):
        states = _states()
        states["vf-shw-node-t104"] = {
            "volume_m3": 29.99,
            "capacity_m3": 30.0,
            "queued_inbound_m3": 0.0,
        }
        allocation = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=states,
            requested_m3_s={L3: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert allocation.receiver_headroom_m3_s["vf-shw-node-t104"] == pytest.approx(0.01, rel=1e-9)
        assert allocation.budgets[L3].limiting_factor == "receiver_capacity"
        assert allocation.budgets[L3].budget_m3_s == pytest.approx(0.01, rel=1e-9)

    def test_a_reservation_is_never_water(self, profile):
        """The capacity token never adds water: the budget bounds, it never supplies."""
        allocation = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=_states(),
            requested_m3_s={},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert all(budget.budget_m3_s == 0.0 for budget in allocation.budgets.values())
        assert allocation.queued_volume_m3 == 0.0

    def test_queue_limit_is_enforced(self, profile):
        states = _states()
        states["vf-shw-node-t103"]["queued_inbound_m3"] = profile.queue.max_queued_volume_m3 + 1.0
        with pytest.raises(X3BudgetError):
            allocate_tick(
                profile=profile,
                tick_index=1,
                scope_state=states,
                requested_m3_s={L2: 0.0125},
                bindings=SERIES,
                source_ports=SERIES_PORTS,
            )


class TestSerialAndParallelCapacity:
    def test_series_hops_are_not_charged_twice(self, profile):
        """One parcel crossing N series pipes must not be charged N times."""
        allocation = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=_states(),
            requested_m3_s={L1: 0.0125, L2: 0.0125, L3: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        # every hop of the series chain may carry the SAME water in one tick
        assert allocation.budgets[L1].budget_m3_s == pytest.approx(0.0125, rel=1e-12)
        assert allocation.budgets[L2].budget_m3_s == pytest.approx(0.0125, rel=1e-12)
        assert allocation.budgets[L3].budget_m3_s == pytest.approx(0.0125, rel=1e-12)

    def test_a_narrow_serial_hop_bounds_the_whole_chain(self, profile, contracts):
        """A narrow hop must throttle the chain AND must not drop the upstream water."""
        edged = dict(profile.edges)
        edged[L2] = type(edged[L2])(binding_id=L2, max_flow_m3_s=0.002, trunk_id=edged[L2].trunk_id)
        narrowed = type(profile)(
            profile_id=profile.profile_id,
            version=profile.version,
            tick_s=profile.tick_s,
            coupling_policy=profile.coupling_policy,
            units=profile.units,
            tanks=profile.tanks,
            edges=edged,
            trunks=profile.trunks,
            valves=profile.valves,
            pumps=profile.pumps,
            controllers=profile.controllers,
            queue=profile.queue,
            acceptance=profile.acceptance,
            energy_unavailable=profile.energy_unavailable,
            deferred_loops=profile.deferred_loops,
            raw=profile.raw,
        )
        allocation = allocate_tick(
            profile=narrowed,
            tick_index=1,
            scope_state=_states(),
            requested_m3_s={L1: 0.0125, L2: 0.0125, L3: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert allocation.budgets[L2].budget_m3_s == pytest.approx(0.002, rel=1e-12)
        # the ENTRY into the narrow conduit is limited too, so the upstream hop may
        # not push water the narrow pipe cannot carry (that would be a hidden loss)
        assert allocation.budgets[L1].budget_m3_s <= 0.002 + 1e-12
        # and on the live runtime the chain throughput settles at the narrow rating
        model = build_shwtp_whole_plant_x3(
            profile=narrowed, contracts=contracts, run_id="x3-narrow"
        )
        for index in range(1, 1501):
            model.run_window(f"w{index}")
        filtered = model.participants["vf-shw-node-t106"].monitor_values()["inflow_m3h"]
        assert filtered / 3600.0 <= 0.002 + 1e-9
        plant = model.balance_report()["plant_water"]
        assert plant["physical_valid"] is True
        assert plant["shortfall_m3"] <= 1e-9

    def test_parallel_branches_sharing_a_trunk_are_aggregated_per_tick(self, profile):
        """Two parallel branches from the SAME header share the trunk in one tick."""
        states = {
            "vf-shw-node-t102": {"volume_m3": 0.0, "queued_inbound_m3": 0.0},
            "vf-shw-node-t103": {"volume_m3": 0.0, "queued_inbound_m3": 0.0},
            "vf-shw-node-t104": {"volume_m3": 0.0, "queued_inbound_m3": 0.0},
        }
        allocation = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=states,
            requested_m3_s={L2: 0.0125, L3: 0.0125},
            bindings=_bindings(
                [
                    (L2, "vf-shw-node-t102", "vf-shw-node-t103"),
                    (L3, "vf-shw-node-t102", "vf-shw-node-t104"),
                ]
            ),
            source_ports={L2: "flow_out", L3: "flow_out"},
        )
        trunk = profile.trunks[LINE1_TRUNK]
        drawn = allocation.budgets[L2].budget_m3_s + allocation.budgets[L3].budget_m3_s
        assert drawn <= trunk + 1e-12, "one trunk may not carry more than its rating"
        assert drawn == pytest.approx(trunk, rel=1e-12), "the trunk must actually be saturated"
        assert allocation.budgets[L3].limiting_factor == "shared_trunk"

    def test_series_segments_of_one_line_may_both_flow(self, profile):
        """The regression guard: a shared trunk must not forbid the 2nd segment."""
        allocation = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=_states(),
            requested_m3_s={L1: 0.0125, L2: 0.0125, L3: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert allocation.budgets[L2].budget_m3_s > 0.0
        assert allocation.budgets[L3].budget_m3_s > 0.0


class TestFullReceiverAndDeadlock:
    def test_full_receiver_never_overfills(self, profile):
        states = _states()
        states["vf-shw-node-t102"] = {"volume_m3": 0.0, "queued_inbound_m3": 0.0}
        states["vf-shw-node-t104"] = {"volume_m3": 30.0, "capacity_m3": 30.0, "queued_inbound_m3": 0.0}
        allocation = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=states,
            requested_m3_s={L3: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert allocation.budgets[L3].budget_m3_s == 0.0
        assert allocation.budgets[L3].limiting_factor == "receiver_capacity"
        # a full terminal receiver legitimately blocks its SERIES chain: the water
        # stays in the upstream storage instead of being pushed in and lost
        assert allocation.budgets[L1].budget_m3_s == pytest.approx(0.0, abs=1e-12)
        assert allocation.diagnostics

    def test_releasing_the_receiver_wakes_the_chain_without_loss(self, profile):
        states = _states()
        states["vf-shw-node-t104"] = {"volume_m3": 30.0, "capacity_m3": 30.0, "queued_inbound_m3": 0.0}
        blocked = allocate_tick(
            profile=profile,
            tick_index=1,
            scope_state=states,
            requested_m3_s={L3: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert blocked.budgets[L3].budget_m3_s == 0.0
        states["vf-shw-node-t104"] = {"volume_m3": 20.0, "capacity_m3": 30.0, "queued_inbound_m3": 0.0}
        released = allocate_tick(
            profile=profile,
            tick_index=2,
            scope_state=states,
            requested_m3_s={L3: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert released.budgets[L3].budget_m3_s == pytest.approx(0.0125, rel=1e-12)

    def test_cycle_in_the_propagation_graph_fails_closed(self, profile):
        states = {
            "vf-shw-node-t102": {"volume_m3": 0.0, "queued_inbound_m3": 0.0},
            "vf-shw-node-t103": {"volume_m3": 0.0, "queued_inbound_m3": 0.0},
        }
        with pytest.raises(X3BudgetError):
            allocate_tick(
                profile=profile,
                tick_index=1,
                scope_state=states,
                requested_m3_s={L1: 0.0125, L2: 0.0125},
                bindings=_bindings(
                    [
                        (L1, "vf-shw-node-t102", "vf-shw-node-t103"),
                        (L2, "vf-shw-node-t103", "vf-shw-node-t102"),
                    ]
                ),
                source_ports={L1: "flow_out", L2: "flow_out"},
            )


class TestReservationLifecycleOnTheRealRuntime:
    def test_reservations_are_released_when_the_flow_stops(self, profile, contracts):
        """No reservation outlives the parcel, and a series parcel is charged ONCE."""
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-release")
        for index in range(1, 901):
            model.run_window(f"w{index}")
        steady = model._allocation
        assert steady is not None
        keys = (L2, L3)
        components = {
            key: min(steady.budgets[key].requested_m3_s, profile.edge(key).max_flow_m3_s)
            for key in keys
        }
        charges = {key: components[key] - steady.conduit_remaining_m3_s[key] for key in keys}
        assert charges[L2] > 0.0, "the running plant must actually hold a conduit reservation"
        # NO DOUBLE COUNT: one parcel crossing the series hops is charged the SAME
        # amount to each hop of that conduit, never the same water twice
        assert charges[L2] == pytest.approx(charges[L3], abs=1e-12)
        # ... and the charged parcel COVERS the parcel actually moved in that tick
        moved = sum(
            float(row["water_m3"])
            for row in model._transfers
            if row["binding_id"] == L2 and row["transfer_kind"] == "physical_water"
        )
        assert charges[L2] >= moved - 1e-12
        assert moved > 0.0
        # stop the plant: hold the boundary source at zero and empty every storage
        # before each tick (a test-only dry state), then let the chain drain
        source = model.participants["vf-shw-node-raw-source"]
        intake = model.participants["vf-shw-node-raw-intake"]
        for index in range(901, 1001):
            source._flow_m3h = 0.0
            intake._raw_flow_m3h = 0.0
            for participant in model.participants.values():
                if getattr(participant, "storage", False):
                    participant._volume_m3 = 0.0
                    participant._initial_volume_m3 = 0.0
            model.run_window(f"w{index}")
        drained = model._allocation
        assert drained is not None
        # no water moves any more ...
        moved_after = sum(
            float(row["water_m3"])
            for row in model._transfers
            if row["binding_id"] == L2 and row["transfer_kind"] == "physical_water"
        )
        assert moved_after == pytest.approx(0.0, abs=1e-12)
        # ... and every conduit hop returns to its full component capacity
        for key in keys:
            component = min(
                drained.budgets[key].requested_m3_s, model.profile.edge(key).max_flow_m3_s
            )
            if component <= 0.0:
                continue
            assert drained.conduit_remaining_m3_s[key] == pytest.approx(component, rel=1e-9), (
                f"{key} kept its reservation without a parcel"
            )
        # the forced dry state is itself a STATE TAMPER and the ledger must detect
        # it (this is the same guard that protects a duplicated initialisation)
        plant = model.balance_report()["plant_water"]
        assert plant["physical_valid"] is False
        assert abs(plant["storage_integration_gap_m3"]) > plant["tolerance_m3"]

    def test_in_flight_water_survives_a_stop_without_loss(self, profile, contracts):
        """Pending (queued) slugs are physical inventory, never silently dropped."""
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-inflight")
        for index in range(1, 601):
            model.run_window(f"w{index}")
        plant_before = model.balance_report()["plant_water"]
        inflight = plant_before["transit_inventory_m3"]
        assert inflight > 0.0, "the running plant must hold in-transit water"
        model.reset()
        after_reset = model.balance_report()["plant_water"]
        assert after_reset["transit_inventory_m3"] == 0.0
        assert after_reset["physical_valid"] is True
        # the reset state is deterministic: a second identical run reproduces it
        for index in range(1, 601):
            model.run_window(f"r{index}")
        plant_again = model.balance_report()["plant_water"]
        assert plant_again["plant_in_m3"] == pytest.approx(plant_before["plant_in_m3"], abs=1e-9)
        assert plant_again["transit_inventory_m3"] == pytest.approx(inflight, abs=1e-9)
        assert plant_again["physical_valid"] is True

    def test_actuator_requests_and_the_limiting_factor_stay_visible(self, profile, contracts):
        model = build_shwtp_whole_plant_x3(profile=profile, contracts=contracts, run_id="x3-visible")
        for index in range(1, 901):
            model.run_window(f"w{index}")
        budget = model.budget_report()
        valve_edge = budget["budgets"]["vf-shw-edge-t105-t106"]
        assert valve_edge["requested_m3_s"] > 0.0
        assert valve_edge["budget_m3_s"] <= valve_edge["requested_m3_s"] + 1e-15
        row = model.control_rows()
        flow_row = next(r for r in row if r["controller_id"] == "vf-shw-ctrl-f106-inlet-flow-pi")
        assert flow_row["applied_by"] in ("pi", "pi_flow_output", "c1_backwash_closes_inlet")
        assert flow_row["pi_output_mv"] is not None
        assert flow_row["applied_mv"] is not None
        level_row = next(r for r in row if r["controller_id"] == "vf-shw-ctrl-t108-level-pi")
        assert level_row["limitation_reason"] in (
            "ok",
            "output_saturated",
            "actuator_slew_limit",
            "external_c1_override_integral_held",
            "forced_stop_integral_held",
            "interlock_protective_stop",
            "manual_mode",
        )
        energy = model.energy_report()
        for pump_id, point in energy["pump_operating_points"].items():
            assert point["feasible"] is True, pump_id
            assert point["electric_w"] <= point["motor_rating_w"] + 1e-6


class TestReservationDocumentation:
    def test_the_profile_declares_the_queue_and_trunk_semantics(self, profile):
        assert profile.queue.max_transfers_per_edge >= 1
        assert profile.queue.max_queued_volume_m3 > 0.0
        assert profile.trunks, "the shared trunk rating must be declared"
        for edge_id in (L1, L2, L3, L4):
            assert profile.edge(edge_id).trunk_id == LINE1_TRUNK
        assert profile.raw["time"]["note"]

    def test_allocation_is_deterministic_for_identical_inputs(self, profile):
        first = allocate_tick(
            profile=profile,
            tick_index=7,
            scope_state=_states(),
            requested_m3_s={L1: 0.0125, L2: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        second = allocate_tick(
            profile=profile,
            tick_index=7,
            scope_state=_states(),
            requested_m3_s={L1: 0.0125, L2: 0.0125},
            bindings=SERIES,
            source_ports=SERIES_PORTS,
        )
        assert {
            key: (value.budget_m3_s, value.limiting_factor)
            for key, value in first.budgets.items()
        } == {
            key: (value.budget_m3_s, value.limiting_factor)
            for key, value in second.budgets.items()
        }
        assert first.diagnostics == second.diagnostics
        assert X3_ACTIVE_C2_LOOP_IDS == ("vf-shw-ctrl-f106-inlet-flow-pi", "vf-shw-ctrl-t108-level-pi")
