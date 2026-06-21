"""Registry that loads model-type definitions and builds runtime objects.

Each model type is defined in its own YAML file under
``configs/model_types/``.  The file must contain at minimum:

    id: tank_v1
    category: equipment          # equipment | instrumentation | control | actuation
    python_class: virtual_factory.equipment.tank.Tank

The registry maps ``model_type_id`` → ``python_class`` and can instantiate
objects by calling the class constructor with the matching Pydantic config
object.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_MODEL_TYPES_DIR = Path("configs/model_types")
_CATEGORY_CLASS_MAP = {
    "equipment": "virtual_factory.equipment.base_equipment.BaseEquipment",
    "instrumentation": "virtual_factory.instrumentation.base_sensor.BaseSensor",
    "control": "virtual_factory.control.base_controller.BaseController",
    "actuation": "virtual_factory.actuation.base_actuator.BaseActuator",
}


@dataclass(slots=True)
class ModelRegistry:
    """Loads model-type metadata and maps IDs to Python classes."""

    classes: dict[str, type] = field(default_factory=dict)
    metadata: dict[str, dict[str, Any]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_directory(cls, directory: str | Path = _MODEL_TYPES_DIR) -> "ModelRegistry":
        """Discover all ``.yaml`` files in *directory* and build the registry."""
        registry = cls()
        dir_path = Path(directory)
        for yaml_file in sorted(dir_path.glob("*.yaml")):
            meta = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            if not isinstance(meta, dict):
                continue
            model_id = meta.get("id")
            python_class = meta.get("python_class")
            if not model_id or not python_class:
                continue
            registry.metadata[model_id] = meta
            registry.classes[model_id] = registry._import_class(python_class)
        return registry

    @classmethod
    def from_dicts(cls, *mappings: dict[str, type]) -> "ModelRegistry":
        """Build a minimal registry from one or more ``{id: class}`` dicts.

        Useful for tests that do not need the full YAML directory.
        """
        registry = cls()
        for mapping in mappings:
            for model_id, cls_ in mapping.items():
                registry.classes[model_id] = cls_
                registry.metadata[model_id] = {"id": model_id}
        return registry

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self, model_type: str, config: Any) -> Any:
        """Instantiate a runtime object for the given *model_type*.

        Parameters
        ----------
        model_type : str
            The ``model_type`` field from the plant config item (e.g.
            ``"tank_v1"``).
        config : pydantic.BaseModel
            The corresponding config item (``EquipmentConfig``,
            ``SensorConfig``, …).

        Returns
        -------
        object
            An instance of the Python class registered for *model_type*,
            constructed as ``cls(config)``.

        Raises
        ------
        ValueError
            If *model_type* is not recognised.
        """
        cls_ = self.classes.get(model_type)
        if cls_ is None:
            raise ValueError(
                f"Unsupported model_type: {model_type}. "
                f"Known types: {sorted(self.classes)}"
            )
        return cls_(config)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _import_class(self, dotted_path: str) -> type:
        """Dynamically import a class from a dotted path."""
        module_path, _, class_name = dotted_path.rpartition(".")
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
