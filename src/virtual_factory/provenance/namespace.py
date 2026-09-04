"""Deterministic output namespace seam (PH00 B2 / B8).

``outputs.namespace`` is a protocol/path-safe routing namespace DERIVED from
authoritative workspace/output inputs. It is a DISTINCT concept from
``workspace_id`` (B2) — it is a deterministic output routing key, never the
workspace identity itself and never a PIM canonical id.

No global mutable registry; no workspace-name special cases.
"""

from __future__ import annotations

import re

# A deterministic, path-safe namespace segment.
_NAMESPACE_RE = re.compile(r"[^A-Za-z0-9_.-]+")

_SEPARATOR = "."


class OutputNamespaceError(ValueError):
    """Raised when an output namespace cannot be derived deterministically."""


def _sanitize(segment: str) -> str:
    """Replace any non-namespace-safe characters with '-' and collapse runs."""
    cleaned = _NAMESPACE_RE.sub("-", segment)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip(".-")
    return cleaned or "default"


def derive_output_namespace(
    workspace_id: str,
    *,
    output_namespace: str | None = None,
    output_namespace_suffix: str | None = None,
) -> str:
    """Derive a deterministic, path-safe output namespace.

    Rules (frozen):
    - ``workspace_id`` must be non-empty;
    - an explicit ``output_namespace`` wins and is sanitized as-is (never renamed);
    - otherwise the namespace is derived from ``workspace_id`` (plus an optional
      suffix) — still a DISTINCT output-routing concept, not the workspace id;
    - the result is deterministic: same inputs -> same namespace; no registry,
      no workspace-name branching.
    """
    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise OutputNamespaceError("workspace_id must be a non-empty str")

    if output_namespace is not None:
        base = output_namespace
    else:
        base = workspace_id
        if output_namespace_suffix:
            base = f"{base}{_SEPARATOR}{output_namespace_suffix}"

    if not isinstance(base, str) or not base.strip():
        raise OutputNamespaceError("output namespace must be a non-empty str")

    # A namespace may itself contain '.' separators (multi-segment); sanitize
    # each segment independently and rejoin deterministically.
    segments = [_sanitize(part) for part in base.split(".")]
    return _SEPARATOR.join(segments)
