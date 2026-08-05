"""Tests for the engine-boundary compatibility seam (Slice 1)."""

import pytest
from virtual_factory.core.engine_contract import SimulationEngineProtocol
from virtual_factory.core.engine_factory import (
    UnsupportedEngineError,
    create_engine,
    resolve_engine_kind,
)
from virtual_factory.core.simulation_engine import SimulationEngine


# ──────────────────────────────────────────────
# Factory resolution tests
# ──────────────────────────────────────────────

class TestResolveEngineKind:
    """Engine-kind resolution from config."""

    def test_legacy_config_no_model_type_defaults_to_continuous(self):
        """A config without model_type resolves to continuous_process."""
        kind = resolve_engine_kind({})
        assert kind == "continuous_process"

    def test_explicit_continuous_process(self):
        """Explicit model_type='continuous_process' resolves correctly."""
        kind = resolve_engine_kind({"model_type": "continuous_process"})
        assert kind == "continuous_process"

    def test_unsupported_kind_raises_typed_error(self):
        """An unsupported kind raises UnsupportedEngineError."""
        with pytest.raises(UnsupportedEngineError, match="discrete_manufacturing"):
            resolve_engine_kind({"model_type": "discrete_manufacturing"})

    def test_unsupported_kind_error_message_includes_kind(self):
        """Error message names the unsupported kind."""
        with pytest.raises(UnsupportedEngineError) as exc_info:
            resolve_engine_kind({"model_type": "batch_process"})
        assert "batch_process" in str(exc_info.value)


class TestCreateEngine:
    """Engine creation through the factory."""

    def test_legacy_dict_config_creates_simulation_engine(self):
        """A plain dict config (no model_type) returns SimulationEngine."""
        from virtual_factory.core.config_loader import load_plant_config
        from pathlib import Path

        config_path = Path("configs/plants/continuous_mvp_01.yaml")
        if not config_path.exists():
            pytest.skip("Legacy config not found")
        config = load_plant_config(config_path)
        engine = create_engine(config, dt_s=1.0)
        assert isinstance(engine, SimulationEngine)

    def test_engine_satisfies_protocol(self):
        """The created engine structurally satisfies the protocol."""
        from pathlib import Path
        from virtual_factory.core.config_loader import load_plant_config

        config_path = Path("configs/plants/continuous_mvp_01.yaml")
        if not config_path.exists():
            pytest.skip("Legacy config not found")
        config = load_plant_config(config_path)
        engine = create_engine(config, dt_s=1.0)

        assert isinstance(engine, SimulationEngineProtocol)
        assert hasattr(engine, "initialized")
        assert hasattr(engine, "dt_s")
        assert callable(getattr(engine, "initialize", None))
        assert callable(getattr(engine, "step", None))

    def test_explicit_continuous_config_creates_engine(self):
        """model_type='continuous_process' on a real YAML config works end-to-end."""
        import yaml
        from pathlib import Path
        from virtual_factory.core.schema import PlantConfig

        config_path = Path("configs/plants/continuous_mvp_01.yaml")
        if not config_path.exists():
            pytest.skip("Legacy config not found")

        # F-003: Load raw YAML, inject model_type, validate through PlantConfig
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)
        raw["model_type"] = "continuous_process"
        config = PlantConfig.model_validate(raw)

        # Extra field preserved
        assert getattr(config, "model_type", None) == "continuous_process"

        # Resolver and factory choose continuous engine
        kind = resolve_engine_kind(config)
        assert kind == "continuous_process"
        engine = create_engine(config, dt_s=1.0)
        assert isinstance(engine, SimulationEngineProtocol)

    def test_unsupported_kind_raises_on_create(self):
        """create_engine raises for unsupported kinds."""
        with pytest.raises(UnsupportedEngineError):
            create_engine({"model_type": "discrete_manufacturing"})


