"""G9 — deterministic semantic binding validation (fail-closed).

Validates pinned semantic source identity and local->canonical mapping
cardinality/status WITHOUT owning or rewriting PIM truth and WITHOUT conflating
semantic compatibility with runtime authorization.

Frozen rules enforced here (Issue #54 §1–§4):
- required mode: required source pins (producer/artifact/version/hash) must be
  present; a known artifact's exact accepted hash is checked (mismatch fails);
- name-only/heuristic mappings are rejected;
- required mappings must resolve exactly one canonical target: zero target,
  multiple/ambiguous targets, ``unmapped``, ``review_required`` fail closed;
- optional local-only mappings are allowed only when explicitly non-published
  and non-canonical; claiming canonical/published without a target fails.

``KNOWN_SEMANTIC_ARTIFACTS`` is a static, deterministic, offline pin registry
(never a mutable ``main/latest`` lookup). The current SH-WTP export baseline is
registered for hash-mismatch validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from virtual_factory.semantic.binding import (
    BindingMode,
    LocalCanonicalMapping,
    MappingStatus,
    SemanticBinding,
)

# (artifact_id, version) -> (accepted artifact hash, accepted semantic identity SHA).
KNOWN_SEMANTIC_ARTIFACTS: dict[tuple[str, str], tuple[str, str]] = {
    (
        "SHW-PIM-VF-EXPORT-v0.1",
        "v0.1",
    ): (
        "ea3361a4aca9d25927a4a76c792f3af184e1aabb",
        "f23f3c4614f50a1a2e3805f7e887433feb934915",
    ),
}


@dataclass(frozen=True, slots=True)
class BindingValidation:
    """Deterministic validation result + diagnostics (fail-closed)."""

    ok: bool
    diagnostics: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"ok": self.ok, "diagnostics": list(self.diagnostics)}


def validate_binding(binding: SemanticBinding) -> BindingValidation:
    """Validate one semantic binding deterministically (no network, no heuristics)."""
    if not isinstance(binding, SemanticBinding):
        return BindingValidation(False, ("not a SemanticBinding",))

    diags: list[str] = []

    if binding.mode is BindingMode.NONE:
        # No semantic binding claim: nothing to validate.
        return BindingValidation(True)

    # ── source identity pins ───────────────────────────────
    src = binding.source
    if binding.mode is BindingMode.REQUIRED:
        for field_name, label in (
            ("producer_id", "producer_id"),
            ("artifact_id", "artifact_id"),
            ("version", "version"),
            ("artifact_hash", "artifact_hash"),
            ("semantic_identity_sha", "semantic_identity_sha"),
        ):
            if not getattr(src, field_name):
                diags.append(f"required binding missing source pin: {label}")

    # exact accepted pins baseline (mismatch fails closed, offline)
    if src.artifact_id and src.version:
        known = KNOWN_SEMANTIC_ARTIFACTS.get((src.artifact_id, src.version))
        if known is not None:
            accepted_hash, accepted_sha = known
            if src.artifact_hash and src.artifact_hash != accepted_hash:
                diags.append(
                    f"artifact hash mismatch for {src.artifact_id}@{src.version}: "
                    f"supplied {src.artifact_hash!r} != accepted {accepted_hash!r}"
                )
            if src.semantic_identity_sha and src.semantic_identity_sha != accepted_sha:
                diags.append(
                    f"semantic identity SHA mismatch for "
                    f"{src.artifact_id}@{src.version}: supplied "
                    f"{src.semantic_identity_sha!r} != accepted {accepted_sha!r}"
                )

    # ── mapping cardinality / status ───────────────────────
    if binding.mode in (BindingMode.REQUIRED, BindingMode.OPTIONAL):
        seen_local: dict[str, int] = {}
        for mapping in binding.mappings:
            if not isinstance(mapping, LocalCanonicalMapping):
                diags.append("mapping entry is not a LocalCanonicalMapping")
                continue
            seen_local[mapping.local_id] = seen_local.get(mapping.local_id, 0) + 1

            # name-only / heuristic mapping is never allowed to resolve.
            if not mapping.explicit:
                diags.append(f"name-only mapping rejected for local_id {mapping.local_id!r}")

            claims = mapping.published or mapping.canonical_claimed

            if binding.mode is BindingMode.REQUIRED:
                if mapping.status is MappingStatus.UNMAPPED:
                    diags.append(f"required mapping unmapped: {mapping.local_id!r}")
                if mapping.status is MappingStatus.REVIEW_REQUIRED:
                    diags.append(f"required mapping review_required: {mapping.local_id!r}")
                # Frozen rule: every REQUIRED mapping must have exactly one
                # non-empty canonical target, independent of published/
                # canonical_claimed flags.
                if not mapping.canonical_id:
                    diags.append(f"required mapping zero target: {mapping.local_id!r}")
            else:  # OPTIONAL
                if claims and not mapping.canonical_id:
                    diags.append(
                        f"optional mapping claims canonical/published without target: "
                        f"{mapping.local_id!r}"
                    )
                if not claims and mapping.status is MappingStatus.UNMAPPED:
                    # local-only, explicitly non-published and non-canonical: allowed.
                    pass

        for local_id, count in seen_local.items():
            if count > 1:
                diags.append(
                    f"multiple/ambiguous targets for local_id {local_id!r} "
                    f"({count} mappings)"
                )

    return BindingValidation(ok=len(diags) == 0, diagnostics=tuple(diags))
