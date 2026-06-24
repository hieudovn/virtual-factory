"""Persist user preferences across sessions (last-used config, etc.)."""

import json
from pathlib import Path

STATE_DIR = Path.home() / ".virtual_factory"
STATE_FILE = STATE_DIR / "state.json"

DEFAULT_STATE = {
    "last_config": "configs/plants/continuous_mvp_01.yaml",
    "last_scenario": None,
}


def _ensure_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def load_state() -> dict:
    """Load persisted state, returning defaults if the file doesn't exist."""
    _ensure_dir()
    if not STATE_FILE.exists():
        return dict(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults in case new keys are added later
        merged = dict(DEFAULT_STATE)
        merged.update(data)
        return merged
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_STATE)


def save_state(state: dict) -> None:
    """Persist state dict to disk."""
    _ensure_dir()
    current = load_state()
    current.update(state)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)


def get_last_config() -> str:
    """Return the last-used plant config path."""
    return load_state().get("last_config", DEFAULT_STATE["last_config"])


def set_last_config(config_path: str) -> None:
    """Persist the last-used plant config path."""
    save_state({"last_config": config_path})


def get_last_scenario() -> str | None:
    """Return the last-used scenario path."""
    return load_state().get("last_scenario")


def set_last_scenario(scenario_path: str | None) -> None:
    """Persist the last-used scenario path."""
    save_state({"last_scenario": scenario_path})