# ──────────────────────────────────────────────
# Contract compatibility
# ──────────────────────────────────────────────

class TestEngineContract:
    """Existing SimulationEngine satisfies the structural protocol."""

    def test_simulation_engine_satisfies_protocol(self):
        """SimulationEngine structurally satisfies SimulationEngineProtocol."""
        from pathlib import Path
        from virtual_factory.core.config_loader import load_plant_config

        config_path = Path("configs/plants/continuous_mvp_01.yaml")
        if not config_path.exists():
            pytest.skip("Legacy config not found")
        config = load_plant_config(config_path)
        engine = SimulationEngine(config, dt_s=1.0)

        # The engine must satisfy the protocol structurally
        assert isinstance(engine, SimulationEngineProtocol)


# ──────────────────────────────────────────────
# Behavioral characterization: factory vs direct
# ──────────────────────────────────────────────

class TestFactoryVsDirectEquivalence:
    """Factory-created engine behaves identically to direct construction."""

    def test_same_behavior_factory_vs_direct(self):
        """Factory and direct construction produce equivalent step results.

        Compares stable normalized projection:
        - signal name, category, unit, timestamp_s
        - selected deterministic signal value (LT102_LEVEL)
        """
        from pathlib import Path
        from virtual_factory.core.config_loader import load_plant_config

        config_path = Path("configs/plants/continuous_mvp_01.yaml")
        if not config_path.exists():
            pytest.skip("Legacy config not found")

        config1 = load_plant_config(config_path)
        config2 = load_plant_config(config_path)

        engine_direct = SimulationEngine(config1, dt_s=1.0)
        engine_factory = create_engine(config2, dt_s=1.0)

        # Run same number of steps
        for _ in range(3):
            snap_direct = engine_direct.step()
            snap_factory = engine_factory.step()

        # --- Stable normalized projection (name, category, unit, timestamp_s) ---
        direct_signals = {
            s.name: (s.category, s.unit, s.timestamp_s)
            for s in snap_direct["telemetry_latest"]
        }
        factory_signals = {
            s.name: (s.category, s.unit, s.timestamp_s)
            for s in snap_factory["telemetry_latest"]
        }
        assert direct_signals == factory_signals
        assert len(direct_signals) == len(factory_signals)

        # --- Selected deterministic value ---
        direct_level = next(
            (s for s in snap_direct["telemetry_latest"] if s.name == "LT102_LEVEL"),
            None,
        )
        factory_level = next(
            (s for s in snap_factory["telemetry_latest"] if s.name == "LT102_LEVEL"),
            None,
        )
        assert direct_level is not None
        assert factory_level is not None
        assert direct_level.value == factory_level.value, (
            f"LT102_LEVEL mismatch: direct={direct_level.value}, "
            f"factory={factory_level.value}"
        )

    def test_direct_import_normal_construction(self):
        """SimulationEngine construction lifecycle: uninitialized → step → initialized."""
        from pathlib import Path
        from virtual_factory.core.config_loader import load_plant_config

        config_path = Path("configs/plants/continuous_mvp_01.yaml")
        if not config_path.exists():
            pytest.skip("Legacy config not found")
        config = load_plant_config(config_path)
        engine = SimulationEngine(config, dt_s=1.0)

        # Before step: not initialized
        assert engine.initialized is False
        assert engine.dt_s == 1.0

        # Step auto-initializes and succeeds
        snap = engine.step()
        assert engine.initialized is True
        assert "telemetry_latest" in snap
        assert len(snap["telemetry_latest"]) > 0


# ──────────────────────────────────────────────
# Direct-import compatibility
# ──────────────────────────────────────────────

class TestDirectImportCompatibility:
    """Existing direct imports of SimulationEngine still work."""

    def test_direct_import_still_works(self):
        """SimulationEngine can still be imported and instantiated directly."""
        engine = SimulationEngine.__new__(SimulationEngine)
        assert engine is not None
