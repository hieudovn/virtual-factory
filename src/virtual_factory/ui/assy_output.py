"""VF-vNEXT-R3 — canonical same-session Observation / MES output projection.

READ-ONLY downstream projection of the ONE canonical TIPA ``RuntimeSession``
accepted in R1/R2:

    WorkspaceMonitor
      -> ONE TIPA RuntimeSession
      -> AssyExecutionBridge
      -> TipaAssyFederation
      -> exactly 6 AssyLineRuntime truths
      -> READ-ONLY observation/output projection (this module)
           -> ObservationService / ObservationRouter
           -> MESProjection / ProjectedMessage
           -> in-memory/demo gateway evidence

Invariants (R3):
- No output path constructs, owns, advances, resets or forks simulation truth.
  This adapter never creates a ``RuntimeSession``, ``TipaAssyFederation`` or
  ``DemoController``; it consumes the exact live session/federation from the
  R2 ``CanonicalAssyExperience`` seam.
- Polling is downstream only: it may read runtime truth and emit
  observations/messages, but a poll that changes canonical simulation truth
  raises ``OutputMutationError`` (hard guard).
- Canonical parent-session identity (workspace / canonical run id / pinned
  scenario / pinned profile) supersedes the legacy sub-line-local synthetic run
  generation in emitted facts.  The legacy ``ASSY-SLxx:R<n>`` key is retained
  only as a subordinate compatibility/source key.
- A reset of the SAME canonical run id is scoped by an explicit projection
  epoch (projection metadata only) so post-reset facts never collide with
  pre-reset delivered facts.  G22 reset semantics are untouched.
- Fresh canonical run ids (new attempt / replay) get a fresh output namespace:
  no checkpoint carry-over between attempts.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from virtual_factory.assembly.assy_mes_bridge import (
    CONTRACT_VERSION,
    AssyMesBridge,
    build_assy_mes_pipeline,
)
from virtual_factory.assembly.observation_bridge import (
    AssyObservationBridge,
    build_assy_observation_pipeline,
)
from virtual_factory.ui.assy_experience import (
    CANONICAL_TIPA_WORKSPACE,
    CanonicalAssyExperience,
    SessionNotStarted,
)

#: Authority statement carried by every R3 output payload.
PROJECTION_AUTHORITY = "canonical_tipa_runtime_session"
#: Provenance of every projected fact: simulation/synthetic, never site truth.
PROJECTION_PROVENANCE = "simulation_synthetic"
#: Output surfaces re-enabled by R3 (previously R2-deferred).
OUTPUT_SURFACES = ("observations", "mes_messages", "mes_trace")


class CanonicalOutputError(RuntimeError):
    """R3 output projection refused the request (fail closed, never legacy)."""


class OutputMutationError(CanonicalOutputError):
    """A read-only output call changed canonical simulation truth."""


class CanonicalAssyOutput:
    """Read-only observation/MES projection over ONE canonical TIPA session."""

    def __init__(self, experience: CanonicalAssyExperience) -> None:
        self._experience = experience
        self._observations: Optional[AssyObservationBridge] = None
        self._mes: Optional[AssyMesBridge] = None
        self._federation: Any = None
        self._namespace_run_id: str = ""
        #: Last projection epoch bound into the output bridges. R3-C01: it is
        #: READ from the canonical session reset generation, never inferred.
        self._epoch: Optional[int] = None
        self._epoch_changes: int = 0
        self._last_snapshot: Optional[dict[str, Any]] = None
        self._last_poll: dict[str, int] = {
            "observations_delivered": 0,
            "mes_delivered": 0,
        }

    # ── Canonical seams (never construct) ──

    @property
    def experience(self) -> CanonicalAssyExperience:
        return self._experience

    @property
    def session(self):
        """The ONE canonical TIPA RuntimeSession (same object as /workspaces)."""
        return self._experience.session

    def sub_line_ids(self) -> tuple[str, ...]:
        return self._experience.sub_line_ids()

    # ── Identity binding ──

    # ── Canonical reset generation (R3-C01) ──

    def _session_reset_generation(self) -> int:
        """Authoritative canonical reset generation of the current run.

        The projection epoch is READ from the canonical ``RuntimeSession``
        (incremented exactly when the session's own ``reset()`` succeeds), so
        output correctness never depends on polling timing.  A session without
        the lifecycle seam fails closed rather than falling back to inference.
        """
        value = getattr(self.session, "reset_generation", None)
        if value is None:
            raise CanonicalOutputError(
                "the canonical session exposes no reset_generation; R3-C01 "
                "requires the authoritative canonical lifecycle seam"
            )
        return int(value)

    def _sync_projection_epoch(self) -> bool:
        """Adopt the canonical reset generation as the projection epoch.

        Returns True when the epoch changed since the previous observation.
        A same-run reset advances the generation (collision-free new epoch); a
        fresh canonical run (new attempt / replay) restarts it at 1 and is
        re-bound by ``_ensure_bridges`` together with the fresh namespace.
        """
        current = self._session_reset_generation()
        if self._epoch is None:
            self._epoch = current
            return False
        if current == self._epoch:
            return False
        previous = self._epoch
        self._epoch = current
        if current > previous:
            self._epoch_changes += 1
            if self._mes is not None:
                # explicit projection re-baseline (projection state only)
                self._mes.reset_all()
            return True
        # current < previous → fresh canonical run re-baselined the generation
        return True

    def binding(self) -> dict[str, Any]:
        """Canonical parent-session identity bound into the output bridges."""
        ident = self._experience.session_identity()
        epoch = self._epoch
        if epoch is None:
            epoch = self._session_reset_generation()
        return {
            "canonical_run_id": str(ident.get("run_id") or ""),
            "workspace_id": str(
                ident.get("workspace_id") or CANONICAL_TIPA_WORKSPACE
            ),
            "scenario_id": str(ident.get("scenario_id") or ""),
            "profile_id": str(ident.get("profile_id") or ""),
            "run_state": str(ident.get("run_state") or ""),
            "projection_epoch": epoch,
            "projection_epoch_source": "canonical_session_reset_generation",
            "authority": PROJECTION_AUTHORITY,
            "provenance": PROJECTION_PROVENANCE,
            "site_truth": False,
        }

    def _require_federation(self) -> Any:
        """Resolve the ONE canonical federation (never constructs a second)."""
        try:
            self._federation = self._experience.require_federation()
        except SessionNotStarted as exc:
            raise CanonicalOutputError(str(exc)) from exc
        return self._federation

    def _bind(self) -> dict[str, Any]:
        """Read-only bind: canonical federation + authoritative epoch + bridges."""
        self._require_federation()
        self._sync_projection_epoch()
        return self._ensure_bridges()

    def _ensure_bridges(self) -> dict[str, Any]:
        """Materialize (or re-bind) the output bridges on the canonical session.

        Uses the R2 experience seam: the projection is materialized from the
        session's OWN federation — never a second session/federation/runtime.
        R3-C01: the binding is recomputed AFTER the epoch is (re)resolved, so a
        fresh canonical run can never carry stale prior-run epoch metadata into
        a newly created bridge.
        """
        if self._federation is None:
            self._federation = self._experience.require_federation()
        binding = self.binding()
        run_id = binding["canonical_run_id"]
        if run_id != self._namespace_run_id:
            # new canonical run (fresh attempt / replay) → fresh output namespace
            self._observations = None
            self._mes = None
            self._namespace_run_id = run_id
            self._epoch = self._session_reset_generation()
            self._epoch_changes = 0
            self._last_snapshot = None
            binding = self.binding()  # recompute after the epoch change
        if self._observations is None or self._mes is None:
            self._observations = build_assy_observation_pipeline(
                canonical=binding
            ).bridge
            self._mes = build_assy_mes_pipeline(canonical=binding).bridge
        else:
            self._observations.canonical = binding
            self._mes.canonical = binding
        return binding

    # ── Composition shim (references the SAME six runtimes) ──

    def _canonical_bridge(self):
        """The session's own execution bridge (canonical control/fault owner)."""
        record = self.session.record
        return getattr(record, "bridge", None)

    def fault_state(self) -> dict[str, dict[str, Any]]:
        """READ-ONLY canonical AP05 fault read model.

        The fault lifecycle is owned by the canonical execution bridge; the
        output projection only reads it (never owns simulation fault state).
        """
        bridge = self._canonical_bridge()
        if bridge is None or not hasattr(bridge, "fault_read_model"):
            return {}
        return {
            sub_line_id: dict(row)
            for sub_line_id, row in bridge.fault_read_model().items()
        }

    def _composition(self) -> SimpleNamespace:
        """Duck-typed composition over the canonical six sub-line runtimes.

        Contains references/read access only: no lifecycle, no mutable truth.
        ``faults`` carries the canonical fault read model (R4) so the output
        bridges derive issue/downtime/OEE from canonical truth.
        """
        federation = self._federation
        step_count = int(getattr(self.session.record, "step_count", 0) or 0)
        return SimpleNamespace(
            contexts=dict(federation.sub_lines),
            demo_step_number=step_count,
            faults=self.fault_state(),
        )

    # ── Read-only guard ──

    def _truth_snapshot(self) -> dict[str, Any]:
        record = self.session.record
        lines: dict[str, dict[str, Any]] = {}
        for sub_line_id, entry in self._federation.sub_lines.items():
            runtime = entry.runtime
            lines[sub_line_id] = {
                "simulation_time_s": float(runtime.simulation_time_s),
                "wip_count": len(runtime.wip_ids),
                "genealogy_records": len(runtime.genealogy.all_records()),
            }
        return {
            "run_id": str(getattr(record, "run_id", "")),
            "step_count": int(getattr(record, "step_count", 0) or 0),
            "last_time_s": getattr(record, "last_time_s", None),
            "sub_lines": lines,
        }

    # ── Poll (downstream only) ──

    def poll(self) -> dict[str, int]:
        """Poll both canonical output bridges once. Never mutates truth."""
        self._require_federation()
        before = self._truth_snapshot()
        # R3-C01: authoritative epoch is read AFTER the federation exists and
        # BEFORE any bridge is (re)created, so a fresh-run rebinding can never
        # carry stale prior-run epoch metadata.
        self._sync_projection_epoch()
        self._ensure_bridges()
        composition = self._composition()
        obs_results = self._observations.poll(composition)
        mes_results = self._mes.poll(composition)
        after = self._truth_snapshot()
        if before != after:
            raise OutputMutationError(
                "canonical output poll changed simulation truth: "
                f"{before} -> {after}"
            )
        self._last_snapshot = after
        self._last_poll = {
            "observations_delivered": len(obs_results),
            "mes_delivered": len(mes_results),
        }
        return dict(self._last_poll)

    # ── Canonical envelope ──

    def canonical_envelope(self) -> dict[str, Any]:
        """Canonical run/session identity + projection namespace provenance."""
        ident = self._experience.session_identity()
        source_keys: dict[str, str] = {}
        epochs: dict[str, int] = {}
        if self._observations is not None:
            for sub_line_id in self.sub_line_ids():
                source_keys[sub_line_id] = self._observations.run_id_for(sub_line_id)
                epochs[sub_line_id] = self._epoch
        return {
            "authority": PROJECTION_AUTHORITY,
            "workspace_id": ident.get("workspace_id"),
            "run_id": ident.get("run_id"),
            "scenario_id": ident.get("scenario_id"),
            "profile_id": ident.get("profile_id"),
            "run_state": ident.get("run_state"),
            "step_count": ident.get("step_count"),
            "simulation_time_s": ident.get("simulation_time_s"),
            "provenance": PROJECTION_PROVENANCE,
            "site_truth": False,
            "sub_line_count": len(self.sub_line_ids()),
            "sub_line_ids": list(self.sub_line_ids()),
            "output_surfaces": list(OUTPUT_SURFACES),
            "output_namespace": {
                "canonical_run_id": self._namespace_run_id,
                "namespace_is_canonical_run": (
                    self._namespace_run_id == str(ident.get("run_id") or "")
                ),
                "projection_epoch": self._epoch,
                "session_reset_generation": self._session_reset_generation(),
                "epoch_source": "canonical_session_reset_generation",
                "epoch_changes": self._epoch_changes,
                "epoch_resets": self._epoch_changes,
                "source_run_keys": source_keys,
                "projection_epochs": epochs,
            },
            "poll": dict(self._last_poll),
        }

    def identity(self) -> dict[str, Any]:
        """Canonical output identity (never polls, never steps)."""
        self._bind()
        payload = {"canonical": self.canonical_envelope()}
        payload["legacy_runtime_authority"] = False
        return payload

    # ── Output surfaces (poll + read; never step) ──

    def observations(self) -> dict[str, Any]:
        """Delivered P0 observation facts from the canonical session."""
        counts = self.poll()
        messages = [dict(entry) for entry in self._observations.outbound_trace]
        return {
            "authority": PROJECTION_AUTHORITY,
            "legacy_runtime_authority": False,
            "status": "ok",
            "provenance": PROJECTION_PROVENANCE,
            "canonical": self.canonical_envelope(),
            "observation_points": [
                point.point_id for point in self._observations.service.points
            ],
            "observations": messages,
            "count": len(messages),
            "delivered_this_poll": counts["observations_delivered"],
        }

    def mes_messages(self) -> dict[str, Any]:
        """Delivered MES ProjectedMessages from the canonical session."""
        counts = self.poll()
        messages = [
            {
                "message_key": msg.key,
                "message_type": msg.message_type,
                "schema_name": msg.schema_name,
                "schema_version": msg.schema_version,
                "headers": dict(msg.headers),
                "payload": dict(msg.payload),
            }
            for msg in self._mes.projected_messages
        ]
        return {
            "authority": PROJECTION_AUTHORITY,
            "legacy_runtime_authority": False,
            "status": "ok",
            "provenance": PROJECTION_PROVENANCE,
            "contract_version": CONTRACT_VERSION,
            "canonical": self.canonical_envelope(),
            "mes_messages": messages,
            "count": len(messages),
            "delivered_this_poll": counts["mes_delivered"],
        }

    def oee_summary(self) -> dict[str, Any]:
        """READ-ONLY OEE / final summary from canonical facts (idempotent).

        Reuses the accepted MES OEE projection over the canonical six runtimes;
        downtime comes from the canonical fault lifecycle. It never advances or
        mutates simulation truth and repeated reads are idempotent.
        """
        counts = self.poll()
        if self._mes is None:
            raise CanonicalOutputError(
                "the canonical MES projection is not bound for OEE"
            )
        for sub_line_id, entry in self._federation.sub_lines.items():
            self._mes.emit_oee(sub_line_id, entry.runtime)
        summaries = [
            {
                "message_key": msg.key,
                "message_type": msg.message_type,
                "schema_name": msg.schema_name,
                "payload": dict(msg.payload),
            }
            for msg in self._mes.projected_messages
            if msg.message_type == "mes.oee_summary"
        ]
        faults = self.fault_state()
        sub_lines = []
        for sub_line_id, entry in self._federation.sub_lines.items():
            runtime = entry.runtime
            released = 0
            rejected = 0
            for wip_id in runtime.wip_ids:
                ws = runtime.get_wip(wip_id)
                if ws is not None and ws.lifecycle.value == "released":
                    released += 1
                elif runtime.get_current_quality_status(wip_id).value == "FAILED_FINAL":
                    rejected += 1
            fault = faults.get(sub_line_id, {})
            sub_lines.append(
                {
                    "sub_line_id": sub_line_id,
                    "simulation_time_s": float(runtime.simulation_time_s),
                    "released_wips": released,
                    "rejected_wips": rejected,
                    "fault_state": fault.get("state", "RUNNING"),
                    "downtime_s": float(fault.get("downtime_s") or 0.0)
                    if fault.get("raised_at_s") is not None
                    else 0.0,
                }
            )
        return {
            "authority": PROJECTION_AUTHORITY,
            "legacy_runtime_authority": False,
            "status": "ok",
            "provenance": PROJECTION_PROVENANCE,
            "contract_version": CONTRACT_VERSION,
            "canonical": self.canonical_envelope(),
            "oee_summaries": summaries,
            "count": len(summaries),
            "sub_lines": sub_lines,
            "delivered_this_poll": counts["mes_delivered"],
        }

    def mes_trace(self) -> dict[str, Any]:
        """Ordered MES delivery trace from the canonical session."""
        counts = self.poll()
        trace = [dict(entry) for entry in self._mes.outbound_trace]
        return {
            "authority": PROJECTION_AUTHORITY,
            "legacy_runtime_authority": False,
            "status": "ok",
            "provenance": PROJECTION_PROVENANCE,
            "contract_version": CONTRACT_VERSION,
            "canonical": self.canonical_envelope(),
            "mes_trace": trace,
            "count": len(trace),
            "delivered_this_poll": counts["mes_delivered"],
        }


__all__ = [
    "CanonicalAssyOutput",
    "CanonicalOutputError",
    "OutputMutationError",
    "OUTPUT_SURFACES",
    "PROJECTION_AUTHORITY",
    "PROJECTION_PROVENANCE",
]
