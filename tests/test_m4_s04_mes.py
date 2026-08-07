"""VF-DM-M4-S04 — MES Adapter Contract tests.

C01: Replaced TIPA-based integration proof with generic_demo.yaml pipeline.
C01: Added MESInput boundary mapping proof.
"""

from virtual_factory.assembly.mes_adapter import (
    MESInput, MESOutput, MESEvent, MESEventType, MESAdapter,
    ProductionOrder, MaterialRelease, OperationCommand, QualityRequirement,
)


class TestMESAdapter:
    def test_mes_input_construction(self):
        inp = MESInput(
            run_id="run-1",
            production_orders=[
                ProductionOrder(order_id="MO-001", product_id="SSO2", quantity=100),
            ],
            material_releases=[
                MaterialRelease(release_id="R1", order_id="MO-001",
                                wip_id="w-1", source_id="sso2-1"),
            ],
        )
        assert inp.run_id == "run-1"
        assert len(inp.production_orders) == 1
        assert inp.material_releases[0].source_id == "sso2-1"

    def test_mes_to_simulation_conversion(self):
        adapter = MESAdapter()
        inp = MESInput(
            run_id="run-x",
            production_orders=[
                ProductionOrder(order_id="MO-001", product_id="SSO2", quantity=50),
            ],
            material_releases=[
                MaterialRelease(release_id="R1", order_id="MO-001",
                                wip_id="w-1", source_id="sso2-1"),
            ],
        )
        result = adapter.mes_to_simulation(inp)
        assert result["run_id"] == "run-x"
        assert len(result["orders"]) == 1

    def test_simulation_to_mes_conversion(self):
        adapter = MESAdapter()
        sim_events = [
            {"event_id": "e1", "event_type": "WIP_CREATED",
             "simulation_time_s": 0.0, "wip_id": "w-1", "target_id": "sso2-1"},
            {"event_id": "e2", "event_type": "PROCESS_START",
             "simulation_time_s": 0.5, "wip_id": "w-1", "target_id": "AP01"},
            {"event_id": "e3", "event_type": "QUALITY_CHECK",
             "simulation_time_s": 3.0, "wip_id": "w-1", "target_id": "qg-1",
             "disposition": "pass"},
            {"event_id": "e4", "event_type": "WIP_COMPLETED",
             "simulation_time_s": 3.5, "wip_id": "w-1", "target_id": "sink-1"},
        ]
        output = adapter.simulation_to_mes("run-x", "completed", sim_events)
        assert output.run_id == "run-x"
        assert output.run_status == "completed"
        assert len(output.events) == 4
        assert output.events[0].event_type == MESEventType.WIP_CREATED
        assert output.events[1].event_type == MESEventType.OPERATION_STARTED
        assert output.events[2].event_type == MESEventType.QUALITY_RESULT
        assert output.events[3].event_type == MESEventType.WIP_COMPLETED

    def test_mes_output_events_have_required_metadata(self):
        adapter = MESAdapter()
        sim_events = [
            {"event_id": "e1", "event_type": "PROCESS_COMPLETE",
             "simulation_time_s": 1.5, "wip_id": "w-1", "target_id": "AP01"},
        ]
        output = adapter.simulation_to_mes("run-1", "running", sim_events)
        ev = output.events[0]
        assert ev.run_id == "run-1"
        assert ev.wip_id == "w-1"
        assert ev.station_id == "AP01"
        assert ev.simulation_time_s == 1.5

    def test_adapter_boundary_no_runtime_exposure(self):
        """Adapter does not import or expose discrete runtime internals."""
        import inspect
        import virtual_factory.assembly.mes_adapter as mod
        source = inspect.getsource(mod)
        assert "DiscreteRunService" not in source
        assert "DiscreteSimulationEngine" not in source
        assert "WipState" not in source
        assert "AssemblyRuntimeState" not in source


