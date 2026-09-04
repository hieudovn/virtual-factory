"""Build publishable industrial telemetry frames from runtime state.

``build_publishable_frame`` is the legacy, backward-compatible seam: it returns a
plain ``list[SignalValue]`` with NO provenance envelope (legacy callers keep
working; no provenance is fabricated for them).

``build_provenanced_frame`` is the additive G2 seam: it returns the same
policy-filtered signal values wrapped in an immutable :class:`ProvenancedFrame`
carrying a ``ProvenanceV2`` envelope. Domain ``SignalValue`` truth semantics are
unchanged — provenance is carried beside the frame, never merged into it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from virtual_factory.core.runtime_state import RuntimeState
from virtual_factory.core.schema import PlantConfig, SignalConfig
from virtual_factory.provenance.envelope import ProvenanceV2
from virtual_factory.telemetry.output_policy import OutputPolicy
from virtual_factory.telemetry.signal_value import SignalValue


def build_publishable_frame(
    config: PlantConfig,
    state: RuntimeState,
    policy: OutputPolicy,
    timestamp_s: float,
) -> list[SignalValue]:
    """Return policy-allowed signal values for external publication (legacy seam)."""
    frame: list[SignalValue] = []
    for signal_name, signal_config in config.signals.items():
        if not policy.can_publish(signal_config):
            continue
        current_value = state.get_signal_value(signal_name)
        if current_value is None:
            continue
        frame.append(_coerce_signal_value(signal_name, current_value, signal_config, timestamp_s))
    return frame


def _coerce_signal_value(
    name: str,
    current_value: object,
    signal_config: SignalConfig,
    timestamp_s: float,
) -> SignalValue:
    if isinstance(current_value, SignalValue):
        return SignalValue(
            name=name,
            value=current_value.value,
            unit=current_value.unit or signal_config.unit,
            category=signal_config.category,
            quality=current_value.quality,
            timestamp_s=current_value.timestamp_s,
            source=current_value.source or signal_config.source,
        )
    return SignalValue(
        name=name,
        value=current_value,
        unit=signal_config.unit,
        category=signal_config.category,
        quality="GOOD",
        timestamp_s=timestamp_s,
        source=signal_config.source,
    )


@dataclass(frozen=True, slots=True)
class ProvenancedFrame:
    """A policy-filtered telemetry frame plus its immutable provenance envelope.

    ``signals`` preserves ``SignalValue`` truth semantics unchanged; provenance
    is additive and lives beside the signals (never inside them).
    """

    signals: tuple[SignalValue, ...]
    provenance: ProvenanceV2

    def signal_values(self) -> list[SignalValue]:
        """Return the signal values as a plain list (legacy interop)."""
        return list(self.signals)

    def to_records(self) -> list[dict[str, Any]]:
        """Flatten each signal record plus the provenance envelope (additive).

        Signal fields are preserved verbatim; provenance fields are added as a
        separate per-record provenance section (never overwriting signal fields,
        and never fabricating a PIM canonical id).
        """
        prov = self.provenance.to_dict()
        records: list[dict[str, Any]] = []
        for signal in self.signals:
            record = {
                "name": signal.name,
                "value": signal.value,
                "unit": signal.unit,
                "category": signal.category,
                "quality": signal.quality,
                "timestamp_s": signal.timestamp_s,
                "source": signal.source,
                "provenance": prov,
            }
            records.append(record)
        return records

    def to_dict(self) -> dict[str, Any]:
        """Deterministic serialization of the whole frame."""
        return {
            "provenance": self.provenance.to_dict(),
            "signals": [
                {
                    "name": s.name,
                    "value": s.value,
                    "unit": s.unit,
                    "category": s.category,
                    "quality": s.quality,
                    "timestamp_s": s.timestamp_s,
                    "source": s.source,
                }
                for s in self.signals
            ],
        }


def build_provenanced_frame(
    config: PlantConfig,
    state: RuntimeState,
    policy: OutputPolicy,
    timestamp_s: float,
    provenance: ProvenanceV2,
) -> ProvenancedFrame:
    """Build the policy-filtered frame wrapped in a provenance envelope (additive).

    Uses the exact same policy filtering and signal coercion as
    ``build_publishable_frame``, so output-policy behavior is unchanged; the only
    difference is the immutable provenance wrapper.
    """
    frame = build_publishable_frame(config, state, policy, timestamp_s)
    return ProvenancedFrame(signals=tuple(frame), provenance=provenance)

