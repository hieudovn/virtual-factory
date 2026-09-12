"""VF-vNEXT-G2 — output namespace seam tests."""

from __future__ import annotations

import pytest

from virtual_factory.provenance import OutputNamespaceError, derive_output_namespace


def test_namespace_is_deterministic() -> None:
    assert derive_output_namespace("W") == derive_output_namespace("W")
    assert derive_output_namespace("W", output_namespace="out.w") == "out.w"


def test_namespace_is_distinct_concept_from_workspace_id() -> None:
    # Derivation from workspace id is a deterministic default, but the result is
    # a separate output-routing concept (and an explicit namespace wins).
    assert derive_output_namespace("My Workspace") != "My Workspace"
    assert derive_output_namespace("W", output_namespace="explicit-ns") == "explicit-ns"


def test_namespace_sanitization_is_path_safe() -> None:
    assert derive_output_namespace("My Workspace!") == "My-Workspace"
    assert derive_output_namespace("A/B/C") == "A-B-C"


def test_namespace_suffix_is_deterministic() -> None:
    assert derive_output_namespace("W", output_namespace_suffix="out") == "W.out"


def test_empty_workspace_fails_closed() -> None:
    with pytest.raises(OutputNamespaceError):
        derive_output_namespace("")
