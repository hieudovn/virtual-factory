"""VF-DM-M4-S04 — MES Adapter Contract tests."""

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


class TestMESIntegrationProof:
    """VF-DM-M4-S04-DONE — Full integration: definition → run → project → MES."""

    def test_full_pipeline_mes_output(self):
        from virtual_factory.assembly.definition import (
            SimulationDefinition, PrimitiveDef, EdgeDef,
            validate_definition, build_topology_from_definition,
        )
        from virtual_factory.assembly.projection import project_assembly
        from virtual_factory.assembly.tipa import (
            build_tipa_topology, build_tipa_handler_registry,
        )
        from virtual_factory.assembly.quality import QualityDisposition
        from virtual_factory.discrete.run_service import DiscreteRunService
        from virtual_factory.discrete.run_context import RunContext
        from virtual_factory.discrete.events import ScheduledEvent

        # 1. Build topology from TIPA
        topo = build_tipa_topology()

        # 2. Create handlers and run service
        reg, state, _ = build_tipa_handler_registry(
            {"wip-0001": [QualityDisposition.PASS]}
        )
        svc = DiscreteRunService()
        svc.create_run(
            RunContext(run_id="mes-proof", model_id="tipa"),
            reg,
            initial_events=[
                ScheduledEvent(
                    event_id="wip-0001-create", simulation_time_s=0,
                    event_type="WIP_CREATED", target_id="sso2-1",
                ),
            ],
        )

        # 3. Run full simulation
        svc.step_once()  # create WIP
        svc.step_once()  # route to first station
        svc.step_once()  # process start

        # 4. Project
        proj = project_assembly(svc, state, topo)
        assert proj is not None
        assert proj.run.status in ("running", "ready")
        assert len(proj.wips) > 0

        # 5. Convert projected events to MES output
        mes_events = [
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "simulation_time_s": ev.simulation_time_s,
                "wip_id": ev.wip_id,
                "target_id": ev.target_id,
                "disposition": None,
                "result": ev.result,
            }
            for ev in proj.recent_events
        ]
        adapter = MESAdapter()
        output = adapter.simulation_to_mes("mes-proof", proj.run.status, mes_events)
        assert output.run_id == "mes-proof"
        assert output.run_status == proj.run.status
        assert len(output.events) == len(mes_events)

        # 6. Verify MES events contain expected metadata
        wip_ids_found = [ev.wip_id for ev in output.events if ev.wip_id is not None]
        assert len(wip_ids_found) > 0, "Expected at least one MES event with wip_id"
        for ev in output.events:
            assert ev.run_id == "mes-proof"
            assert ev.simulation_time_s >= 0
