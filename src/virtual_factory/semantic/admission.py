"""G9 — bounded semantic admission seam for run-control (pre-start/pre-advance).

Keeps semantic compatibility and runtime authorization as SEPARATE decisions:

- ``compatible_with_constraints`` is a review/compatibility fact and never, by
  itself, authorizes execution;
- ``NOT_AUTHORIZED`` always rejects admission (fail closed), so the pinned
  SH-WTP reference export can be validated but never started/advanced.

The gate is a plain callable consumed by ``RunLifecycleService`` as an optional
admission hook. On success it threads the consumed semantic contract identity
(version + semantic identity SHA) onto the run record so provenance can carry it
exactly; on failure it raises before any state change / domain advancement.
"""

from __future__ import annotations

from virtual_factory.runcontrol.lifecycle import RunLifecycleError
from virtual_factory.semantic.binding import RuntimeAuthorization, SemanticBinding
from virtual_factory.semantic.validation import BindingValidation, validate_binding


class SemanticAdmissionError(RunLifecycleError):
    """Raised when a semantic binding cannot admit a run (invalid or NOT_AUTHORIZED)."""


class SemanticAdmissionGate:
    """Admission gate for one pinned SemanticBinding."""

    def __init__(self, binding: SemanticBinding) -> None:
        if not isinstance(binding, SemanticBinding):
            raise TypeError(
                f"binding must be SemanticBinding, got {type(binding).__name__}"
            )
        self._binding = binding

    @property
    def binding(self) -> SemanticBinding:
        return self._binding

    def assess(self) -> BindingValidation:
        """Deterministic structural/mapping validation (no side effects)."""
        return validate_binding(self._binding)

    def assert_admittable(self) -> None:
        """Fail closed if the binding is invalid or NOT runtime-authorized.

        ``compatibility`` is deliberately NOT consulted here: a
        ``compatible_with_constraints`` review decision does not authorize
        execution.
        """
        validation = self.assess()
        if not validation.ok:
            raise SemanticAdmissionError(
                "semantic binding invalid: " + "; ".join(validation.diagnostics)
            )
        if self._binding.runtime_authorization is RuntimeAuthorization.NOT_AUTHORIZED:
            raise SemanticAdmissionError(
                f"semantic runtime authorization NOT_AUTHORIZED for "
                f"{self._binding.source.artifact_id or 'unknown artifact'} "
                f"(compatibility={self._binding.compatibility.value})"
            )

    def consume(self, record) -> None:
        """Admit and thread the consumed semantic contract identity into a record.

        ``record`` is a ``RunRecord`` (mutable lifecycle record); only the
        ``semantic_contract_version`` / ``semantic_contract_sha`` fields are set
        on success — never on failure.
        """
        self.assert_admittable()
        record.semantic_contract_version = self._binding.source.version
        record.semantic_contract_sha = self._binding.source.semantic_identity_sha

    def __call__(self, record) -> None:
        """Admission hook callable: raise on rejection, consume identity on success."""
        self.consume(record)
