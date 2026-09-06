"""VF-vNEXT-G9 — Semantic Binding vNext tests (Issue #54).

Proves the generic, fail-closed semantic-binding/admission seam:
PIM stays canonical (read-only reference); VF local ids remain local; binding is
an explicit local -> canonical relationship; required bindings fail closed on
missing pins / hash mismatch / name-only / zero-multiple-ambiguous targets /
unmapped / review_required; semantic compatibility and runtime authorization
stay separate (SH-WTP: compatible_with_constraints + NOT_AUTHORIZED); admission
fails before domain advancement; consumed contract version/SHA thread into
provenance; absent binding fabricates nothing; no G10.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from virtual_factory.provenance.adapter import to_provenance_v2
from virtual_factory.runcontrol import (
    RunLifecycleService,
    RunState,
    build_continuous_workspace,
)
from virtual_factory.runcontrol.lifecycle import StepResult
from virtual_factory.semantic import (
    BindingMode,
    CompatibilityDecision,
    LocalCanonicalMapping,
    MappingStatus,
    RuntimeAuthorization,
    SemanticAdmissionError,
    SemanticAdmissionGate,
    SemanticBinding,
    SemanticSourcePin,
    load_binding_artifact,
    validate_binding,
)

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "semantic"
    / "song_hong_wtp_export_v0_1.yaml"
)


class _FakeBridge:
    """Deterministic bridge that records advancement (for zero-advance proof)."""

    def __init__(self) -> None:
        self.advances = 0
        self.current = 0.0

    @property
    def supports_reset(self) -> bool:
        return True

    def natural_next_boundary(self, scope_ids):
        return self.current + 1.0

    def advance(self, target_time_s, scope_ids, window_id) -> StepResult:
        self.advances += 1
        self.current = target_time_s
        return StepResult(
            status="completed",
            target_time_s=target_time_s,
            participants=tuple(scope_ids),
            committed=(),
            failure=None,
        )

    def reset(self, scope_ids) -> None:
        self.current = 0.0


def _service(*, admission=None):
    return RunLifecycleService(
        build_continuous_workspace(), lambda: _FakeBridge(), admission=admission
    )


def _valid_required_binding(**overrides) -> SemanticBinding:
    kwargs = dict(
        mode=BindingMode.REQUIRED,
        source=SemanticSourcePin(
            producer_id="producer-x",
            artifact_id="artifact-y",
            version="v1.2.3",
            artifact_hash="hash-y",
            semantic_identity_sha="sha-y",
            source_model_version="model-y",
        ),
        compatibility=CompatibilityDecision.COMPATIBLE,
        runtime_authorization=RuntimeAuthorization.AUTHORIZED,
        mappings=(
            LocalCanonicalMapping(
                local_id="runtime.sig", canonical_id="PIM.CANON", published=True
            ),
        ),
    )
    kwargs.update(overrides)
    return SemanticBinding(**kwargs)


# ── 1-3. required pins / hash ──────────────────────────────

class TestSourceIdentity:
    def test_valid_required_binding_validates_deterministically(self):
        binding = _valid_required_binding()
        a = validate_binding(binding)
        b = validate_binding(binding)
        assert a.ok is True
        assert a.diagnostics == ()
        assert a.to_dict() == b.to_dict()  # deterministic

    def test_missing_required_pins_fail_closed(self):
        for missing in ("artifact_id", "version", "artifact_hash"):
            kwargs = {
                "producer_id": "producer-x",
                "artifact_id": "artifact-y",
                "version": "v1.2.3",
                "artifact_hash": "hash-y",
            }
            kwargs[missing] = None
            source = SemanticSourcePin(**kwargs)
            binding = _valid_required_binding(source=source)
            result = validate_binding(binding)
            assert result.ok is False
            assert any(missing in d for d in result.diagnostics)

    def test_hash_mismatch_fails_closed(self):
        # SH-WTP pinned artifact/version but a wrong artifact hash.
        binding = SemanticBinding(
            mode=BindingMode.REQUIRED,
            source=SemanticSourcePin(
                producer_id="song-hong-wtp-pim",
                artifact_id="SHW-PIM-VF-EXPORT-v0.1",
                version="v0.1",
                artifact_hash="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
            ),
            compatibility=CompatibilityDecision.COMPATIBLE_WITH_CONSTRAINTS,
            runtime_authorization=RuntimeAuthorization.NOT_AUTHORIZED,
        )
        result = validate_binding(binding)
        assert result.ok is False
        assert any("hash mismatch" in d for d in result.diagnostics)


# ── 4-9. mapping cardinality / status ─────────────────────

class TestMappingCardinality:
    def test_name_only_mapping_rejected(self):
        binding = _valid_required_binding(
            mappings=(
                LocalCanonicalMapping(
                    local_id="runtime.sig",
                    canonical_id="runtime.sig",  # name-equal, non-explicit
                    explicit=False,
                    published=True,
                ),
            )
        )
        result = validate_binding(binding)
        assert result.ok is False
        assert any("name-only" in d for d in result.diagnostics)

    def test_zero_target_fails(self):
        binding = _valid_required_binding(
            mappings=(
                LocalCanonicalMapping(
                    local_id="runtime.sig", canonical_id=None, published=True
                ),
            )
        )
        result = validate_binding(binding)
        assert result.ok is False
        assert any("zero target" in d for d in result.diagnostics)

    def test_multiple_ambiguous_targets_fail(self):
        binding = _valid_required_binding(
            mappings=(
                LocalCanonicalMapping(
                    local_id="runtime.sig", canonical_id="PIM.A", published=True
                ),
                LocalCanonicalMapping(
                    local_id="runtime.sig", canonical_id="PIM.B", published=True
                ),
            )
        )
        result = validate_binding(binding)
        assert result.ok is False
        assert any("ambiguous" in d or "multiple" in d for d in result.diagnostics)

    def test_unmapped_and_review_required_fail(self):
        for status, token in (
            (MappingStatus.UNMAPPED, "unmapped"),
            (MappingStatus.REVIEW_REQUIRED, "review_required"),
        ):
            binding = _valid_required_binding(
                mappings=(
                    LocalCanonicalMapping(
                        local_id="runtime.sig",
                        canonical_id="PIM.CANON",
                        status=status,
                        published=True,
                    ),
                )
            )
            result = validate_binding(binding)
            assert result.ok is False
            assert any(token in d for d in result.diagnostics)

    def test_optional_local_only_allowed_when_non_published_non_canonical(self):
        binding = SemanticBinding(
            mode=BindingMode.OPTIONAL,
            source=SemanticSourcePin(
                producer_id="p", artifact_id="a", version="v", artifact_hash="h"
            ),
            compatibility=CompatibilityDecision.COMPATIBLE,
            runtime_authorization=RuntimeAuthorization.AUTHORIZED,
            mappings=(
                LocalCanonicalMapping(
                    local_id="runtime.sig",
                    canonical_id=None,
                    status=MappingStatus.UNMAPPED,
                    published=False,
                    canonical_claimed=False,
                ),
            ),
        )
        assert validate_binding(binding).ok is True

    def test_optional_claim_without_target_fails(self):
        binding = SemanticBinding(
            mode=BindingMode.OPTIONAL,
            source=SemanticSourcePin(
                producer_id="p", artifact_id="a", version="v", artifact_hash="h"
            ),
            compatibility=CompatibilityDecision.COMPATIBLE,
            runtime_authorization=RuntimeAuthorization.AUTHORIZED,
            mappings=(
                LocalCanonicalMapping(
                    local_id="runtime.sig", canonical_id=None, published=True
                ),
            )
        )
        result = validate_binding(binding)
        assert result.ok is False
        assert any("without target" in d for d in result.diagnostics)


# ── 10-11. identity + authority separation ────────────────

class TestIdentityAndAuthority:
    def test_local_runtime_id_is_not_replaced_by_canonical_id(self):
        binding = _valid_required_binding(
            mappings=(
                LocalCanonicalMapping(
                    local_id="runtime_signal_id",
                    canonical_id="PIM.CANONICAL_SIGNAL_ID",
                    published=True,
                ),
            )
        )
        mapping = binding.mappings[0]
        assert mapping.local_id == "runtime_signal_id"  # unchanged local id
        assert mapping.canonical_id == "PIM.CANONICAL_SIGNAL_ID"  # separate ref
        d = mapping.to_dict()
        assert d["local_id"] == "runtime_signal_id"
        assert d["canonical_id"] == "PIM.CANONICAL_SIGNAL_ID"

    def test_compatibility_and_runtime_authorization_remain_separate(self):
        binding = load_binding_artifact(FIXTURE)
        assert binding.compatibility is CompatibilityDecision.COMPATIBLE_WITH_CONSTRAINTS
        assert binding.runtime_authorization is RuntimeAuthorization.NOT_AUTHORIZED
        # structurally valid (exact pins, no claimed mappings) ...
        assert SemanticAdmissionGate(binding).assess().ok is True
        # ... but NOT authorized to run (compatibility does not imply admission).
        with pytest.raises(SemanticAdmissionError):
            SemanticAdmissionGate(binding).assert_admittable()


# ── 12-15. admission / provenance ─────────────────────────

class TestAdmissionAndProvenance:
    def test_shwtp_not_authorized_cannot_start_or_advance(self):
        gate = SemanticAdmissionGate(load_binding_artifact(FIXTURE))
        bridge = _FakeBridge()
        svc = RunLifecycleService(
            build_continuous_workspace(), lambda: bridge, admission=gate
        )
        rec = svc.create_run("continuous")
        rid = rec.context.run_id
        assert rec.state is RunState.CREATED
        with pytest.raises(SemanticAdmissionError):
            svc.start(rid)
        assert rec.state is RunState.CREATED  # never started
        assert bridge.advances == 0  # no domain advancement
        assert rec.step_count == 0
        # NOT consumed -> no fabricated semantic provenance
        assert rec.semantic_contract_version is None
        assert rec.semantic_contract_sha is None

    def test_admission_failure_causes_zero_domain_advancement(self):
        # Invalid required binding (missing artifact pin) -> start must fail
        # before any state change or bridge advancement.
        invalid = SemanticBinding(
            mode=BindingMode.REQUIRED,
            source=SemanticSourcePin(),  # missing all required pins
            compatibility=CompatibilityDecision.COMPATIBLE,
            runtime_authorization=RuntimeAuthorization.AUTHORIZED,
        )
        bridge = _FakeBridge()
        svc = RunLifecycleService(
            build_continuous_workspace(),
            lambda: bridge,
            admission=SemanticAdmissionGate(invalid),
        )
        rec = svc.create_run("continuous")
        rid = rec.context.run_id
        with pytest.raises(SemanticAdmissionError):
            svc.start(rid)
        assert rec.state is RunState.CREATED
        assert rec.step_count == 0
        assert rec.last_time_s is None
        assert bridge.advances == 0

    def test_consumed_contract_threads_exact_version_and_sha_into_provenance(self):
        binding = _valid_required_binding()  # AUTHORIZED + valid
        svc = _service(admission=SemanticAdmissionGate(binding))
        rec = svc.create_run("continuous")
        svc.start(rec.context.run_id)  # admission consumes contract identity
        assert rec.semantic_contract_version == "v1.2.3"
        assert rec.semantic_contract_sha == "sha-y"
        # RunRecord serialization carries the consumed identity.
        d = rec.to_dict()
        assert d["semantic_contract_version"] == "v1.2.3"
        assert d["semantic_contract_sha"] == "sha-y"
        # Existing G2 provenance envelope carries the same exact values.
        prov = to_provenance_v2(
            rec.context,
            semantic_contract_version=rec.semantic_contract_version,
            semantic_contract_sha=rec.semantic_contract_sha,
        )
        pd = prov.to_dict()
        assert pd["semantic_contract_version"] == "v1.2.3"
        assert pd["semantic_contract_sha"] == "sha-y"

    def test_absent_binding_does_not_fabricate_semantic_provenance(self):
        svc = _service()  # no admission -> no semantic binding consumed
        rec = svc.create_run("continuous")
        svc.start(rec.context.run_id)
        assert rec.semantic_contract_version is None
        assert rec.semantic_contract_sha is None
        assert rec.to_dict()["semantic_contract_version"] is None
        assert rec.to_dict()["semantic_contract_sha"] is None
        prov = to_provenance_v2(rec.context)
        assert prov.semantic_contract_version is None
        assert prov.semantic_contract_sha is None


# ── 18. no G10 implementation ─────────────────────────────

class TestNoG10:
    def test_semantic_package_contains_no_shwtp_runtime(self):
        import virtual_factory.semantic as semantic

        pkg_dir = Path(inspect.getfile(semantic)).parent
        for py_file in sorted(pkg_dir.glob("*.py")):
            text = py_file.read_text(encoding="utf-8")
            for forbidden in ("class SHWTPRuntime", "shwtp_runtime", "def run_shwtp"):
                assert forbidden not in text
