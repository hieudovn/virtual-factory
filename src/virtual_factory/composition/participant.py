"""Mechanism-neutral executable participant contract (G4).

The coordinator advances executable scopes through THIS participant surface only
— it never reaches into a participant's domain runtime state. The contract is
deliberately minimal and does NOT imply:

- one engine per scope;
- identical internal ``dt`` / timestep;
- identical scheduler;
- that ``SimulationEngineProtocol.step()`` is the only execution mechanism.

A participant remains structurally addressable by its owning executable scope
and exposes only the lifecycle/exchange surface G4 needs. ``advance_to`` lands
the participant's LOCAL simulation time at the requested coordination boundary
using its own mechanism/cadence (it must not move time backward). Staged
outbound transfers are returned detached; inbound transfers are committed later
through ``commit_transfers``.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from virtual_factory.composition.transfer import BoundaryTransfer
from virtual_factory.workspace.identity import StructuralPath


class ParticipantError(ValueError):
    """Raised when an executable-participant invariant is violated."""


@runtime_checkable
class ExecutableParticipant(Protocol):
    """Mechanism-neutral boundary exchange/lifecycle surface for one scope."""

    @property
    def scope_path(self) -> StructuralPath:
        """The owning executable scope (G1 structural identity)."""
        ...

    @property
    def current_time_s(self) -> float:
        """The participant's current local simulation time."""
        ...

    def advance_to(self, target_time_s: float) -> tuple[BoundaryTransfer, ...]:
        """Advance local time to ``target_time_s`` (never backward) and return
        staged, detached outbound transfers.

        ``target_time_s < current_time_s`` must fail closed (no backward time).
        """
        ...

    def commit_transfers(self, inbound: Sequence[BoundaryTransfer]) -> None:
        """Commit inbound transfers through this participant's declared consumer
        boundary interface. Called only after the whole window validated."""
        ...
