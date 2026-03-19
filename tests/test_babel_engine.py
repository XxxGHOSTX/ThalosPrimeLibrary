"""Tests for the deterministic Babel page engine."""

from __future__ import annotations

import pytest

from thalos_prime.babel import (
    ALPHABET,
    DEFAULT_PAGE_LENGTH,
    basile_index_to_text,
    deterministic_page,
    text_to_basile_index,
)


def test_basile_index_round_trip_for_babel_text() -> None:
    """Converting text to an index and back preserves the original string."""
    source = "babel, text."
    index = text_to_basile_index(source)
    assert basile_index_to_text(index, len(source)) == source



def test_deterministic_page_is_stable() -> None:
    """The same seed must always produce the same page."""
    assert deterministic_page("seed") == deterministic_page("seed")



def test_deterministic_page_uses_babel_alphabet_and_default_length() -> None:
    """Generated pages only use the canonical Babel alphabet."""
    page = deterministic_page("canonical-seed")
    assert len(page) == DEFAULT_PAGE_LENGTH
    assert set(page).issubset(set(ALPHABET))



def test_deterministic_page_changes_with_seed() -> None:
    """Distinct seeds should normally map to distinct pages."""
    assert deterministic_page("seed-a") != deterministic_page("seed-b")



def test_basile_index_to_text_rejects_negative_values() -> None:
    """Negative indices are invalid."""
    with pytest.raises(ValueError, match="non-negative"):
        basile_index_to_text(-1, 10)



def test_text_to_basile_index_rejects_non_babel_characters() -> None:
    """Characters outside the canonical alphabet must fail fast."""
    with pytest.raises(ValueError, match="unsupported Babel character"):
        text_to_basile_index("Babel")