class TestGenericPipeline:
    """M4-S04-C01 — Full pipeline from generic_demo.yaml through MES output.

    Proves a future customer workflow can enter via configuration, not code.
    Does NOT use build_tipa_topology().
    """

    def test_generic_demo_yaml_to_mes_output(self):
        from virtual_factory.assembly.definition_io import load_definition_from_yaml
        from virtual_factory.assembly.definition import (
            validate_definition, build_topology_from_definition,
        )
        from virtual_factory.assembly.handlers import (
            make_source_handler, make_buffer_handler,
            make_processor_handler, make_process_complete_handler,
            make_quality_gate_handler, make_sink_handler,
        )
        from virtual_factory.assembly.runtime import AssemblyRuntimeState
        from virtual_factory.assembly.projection import project_assembly
        from virtual_factory.assembly.scene import build_scene, LayoutDefinition, NodeLayout
        from virtual_factory.discrete.run_service import DiscreteRunService
        from virtual_factory.discrete.run_context import RunContext
        from virtual_factory.discrete.events import ScheduledEvent
        from virtual_factory.discrete.handler_registry import HandlerRegistry

        import os

        # 1. Load from YAML
        yaml_path = os.path.join(
            os.path.dirname(__file__), "..", "configs", "plants", "generic_demo.yaml"
        )
        defn = load_definition_from_yaml(yaml_path)
        assert defn is not None

        # 2. Validate
        result = validate_definition(defn)
        assert result.valid, f"Validation errors: {result.errors}"

        # 3. Build topology
        topo = build_topology_from_definition(defn)

        # 4. Wire generic handlers
        state = AssemblyRuntimeState()
        wip_counter = [0]
        qplan = {"wip-0001": []}  # empty → defaults to PASS

        reg = HandlerRegistry()
        reg.register("WIP_CREATED", make_source_handler(state, topo, wip_counter))
        reg.register("WIP_QUEUED", make_buffer_handler(state, topo))
        reg.register("PROCESS_START", make_processor_handler(state, topo))
        reg.register("PROCESS_COMPLETE", make_process_complete_handler(state, topo))
        reg.register("QUALITY_CHECK", make_quality_gate_handler(state, topo, qplan))
        reg.register("WIP_COMPLETED", make_sink_handler(state))

        # 5. Run simulation
        svc = DiscreteRunService()
        svc.create_run(
            RunContext(run_id="generic-pipe", model_id="generic-demo"),
            reg,
            initial_events=[
                ScheduledEvent(
                    event_id="wip-0001-create", simulation_time_s=0,
                    event_type="WIP_CREATED", target_id="source-1",
                ),
            ],
        )
        for _ in range(10):
            try:
                svc.step_once()
            except Exception:
                break  # run completed

        # 6. Project
        proj = project_assembly(svc, state, topo)
        assert proj is not None
        assert len(proj.wips) == 1
        assert proj.wips[0].flow_id == "base"

        # 7. Scene
        layout = LayoutDefinition(
            canvas_width=1200, canvas_height=400,
            nodes=[
                NodeLayout("source-1", 50, 200),
                NodeLayout("buffer-1", 200, 200),
                NodeLayout("station-1", 400, 200),
                NodeLayout("station-2", 600, 200),
                NodeLayout("quality-1", 800, 200),
                NodeLayout("sink-1", 1000, 200),
            ],
        )
        scene = build_scene(proj, layout)
        assert len(scene.nodes) >= 4
        assert len(scene.wips) == 1

        # 8. MES output
        mes_events = [
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "simulation_time_s": ev.simulation_time_s,
                "wip_id": ev.wip_id,
                "target_id": ev.target_id,
                "result": ev.result,
            }
            for ev in proj.recent_events
        ]
        adapter = MESAdapter()
        output = adapter.simulation_to_mes("generic-pipe", proj.run.status, mes_events)
        assert output.run_id == "generic-pipe"
        assert len(output.events) == len(mes_events)
        # At least one WIP_CREATED or OPERATION_STARTED event
        types_found = {ev.event_type for ev in output.events}
        assert MESEventType.WIP_CREATED in types_found or MESEventType.OPERATION_STARTED in types_found


class TestMESInputBoundary:
    """M4-S04-C01 — MESInput / MaterialRelease identifies run, order, source."""

    def test_mes_input_maps_to_simulation_boundary(self):
        """MESInput can identify run, production order, and source release."""
        inp = MESInput(
            run_id="boundary-01",
            production_orders=[
                ProductionOrder(order_id="MO-001", product_id="generic-demo", quantity=50),
            ],
            material_releases=[
                MaterialRelease(release_id="R1", order_id="MO-001",
                                wip_id="wip-0001", source_id="source-1"),
            ],
        )

        # Boundary assertions: MES input carries enough info to match
        # a simulation definition
        assert inp.run_id == "boundary-01"
        assert inp.production_orders[0].product_id == "generic-demo"
        assert inp.material_releases[0].source_id == "source-1"

        # Convert to simulation dict (current contract — does NOT claim
        # to produce a SimulationDefinition)
        adapter = MESAdapter()
        sim_cfg = adapter.mes_to_simulation(inp)
        assert sim_cfg["run_id"] == "boundary-01"
        assert "generic-demo" not in sim_cfg  # product_id not mapped yet (future Odoo)
        assert len(sim_cfg["releases"]) == 1
        assert sim_cfg["releases"][0]["wip_id"] == "wip-0001"
        assert sim_cfg["releases"][0]["source"] == "source-1"

    def test_mes_input_multiple_orders_and_releases(self):
        """Multiple production orders and releases are preserved."""
        inp = MESInput(
            run_id="multi-01",
            production_orders=[
                ProductionOrder(order_id="MO-001", product_id="prod-a", quantity=10),
                ProductionOrder(order_id="MO-002", product_id="prod-b", quantity=20),
            ],
            material_releases=[
                MaterialRelease(release_id="R1", order_id="MO-001",
                                wip_id="wip-0001", source_id="src-1"),
                MaterialRelease(release_id="R2", order_id="MO-002",
                                wip_id="wip-0002", source_id="src-2"),
            ],
        )
        assert len(inp.production_orders) == 2
        assert len(inp.material_releases) == 2
        assert inp.material_releases[0].order_id == "MO-001"
        assert inp.material_releases[1].order_id == "MO-002"
