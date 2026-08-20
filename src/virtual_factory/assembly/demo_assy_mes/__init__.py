"""TIPA ASSY Customer Demo Scenario v1 (VF-DM-DEMO-ASSY-MES-01).

Deterministic, resettable single-sub-line VF→MES demo built on the existing
M5 observation pipeline and gateways. Contract version ``tipa-assy-demo-v1``.
"""

from virtual_factory.assembly.demo_assy_mes.bridge import (
    DemoPipeline,
    build_demo_pipeline,
    build_observation_points,
    fact_to_reality,
)
from virtual_factory.assembly.demo_assy_mes.model import (
    CONTRACT_VERSION,
    SUB_LINE_ID,
    FactKind,
    DemoFact,
    LineOutDisposition,
    LineState,
    Station,
    STATIONS,
    STATION_IDS,
)
from virtual_factory.assembly.demo_assy_mes.oee import OeeSummary, compute_oee
from virtual_factory.assembly.demo_assy_mes.runner import DemoRunner
from virtual_factory.assembly.demo_assy_mes.scenario import build_scenario_facts

__all__ = [
    "CONTRACT_VERSION",
    "SUB_LINE_ID",
    "FactKind",
    "DemoFact",
    "LineOutDisposition",
    "LineState",
    "Station",
    "STATIONS",
    "STATION_IDS",
    "DemoPipeline",
    "build_demo_pipeline",
    "build_observation_points",
    "fact_to_reality",
    "OeeSummary",
    "compute_oee",
    "DemoRunner",
    "build_scenario_facts",
]
