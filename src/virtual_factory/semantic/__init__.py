"""G9 — Semantic Binding vNext (generic, fail-closed, PIM read-only).

A VF Workspace may validate and consume an explicitly pinned external semantic
contract WITHOUT owning or rewriting that semantic truth:

- PIM stays the canonical semantic authority (read-only reference);
- VF local runtime ids remain local;
- a binding is an explicit local -> canonical relationship (never a rename,
  never name-based/heuristic);
- required bindings fail closed (missing pins / hash mismatch / zero-multiple-
  ambiguous targets / unmapped / review_required);
- semantic compatibility and runtime authorization stay separate
  (SH-WTP: ``compatible_with_constraints`` + ``NOT_AUTHORIZED``);
- admission fails before any domain advancement;
- a consumed contract threads ``semantic_contract_version`` /
  ``semantic_contract_sha`` into existing G2 provenance fields (no new authority).
"""

from __future__ import annotations

from virtual_factory.semantic.admission import (
    SemanticAdmissionError,
    SemanticAdmissionGate,
)
from virtual_factory.semantic.binding import (
    BindingMode,
    CompatibilityDecision,
    LocalCanonicalMapping,
    MappingStatus,
    RuntimeAuthorization,
    SemanticBinding,
    SemanticBindingError,
    SemanticSourcePin,
)
from virtual_factory.semantic.loader import (
    binding_from_dict,
    load_binding_artifact,
)
from virtual_factory.semantic.validation import (
    KNOWN_SEMANTIC_ARTIFACTS,
    BindingValidation,
    validate_binding,
)

__all__ = [
    "BindingMode",
    "BindingValidation",
    "CompatibilityDecision",
    "KNOWN_SEMANTIC_ARTIFACTS",
    "LocalCanonicalMapping",
    "MappingStatus",
    "RuntimeAuthorization",
    "SemanticAdmissionError",
    "SemanticAdmissionGate",
    "SemanticBinding",
    "SemanticBindingError",
    "SemanticSourcePin",
    "binding_from_dict",
    "load_binding_artifact",
    "validate_binding",
]
