"""Tests for thalos_nexus.solver_registry."""

from __future__ import annotations

import pytest

from thalos_nexus.solver_registry import (
    SolverDescriptor,
    SolverInput,
    SolverNotFoundError,
    SolverOutput,
    SolverRegistry,
    get_global_solver_registry,
)


def _make_entrypoint(label: str = "ok"):
    """Return a simple entrypoint callable for test descriptors."""

    def entrypoint(inp: SolverInput) -> SolverOutput:
        return SolverOutput(result=f"{label}:{inp.raw}", metadata={})

    return entrypoint


def _make_descriptor(
    name: str,
    category: str = "math",
    keywords: frozenset[str] | None = None,
    tags: frozenset[str] | None = None,
    priority: int = 100,
) -> SolverDescriptor:
    """Build a minimal ``SolverDescriptor`` for testing."""
    return SolverDescriptor(
        name=name,
        category=category,  # type: ignore[arg-type]
        keywords=keywords if keywords is not None else frozenset({name.lower()}),
        description=f"Test solver {name}",
        entrypoint=_make_entrypoint(name),
        tags=tags if tags is not None else frozenset(),
        priority=priority,
    )


# ---------------------------------------------------------------------------
# register / get
# ---------------------------------------------------------------------------


def test_register_and_get() -> None:
    reg = SolverRegistry()
    d = _make_descriptor("alpha_solver")
    reg.register(d)
    assert reg.get("alpha_solver") is d


def test_register_overwrites() -> None:
    reg = SolverRegistry()
    d1 = _make_descriptor("solver_x")
    d2 = _make_descriptor("solver_x", category="cryptography")
    reg.register(d1)
    reg.register(d2)
    result = reg.get("solver_x")
    assert result.category == "cryptography"


# ---------------------------------------------------------------------------
# unregister
# ---------------------------------------------------------------------------


def test_unregister_known() -> None:
    reg = SolverRegistry()
    reg.register(_make_descriptor("to_remove"))
    reg.unregister("to_remove")
    with pytest.raises(SolverNotFoundError):
        reg.get("to_remove")


def test_unregister_unknown_raises() -> None:
    reg = SolverRegistry()
    with pytest.raises(SolverNotFoundError):
        reg.unregister("ghost")


# ---------------------------------------------------------------------------
# get errors
# ---------------------------------------------------------------------------


def test_get_unknown_raises() -> None:
    reg = SolverRegistry()
    with pytest.raises(SolverNotFoundError):
        reg.get("does_not_exist")


def test_solver_not_found_is_key_error() -> None:
    reg = SolverRegistry()
    with pytest.raises(KeyError):
        reg.get("nope")


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_list_all_sorted_by_name() -> None:
    reg = SolverRegistry()
    for name in ["zebra", "alpha", "mango"]:
        reg.register(_make_descriptor(name))
    names = [d.name for d in reg.list_all()]
    assert names == sorted(names)


def test_list_all_empty() -> None:
    reg = SolverRegistry()
    assert reg.list_all() == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_keyword_overlap() -> None:
    reg = SolverRegistry()
    reg.register(_make_descriptor("caesar", keywords=frozenset({"caesar", "cipher", "rot"})))
    reg.register(_make_descriptor("vigenere", keywords=frozenset({"vigenere", "cipher", "poly"})))
    reg.register(_make_descriptor("rsa", keywords=frozenset({"rsa", "asymmetric"})))

    results = reg.search("cipher rot")
    names = [d.name for d in results]
    # caesar has overlap 2 (cipher, rot); vigenere has overlap 1 (cipher)
    assert names[0] == "caesar"
    assert "vigenere" in names
    assert "rsa" not in names


def test_search_category_filter() -> None:
    reg = SolverRegistry()
    reg.register(
        _make_descriptor(
            "math_tool",
            category="math",
            keywords=frozenset({"prime", "factor"}),
        )
    )
    reg.register(
        _make_descriptor(
            "crypto_tool",
            category="cryptography",
            keywords=frozenset({"prime", "rsa"}),
        )
    )
    results = reg.search("prime", category="math")
    assert len(results) == 1
    assert results[0].name == "math_tool"


def test_search_no_match_returns_empty() -> None:
    reg = SolverRegistry()
    reg.register(_make_descriptor("only_one", keywords=frozenset({"unique"})))
    assert reg.search("zzznomatch") == []


def test_search_empty_query_returns_empty() -> None:
    reg = SolverRegistry()
    reg.register(_make_descriptor("solver", keywords=frozenset({"solver"})))
    assert reg.search("") == []


# ---------------------------------------------------------------------------
# find_by_tags
# ---------------------------------------------------------------------------


def test_find_by_tags_intersection() -> None:
    reg = SolverRegistry()
    reg.register(_make_descriptor("a", tags=frozenset({"cipher_id", "classical_cipher"})))
    reg.register(_make_descriptor("b", tags=frozenset({"encoding_chain"})))
    reg.register(_make_descriptor("c", tags=frozenset({"classical_cipher", "prime_sieve"})))

    results = reg.find_by_tags(frozenset({"cipher_id", "classical_cipher"}))
    names = {d.name for d in results}
    assert "a" in names
    assert "c" in names
    assert "b" not in names


def test_find_by_tags_empty_returns_empty() -> None:
    reg = SolverRegistry()
    reg.register(_make_descriptor("solver", tags=frozenset({"cipher_id"})))
    assert reg.find_by_tags(frozenset()) == []


def test_find_by_tags_sorted_by_priority_then_name() -> None:
    reg = SolverRegistry()
    reg.register(_make_descriptor("z_low", tags=frozenset({"tag"}), priority=10))
    reg.register(_make_descriptor("a_high", tags=frozenset({"tag"}), priority=50))
    reg.register(_make_descriptor("m_low", tags=frozenset({"tag"}), priority=10))

    results = reg.find_by_tags(frozenset({"tag"}))
    # priority 10 comes before 50; within same priority, alphabetical (m < z)
    assert [r.name for r in results] == ["m_low", "z_low", "a_high"]


# ---------------------------------------------------------------------------
# global registry singleton
# ---------------------------------------------------------------------------


def test_global_registry_singleton() -> None:
    r1 = get_global_solver_registry()
    r2 = get_global_solver_registry()
    assert r1 is r2


def test_global_registry_is_solver_registry() -> None:
    assert isinstance(get_global_solver_registry(), SolverRegistry)
