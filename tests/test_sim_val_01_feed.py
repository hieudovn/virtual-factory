"""SIM-VAL-01-C01 — snapshot identity + continuous feed policy tests."""

from virtual_factory.assembly.demo_composition import (
    AssyDemoComposition,
    DemoScenario,
)


CONFIG = "configs/plants/tipa_assy_demo.yaml"


def test_snapshot_carries_selected_sub_line_identity():
    comp = AssyDemoComposition(
        config_path=CONFIG,
        scenario=DemoScenario.HAPPY_PATH,
        selected_sub_line_id="ASSY-SL01",
    )
    comp.initialize()
    snap = comp.snapshot()
    assert snap.sub_line_id == "ASSY-SL01"
    assert snap.production_line_id != ""
    assert snap.plant_id != ""
    assert snap.variant in ("hydraulic", "thermal")


def test_feed_off_finite_starvation():
    comp = AssyDemoComposition(
        config_path=CONFIG,
        scenario=DemoScenario.HAPPY_PATH,
        selected_sub_line_id="ASSY-SL01",
        continuous_feed_enabled=False,
    )
    comp.initialize()
    comp.select_sub_line("ASSY-SL01")
    for _ in range(60):
        comp.step_all()
    snap = comp.snapshot()
    # finite seed (7) → released stops at 7, line empty
    assert snap.production.motors_released <= 7
    assert snap.production.wips_on_line == 0


def test_feed_on_sustained_flow():
    comp = AssyDemoComposition(
        config_path=CONFIG,
        scenario=DemoScenario.HAPPY_PATH,
        selected_sub_line_id="ASSY-SL01",
        continuous_feed_enabled=True,
    )
    comp.initialize()
    comp.select_sub_line("ASSY-SL01")
    for _ in range(60):
        comp.step_all()
    snap = comp.snapshot()
    # continuous feed sustains beyond 10 releases without starving
    assert snap.production.motors_released > 10
    assert snap.production.motors_released <= snap.production.motors_created


def test_feed_mode_preserved_on_reset():
    comp = AssyDemoComposition(
        config_path=CONFIG,
        scenario=DemoScenario.HAPPY_PATH,
        selected_sub_line_id="ASSY-SL01",
        continuous_feed_enabled=False,
    )
    comp.initialize()
    assert comp.continuous_feed_enabled is False
    comp.reset()
    assert comp.continuous_feed_enabled is False


def test_ap04_genealogy_still_correct_with_feed_on():
    comp = AssyDemoComposition(
        config_path=CONFIG,
        scenario=DemoScenario.HAPPY_PATH,
        selected_sub_line_id="ASSY-SL01",
        continuous_feed_enabled=True,
    )
    comp.initialize()
    comp.select_sub_line("ASSY-SL01")
    for _ in range(20):
        comp.step_all()
    snap = comp.snapshot()
    # every MTR child has exactly [SSO2, RSO2] parents joined at AP04
    for g in snap.genealogy:
        assert g.join_station == "AP04"
        assert len(g.parent_wip_ids) == 2
        assert any(p.startswith("SSO2") for p in g.parent_wip_ids)
        assert any(p.startswith("RSO2") for p in g.parent_wip_ids)
