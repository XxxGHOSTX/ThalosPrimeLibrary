"""Tests for utility functions."""

import time

import pytest

from src.utils import compute_file_hash, generate_deterministic_seed, truncate_to_sentences


class TestDeterministicSeed:
    """Test deterministic seed generation."""

    def test_same_inputs_same_seed(self) -> None:
        """Test that same inputs produce same seed."""
        seed1 = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello world",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1000.0,
        )
        seed2 = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello world",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1000.0,
        )
        assert seed1 == seed2

    def test_different_input_different_seed(self) -> None:
        """Test that different inputs produce different seeds."""
        seed1 = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1000.0,
        )
        seed2 = generate_deterministic_seed(
            session_id="test_session",
            user_input="world",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1000.0,
        )
        assert seed1 != seed2

    def test_time_bucket_determinism(self) -> None:
        """Test that timestamps in same bucket produce same seed."""
        seed1 = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1000.0,
        )
        seed2 = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1500.0,
        )
        assert seed1 == seed2

    def test_different_bucket_different_seed(self) -> None:
        """Test that different time buckets produce different seeds."""
        seed1 = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1000.0,
        )
        seed2 = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=5000.0,
        )
        assert seed1 != seed2

    def test_seed_range(self) -> None:
        """Test that seed is within valid range."""
        seed = generate_deterministic_seed(
            session_id="test_session",
            user_input="hello",
            salt="test_salt",
            time_bucket_seconds=3600,
            timestamp=1000.0,
        )
        assert 0 <= seed < 2**31


class TestTruncateSentences:
    """Test sentence truncation."""

    def test_truncate_basic(self) -> None:
        """Test basic truncation."""
        text = "First sentence. Second sentence. Third sentence."
        result = truncate_to_sentences(text, 2)
        assert result == "First sentence. Second sentence."

    def test_truncate_empty(self) -> None:
        """Test truncation of empty string."""
        result = truncate_to_sentences("", 5)
        assert result == ""

    def test_truncate_fewer_than_max(self) -> None:
        """Test truncation when text has fewer sentences than max."""
        text = "Only one sentence."
        result = truncate_to_sentences(text, 5)
        assert result == "Only one sentence."

    def test_truncate_multiple_terminators(self) -> None:
        """Test with different sentence terminators."""
        text = "Question? Exclamation! Period."
        result = truncate_to_sentences(text, 2)
        assert "Question?" in result
        assert "Exclamation!" in result


class TestComputeFileHash:
    """Test file hash computation."""

    def test_file_hash(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test file hash computation."""
        # Create a temporary file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Compute hash
        hash1 = compute_file_hash(str(test_file))
        hash2 = compute_file_hash(str(test_file))

        # Hashes should be the same
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 produces 64-character hex digest

    def test_different_content_different_hash(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test that different content produces different hash."""
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"

        file1.write_text("content 1")
        file2.write_text("content 2")

        hash1 = compute_file_hash(str(file1))
        hash2 = compute_file_hash(str(file2))

        assert hash1 != hash2
