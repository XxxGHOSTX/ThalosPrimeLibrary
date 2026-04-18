from __future__ import annotations

from thalos_prime.individuation import build_individuation_profile, policy_version


def test_profile_has_expected_keys() -> None:
    profile = build_individuation_profile(
        "deterministic global reliability and policy compliance",
        "safe governance with validation and checkpoint review",
    )
    metadata = profile.as_metadata()

    assert metadata["policy_version"] == "individuation-v1"
    assert 0.0 <= float(metadata["distinctness"]) <= 1.0
    assert 0.0 <= float(metadata["identity_continuity"]) <= 1.0
    assert 0.0 <= float(metadata["contextual_integrity"]) <= 1.0
    assert 0.0 <= float(metadata["collective_coupling"]) <= 1.0
    assert 0.0 <= float(metadata["privacy_singling_risk"]) <= 1.0
    assert 0.0 <= float(metadata["recursive_refinement"]) <= 1.0


def test_policy_version_export() -> None:
    assert policy_version() == "individuation-v1"
