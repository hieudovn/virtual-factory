"""Virtual Factory workspace compositions.

A workspace composition binds an existing Virtual Factory runtime to a factory
workspace. It composes, it does not fork: no new simulation engine, telemetry
framework, scenario engine or historian lives here.
"""

from __future__ import annotations

from virtual_factory.workspaces.bottled_water import (
    BottledWaterFactory,
    HierarchyNode,
    load_factory_config,
    load_hierarchy,
    project_target_line,
)
from virtual_factory.workspaces.plantos_export import (
    PlantosLocalIngestion,
    map_snapshot,
    overview_from_snapshot,
)

__all__ = [
    "BottledWaterFactory",
    "HierarchyNode",
    "PlantosLocalIngestion",
    "load_factory_config",
    "load_hierarchy",
    "map_snapshot",
    "overview_from_snapshot",
    "project_target_line",
]
