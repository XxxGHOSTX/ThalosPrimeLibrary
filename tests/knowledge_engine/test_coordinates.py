"""Tests for knowledge_engine.coordinates."""

from __future__ import annotations

import pytest

from thalos_prime.knowledge_engine.coordinates.generator import CoordinateGenerator


def test_generator_lifecycle() -> None:
    gen = CoordinateGenerator()
    gen.initialize()
    gen.validate()
    gen.operate()
    gen.reconcile()
    cp = gen.checkpoint()
    assert cp["component"] == "CoordinateGenerator"
    gen.terminate()


def test_generate_basic() -> None:
    gen = CoordinateGenerator()
    gen.initialize()
    coord = gen.generate("hello world", "lineage_hash_abc", 0)
    assert len(coord.coordinate_hex) == 64
    assert coord.semantic_cluster == 0
    assert coord.lineage_hash == "lineage_hash_abc"
    gen.terminate()


def test_generate_deterministic() -> None:
    gen = CoordinateGenerator()
    gen.initialize()
    coord1 = gen.generate("same content", "same_lineage", 1)
    coord2 = gen.generate("same content", "same_lineage", 1)
    assert coord1.coordinate_hex == coord2.coordinate_hex
    assert coord1.content_hash == coord2.content_hash
    gen.terminate()


def test_generate_different_inputs() -> None:
    gen = CoordinateGenerator()
    gen.initialize()
    coord1 = gen.generate("content A", "lineage", 0)
    coord2 = gen.generate("content B", "lineage", 0)
    assert coord1.coordinate_hex != coord2.coordinate_hex
    gen.terminate()


def test_generate_negative_cluster_raises() -> None:
    gen = CoordinateGenerator()
    gen.initialize()
    with pytest.raises(ValueError, match="semantic_cluster must be >= 0"):
        gen.generate("content", "lineage", -1)
    gen.terminate()


def test_generate_not_initialized_raises() -> None:
    gen = CoordinateGenerator()
    with pytest.raises(RuntimeError, match="not initialized"):
        gen.generate("content", "lineage", 0)


def test_generate_count_increments() -> None:
    gen = CoordinateGenerator()
    gen.initialize()
    gen.generate("a", "b", 0)
    gen.generate("c", "d", 1)
    cp = gen.checkpoint()
    assert cp["generated_count"] == 2
    gen.terminate()
