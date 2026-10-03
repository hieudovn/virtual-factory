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

__all__ = [
    "BottledWaterFactory",
    "HierarchyNode",
    "load_factory_config",
    "load_hierarchy",
    "project_target_line",
]
