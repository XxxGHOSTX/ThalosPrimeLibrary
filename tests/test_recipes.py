"""Tests for thalos_nexus.recipes."""

from __future__ import annotations

import pytest

from thalos_nexus.recipes import (
    CipherIdentificationRecipe,
    DataSignature,
    EncodingChainRecipe,
    PrimeTextRecipe,
    RecipeEngine,
    build_default_recipe_engine,
)
from thalos_nexus.solver_registry import (
    SolverDescriptor,
    SolverInput,
    SolverOutput,
    SolverRegistry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sig(
    *,
    entropy: float = 0.5,
    char_classes: frozenset[str] | None = None,
    likely_cipher: str | None = None,
    encoding_layers: tuple[str, ...] = (),
    prime_index_score: float = 0.0,
    has_whitespace: bool = False,
) -> DataSignature:
    return DataSignature(
        length=100,
        char_classes=char_classes if char_classes is not None else frozenset({"alpha"}),
        has_whitespace=has_whitespace,
        entropy=entropy,
        language_hint=None,
        likely_cipher=likely_cipher,
        encoding_layers=encoding_layers,
        prime_index_score=prime_index_score,
    )


def _entrypoint(inp: SolverInput) -> SolverOutput:
    return SolverOutput(result=inp.raw)


def _desc(name: str, tags: frozenset[str], priority: int = 100) -> SolverDescriptor:
    return SolverDescriptor(
        name=name,
        category="cryptography",
        keywords=frozenset({name}),
        description=f"Test {name}",
        entrypoint=_entrypoint,
        tags=tags,
        priority=priority,
    )


def _registry_with_tools() -> SolverRegistry:
    """Build a registry with one tool per relevant tag category."""
    reg = SolverRegistry()
    reg.register(_desc("cipher_tool", frozenset({"cipher_id", "classical_cipher"})))
    reg.register(_desc("encoding_tool", frozenset({"encoding_chain"})))
    reg.register(_desc("prime_tool", frozenset({"prime_sieve", "babel"})))
    return reg


# ---------------------------------------------------------------------------
# DataSignature immutability
# ---------------------------------------------------------------------------


def test_data_signature_immutable() -> None:
    sig = _sig()
    with pytest.raises(Exception):  # frozen dataclass raises FrozenInstanceError
        sig.length = 999  # type: ignore[misc]


def test_data_signature_fields_accessible() -> None:
    sig = _sig(entropy=0.7, likely_cipher="caesar")
    assert sig.entropy == 0.7
    assert sig.likely_cipher == "caesar"


# ---------------------------------------------------------------------------
# CipherIdentificationRecipe
# ---------------------------------------------------------------------------


def test_cipher_identification_recipe_matches_with_cipher() -> None:
    recipe = CipherIdentificationRecipe()
    sig = _sig(likely_cipher="vigenere")
    assert recipe.matches(sig) is True


def test_cipher_identification_recipe_matches_on_entropy_and_alpha() -> None:
    recipe = CipherIdentificationRecipe()
    # entropy in [0.35, 0.80] AND char_classes subset of {alpha, space, punct}
    sig = _sig(entropy=0.55, char_classes=frozenset({"alpha", "space"}))
    assert recipe.matches(sig) is True


def test_cipher_identification_recipe_no_match_high_entropy_non_alpha() -> None:
    recipe = CipherIdentificationRecipe()
    # high entropy AND has digit class → not a classical cipher
    sig = _sig(entropy=0.95, char_classes=frozenset({"alpha", "digit"}))
    assert recipe.matches(sig) is False


def test_cipher_identification_recipe_no_match_low_entropy() -> None:
    recipe = CipherIdentificationRecipe()
    sig = _sig(entropy=0.10, char_classes=frozenset({"alpha"}), likely_cipher=None)
    assert recipe.matches(sig) is False


def test_cipher_identification_recipe_ranked_tools_returns_tools() -> None:
    recipe = CipherIdentificationRecipe()
    reg = _registry_with_tools()
    sig = _sig(likely_cipher=None)
    tools = recipe.ranked_tools(reg, sig)
    assert any(t.name == "cipher_tool" for t in tools)


def test_cipher_identification_recipe_boosts_by_cipher_name() -> None:
    reg = SolverRegistry()
    reg.register(_desc("caesar_solver", frozenset({"cipher_id", "caesar"}), priority=50))
    reg.register(_desc("general_cipher", frozenset({"cipher_id", "classical_cipher"}), priority=10))

    recipe = CipherIdentificationRecipe()
    sig = _sig(likely_cipher="caesar")
    tools = recipe.ranked_tools(reg, sig)
    # caesar_solver should be boosted to front despite lower priority
    assert tools[0].name == "caesar_solver"


# ---------------------------------------------------------------------------
# EncodingChainRecipe
# ---------------------------------------------------------------------------


def test_encoding_chain_recipe_matches_with_layers() -> None:
    recipe = EncodingChainRecipe()
    sig = _sig(encoding_layers=("base64", "rot13"))
    assert recipe.matches(sig) is True


def test_encoding_chain_recipe_matches_high_entropy() -> None:
    recipe = EncodingChainRecipe()
    sig = _sig(entropy=0.90)
    assert recipe.matches(sig) is True


def test_encoding_chain_recipe_no_match() -> None:
    recipe = EncodingChainRecipe()
    sig = _sig(entropy=0.50, encoding_layers=())
    assert recipe.matches(sig) is False


def test_encoding_chain_recipe_ranked_tools() -> None:
    recipe = EncodingChainRecipe()
    reg = _registry_with_tools()
    sig = _sig(entropy=0.90)
    tools = recipe.ranked_tools(reg, sig)
    assert any(t.name == "encoding_tool" for t in tools)


# ---------------------------------------------------------------------------
# PrimeTextRecipe
# ---------------------------------------------------------------------------


def test_prime_text_recipe_matches_above_threshold() -> None:
    recipe = PrimeTextRecipe()
    sig = _sig(prime_index_score=0.6)
    assert recipe.matches(sig) is True


def test_prime_text_recipe_matches_at_threshold() -> None:
    recipe = PrimeTextRecipe()
    sig = _sig(prime_index_score=0.5)
    assert recipe.matches(sig) is True


def test_prime_text_recipe_no_match_below_threshold() -> None:
    recipe = PrimeTextRecipe()
    sig = _sig(prime_index_score=0.3)
    assert recipe.matches(sig) is False


def test_prime_text_recipe_custom_threshold() -> None:
    recipe = PrimeTextRecipe(score_threshold=0.8)
    assert recipe.matches(_sig(prime_index_score=0.75)) is False
    assert recipe.matches(_sig(prime_index_score=0.85)) is True


def test_prime_text_recipe_ranked_tools() -> None:
    recipe = PrimeTextRecipe()
    reg = _registry_with_tools()
    sig = _sig(prime_index_score=0.7)
    tools = recipe.ranked_tools(reg, sig)
    assert any(t.name == "prime_tool" for t in tools)


# ---------------------------------------------------------------------------
# RecipeEngine
# ---------------------------------------------------------------------------


def test_recipe_engine_plan_deduplicates() -> None:
    """A tool appearing in multiple recipes should only appear once."""
    reg = SolverRegistry()
    shared = _desc("shared_solver", frozenset({"cipher_id", "encoding_chain"}))
    reg.register(shared)

    # Both cipher and encoding recipes will return shared_solver
    engine = RecipeEngine(
        registry=reg,
        recipes=[CipherIdentificationRecipe(), EncodingChainRecipe()],
    )
    # sig matches both recipes
    sig = _sig(entropy=0.60, char_classes=frozenset({"alpha"}), encoding_layers=("base64",))
    result = engine.plan(sig)

    names = [d.name for d in result]
    assert names.count("shared_solver") == 1


def test_recipe_engine_plan_no_match_returns_empty() -> None:
    reg = _registry_with_tools()
    engine = RecipeEngine(
        registry=reg,
        recipes=[PrimeTextRecipe(score_threshold=0.99)],
    )
    sig = _sig(prime_index_score=0.1)
    assert engine.plan(sig) == []


def test_recipe_engine_plan_ordering_preserved() -> None:
    """Tools from earlier recipes come before those from later recipes."""
    reg = SolverRegistry()
    reg.register(_desc("cipher_a", frozenset({"cipher_id"}), priority=50))
    reg.register(_desc("prime_b", frozenset({"prime_sieve", "babel"}), priority=10))

    engine = RecipeEngine(
        registry=reg,
        recipes=[CipherIdentificationRecipe(), PrimeTextRecipe(score_threshold=0.0)],
    )
    sig = _sig(
        entropy=0.55,
        char_classes=frozenset({"alpha"}),
        prime_index_score=0.6,
    )
    result = engine.plan(sig)
    names = [d.name for d in result]
    # cipher_a comes from CipherIdentificationRecipe (first recipe)
    cipher_pos = names.index("cipher_a") if "cipher_a" in names else -1
    prime_pos = names.index("prime_b") if "prime_b" in names else -1
    assert cipher_pos < prime_pos


def test_build_default_recipe_engine() -> None:
    engine = build_default_recipe_engine()
    assert isinstance(engine, RecipeEngine)
