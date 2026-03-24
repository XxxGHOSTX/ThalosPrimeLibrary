"""Tests for the library package: constraints, store, and reconstruct pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

from thalos_prime.library.constraints import validate_artifact, validate_min_word_length
from thalos_prime.library.models import LibraryArtifact
from thalos_prime.library.reconstruct import clean_noise, reconstruct, segment_words
from thalos_prime.library.store import LocalLibraryStore


class TestValidateMinWordLength:
    """Tests for validate_min_word_length."""

    def test_passes_for_2_char_words(self) -> None:
        """Words with length >= 2 pass validation."""
        assert validate_min_word_length("hello world") is True

    def test_fails_for_single_char_word(self) -> None:
        """A single-character word fails validation."""
        assert validate_min_word_length("a hello world") is False

    def test_passes_for_empty_string(self) -> None:
        """Empty string has no words and passes."""
        assert validate_min_word_length("") is True

    def test_custom_min_len(self) -> None:
        """Custom min_len is respected."""
        assert validate_min_word_length("hi", min_len=3) is False
        assert validate_min_word_length("hello", min_len=3) is True

    def test_all_words_must_meet_min_len(self) -> None:
        """All words must meet min_len, not just some."""
        assert validate_min_word_length("hello x world", min_len=2) is False


class TestValidateArtifact:
    """Tests for validate_artifact."""

    def test_valid_artifact_passes(self) -> None:
        """An artifact with valid content passes."""
        artifact = LibraryArtifact.create("hello world")
        valid, reason = validate_artifact(artifact)
        assert valid is True
        assert reason == "ok"

    def test_empty_content_fails(self) -> None:
        """An artifact with empty content fails."""
        artifact = LibraryArtifact.create("")
        valid, reason = validate_artifact(artifact)
        assert valid is False
        assert "empty" in reason.lower()

    def test_whitespace_only_fails(self) -> None:
        """An artifact with only whitespace fails."""
        artifact = LibraryArtifact.create("   ")
        valid, _reason = validate_artifact(artifact)
        assert valid is False

    def test_single_char_word_fails(self) -> None:
        """An artifact containing a single-character word fails."""
        artifact = LibraryArtifact.create("hello x world")
        valid, reason = validate_artifact(artifact)
        assert valid is False
        assert "shorter" in reason.lower() or "char" in reason.lower()


class TestLibraryArtifact:
    """Tests for LibraryArtifact model."""

    def test_create_sets_sha256_id(self) -> None:
        """create() sets id to SHA-256 of content."""
        from thalos_prime.execution_ir.hash import sha256_hex
        content = "test content"
        artifact = LibraryArtifact.create(content)
        assert artifact.id == sha256_hex(content)

    def test_same_content_same_id(self) -> None:
        """Two artifacts with identical content have the same ID."""
        a1 = LibraryArtifact.create("same content")
        a2 = LibraryArtifact.create("same content")
        assert a1.id == a2.id

    def test_different_content_different_id(self) -> None:
        """Different content produces different IDs."""
        a1 = LibraryArtifact.create("content A")
        a2 = LibraryArtifact.create("content B")
        assert a1.id != a2.id

    def test_serialization_round_trip(self) -> None:
        """to_dict/from_dict preserves all fields."""
        artifact = LibraryArtifact.create("hello world", artifact_type="document")
        d = artifact.to_dict()
        restored = LibraryArtifact.from_dict(d)
        assert restored.id == artifact.id
        assert restored.content == artifact.content
        assert restored.artifact_type == artifact.artifact_type


class TestLocalLibraryStore:
    """Tests for LocalLibraryStore deduplication and retrieval."""

    def test_save_and_get_round_trip(self) -> None:
        """save/get correctly persists and retrieves an artifact."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalLibraryStore(base_path=Path(tmp))
            artifact = LibraryArtifact.create("hello world")
            store.save(artifact)
            retrieved = store.get(artifact.id)
            assert retrieved is not None
            assert retrieved.id == artifact.id
            assert retrieved.content == artifact.content

    def test_deduplication_by_content_hash(self) -> None:
        """Saving the same content twice does not create duplicate entries."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalLibraryStore(base_path=Path(tmp))
            a1 = LibraryArtifact.create("same content here")
            a2 = LibraryArtifact.create("same content here")

            store.save(a1)
            store.save(a2)

            ids = store.list_ids()
            assert ids.count(a1.id) == 1

    def test_get_returns_none_for_missing(self) -> None:
        """get() returns None for an unknown artifact ID."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalLibraryStore(base_path=Path(tmp))
            assert store.get("nonexistent-id") is None

    def test_list_ids_returns_all_stored(self) -> None:
        """list_ids returns all saved artifact IDs."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalLibraryStore(base_path=Path(tmp))
            a1 = LibraryArtifact.create("content one")
            a2 = LibraryArtifact.create("content two")
            store.save(a1)
            store.save(a2)

            ids = store.list_ids()
            assert a1.id in ids
            assert a2.id in ids


class TestCleanNoise:
    """Tests for clean_noise utility."""

    def test_removes_control_characters(self) -> None:
        """clean_noise removes non-printable control characters."""
        noisy = "hello\x00\x01world"
        cleaned = clean_noise(noisy)
        assert "\x00" not in cleaned
        assert "\x01" not in cleaned
        assert "hello" in cleaned
        assert "world" in cleaned

    def test_normalizes_whitespace(self) -> None:
        """clean_noise collapses multiple spaces to single space."""
        result = clean_noise("hello   world")
        assert result == "hello world"

    def test_strips_leading_trailing(self) -> None:
        """clean_noise strips leading and trailing whitespace."""
        assert clean_noise("  hello  ") == "hello"


class TestSegmentWords:
    """Tests for segment_words utility."""

    def test_filters_short_words(self) -> None:
        """segment_words filters words shorter than min_len."""
        words = segment_words("hello a world b ok", min_len=2)
        assert "a" not in words
        assert "b" not in words
        assert "hello" in words
        assert "world" in words
        assert "ok" in words

    def test_default_min_len_is_2(self) -> None:
        """Default min_len is 2."""
        words = segment_words("hi me you")
        assert "hi" in words
        assert "me" in words

    def test_returns_empty_for_all_short_words(self) -> None:
        """Returns empty list when all words are below min_len."""
        assert segment_words("a b c", min_len=2) == []


class TestReconstruct:
    """Tests for the reconstruct pipeline."""

    def test_reconstruct_produces_artifact_from_valid_text(self) -> None:
        """reconstruct returns at least one artifact from clean text."""
        artifacts = reconstruct("the quick brown fox jumps over the lazy dog")
        assert len(artifacts) >= 1

    def test_reconstruct_filters_single_char_tokens(self) -> None:
        """reconstruct excludes single-character tokens from artifacts."""
        artifacts = reconstruct("a b c hello world")
        assert artifacts  # should still produce an artifact from hello world
        content = artifacts[0].content
        words = content.split()
        assert all(len(w) >= 2 for w in words)

    def test_reconstruct_empty_text_returns_empty(self) -> None:
        """reconstruct returns empty list for text with no valid words."""
        result = reconstruct("a b c")
        assert result == []

    def test_reconstruct_saves_to_store_when_provided(self) -> None:
        """reconstruct saves valid artifacts to the store."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalLibraryStore(base_path=Path(tmp))
            artifacts = reconstruct("hello world from thalos", store=store)
            assert artifacts

            stored_ids = store.list_ids()
            for artifact in artifacts:
                assert artifact.id in stored_ids

    def test_reconstruct_deduplicates_via_store(self) -> None:
        """Calling reconstruct twice with the same text stores only one artifact."""
        with tempfile.TemporaryDirectory() as tmp:
            store = LocalLibraryStore(base_path=Path(tmp))
            reconstruct("hello world again", store=store)
            reconstruct("hello world again", store=store)

            assert len(store.list_ids()) == 1

    def test_reconstruct_garbled_text(self) -> None:
        """reconstruct handles garbled text with noise characters."""
        garbled = "hel\x00lo wo\x01rld from the system"
        artifacts = reconstruct(garbled)
        assert artifacts
        content = artifacts[0].content
        assert "\x00" not in content
        assert "\x01" not in content
