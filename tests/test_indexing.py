"""Tests for the PRP-based Indexing subsystem.

Covers Coordinate, CoordinateType, ArtifactCoordinates, and PrpIndexer.
All tests use deterministic keys and inputs for full reproducibility.
"""

from __future__ import annotations

import pytest

from thalos_prime.indexing.prp import (
    ArtifactCoordinates,
    Coordinate,
    CoordinateType,
    PrpIndexer,
)

# ---------------------------------------------------------------------------
# Fixed test constants
# ---------------------------------------------------------------------------
_KEY = b"\xab\xcd\xef\x01" * 4  # 16-byte HMAC key (deterministic)
_KEY_ZEROS = b"\x00" * 16
_KEY_ONES = b"\xff" * 16


# ===========================================================================
# Coordinate
# ===========================================================================


class TestCoordinate:
    def test_fields(self) -> None:
        coord = Coordinate(hexagon=1, wall=2, shelf=3, volume=4, page=5)
        assert coord.hexagon == 1
        assert coord.wall == 2
        assert coord.shelf == 3
        assert coord.volume == 4
        assert coord.page == 5

    def test_to_tuple(self) -> None:
        coord = Coordinate(hexagon=10, wall=20, shelf=30, volume=40, page=50)
        assert coord.to_tuple() == (10, 20, 30, 40, 50)

    def test_to_hex_str_length(self) -> None:
        coord = Coordinate(hexagon=0xFFFF, wall=0xFF, shelf=0xFF, volume=0xFFFF, page=0xFFFF)
        hex_str = coord.to_hex_str()
        # 4 + 2 + 2 + 4 + 4 = 16 hex characters
        assert len(hex_str) == 16

    def test_to_hex_str_format(self) -> None:
        coord = Coordinate(hexagon=0x0001, wall=0x02, shelf=0x03, volume=0x0004, page=0x0005)
        assert coord.to_hex_str() == "0001020300040005"

    def test_to_hex_str_max_values(self) -> None:
        coord = Coordinate(
            hexagon=65535, wall=255, shelf=255, volume=65535, page=65535
        )
        assert coord.to_hex_str() == "ffffffffffffffff"

    def test_to_hex_str_zero_values(self) -> None:
        coord = Coordinate(hexagon=0, wall=0, shelf=0, volume=0, page=0)
        assert coord.to_hex_str() == "0000000000000000"

    def test_is_frozen(self) -> None:
        import dataclasses

        coord = Coordinate(hexagon=1, wall=2, shelf=3, volume=4, page=5)
        with pytest.raises(dataclasses.FrozenInstanceError):
            coord.hexagon = 99  # type: ignore[misc]

    def test_equality(self) -> None:
        c1 = Coordinate(hexagon=1, wall=2, shelf=3, volume=4, page=5)
        c2 = Coordinate(hexagon=1, wall=2, shelf=3, volume=4, page=5)
        assert c1 == c2

    def test_inequality(self) -> None:
        c1 = Coordinate(hexagon=1, wall=2, shelf=3, volume=4, page=5)
        c2 = Coordinate(hexagon=9, wall=2, shelf=3, volume=4, page=5)
        assert c1 != c2

    def test_hashable(self) -> None:
        coord = Coordinate(hexagon=1, wall=2, shelf=3, volume=4, page=5)
        # Frozen dataclasses are hashable
        coord_set = {coord}
        assert coord in coord_set


# ===========================================================================
# CoordinateType
# ===========================================================================


class TestCoordinateType:
    def test_all_members(self) -> None:
        members = set(CoordinateType)
        assert CoordinateType.IDENTITY in members
        assert CoordinateType.SEMANTIC in members
        assert CoordinateType.PROVENANCE in members
        assert CoordinateType.VERSION in members
        assert CoordinateType.TRUST_STATE in members

    def test_string_values(self) -> None:
        assert CoordinateType.IDENTITY.value == "identity"
        assert CoordinateType.SEMANTIC.value == "semantic"
        assert CoordinateType.PROVENANCE.value == "provenance"
        assert CoordinateType.VERSION.value == "version"
        assert CoordinateType.TRUST_STATE.value == "trust_state"

    def test_is_str(self) -> None:
        assert isinstance(CoordinateType.IDENTITY, str)


# ===========================================================================
# PrpIndexer
# ===========================================================================


class TestPrpIndexer:
    def test_init_valid_key(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        assert indexer is not None

    def test_init_invalid_key_length(self) -> None:
        with pytest.raises(ValueError, match="16 bytes"):
            PrpIndexer(key=b"\x00" * 8)

    def test_init_empty_key_raises(self) -> None:
        with pytest.raises(ValueError, match="16 bytes"):
            PrpIndexer(key=b"")

    def test_init_long_key_accepted(self) -> None:
        # HMAC accepts keys of any length >= _MIN_KEY_SIZE (16 bytes)
        indexer = PrpIndexer(key=b"\x00" * 32)
        assert indexer is not None

    def test_index_returns_coordinate(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        coord = indexer.index("hello world")
        assert isinstance(coord, Coordinate)

    def test_index_deterministic(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        c1 = indexer.index("hello world")
        c2 = indexer.index("hello world")
        assert c1 == c2

    def test_index_different_inputs_different_coords(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        c1 = indexer.index("content A")
        c2 = indexer.index("content B")
        assert c1 != c2

    def test_index_different_keys_different_coords(self) -> None:
        indexer1 = PrpIndexer(key=_KEY_ZEROS)
        indexer2 = PrpIndexer(key=_KEY_ONES)
        c1 = indexer1.index("same content")
        c2 = indexer2.index("same content")
        assert c1 != c2

    def test_index_coordinate_dimensions_in_range(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        coord = indexer.index("range check")
        assert 0 <= coord.hexagon <= 65535
        assert 0 <= coord.wall <= 255
        assert 0 <= coord.shelf <= 255
        assert 0 <= coord.volume <= 65535
        assert 0 <= coord.page <= 65535

    def test_compute_hash_returns_16_bytes(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        h = indexer._compute_hash("test")
        assert len(h) == 16

    def test_compute_hash_deterministic(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        assert indexer._compute_hash("x") == indexer._compute_hash("x")

    def test_prp_transform_returns_16_bytes(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        data = b"\x00" * 16
        result = indexer._prp_transform(data)
        assert len(result) == 16

    def test_prp_transform_wrong_size_raises(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        with pytest.raises(ValueError, match="16 bytes"):
            indexer._prp_transform(b"\x00" * 8)

    def test_prp_transform_deterministic(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        data = b"\x42" * 16
        assert indexer._prp_transform(data) == indexer._prp_transform(data)

    def test_bytes_to_coordinate_byte_mapping(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        # Carefully craft bytes where we know the expected values
        data = bytes([0x00, 0x01, 0x02, 0x03, 0x00, 0x04, 0x00, 0x05] + [0] * 8)
        coord = indexer._bytes_to_coordinate(data)
        assert coord.hexagon == 0x0001
        assert coord.wall == 0x02
        assert coord.shelf == 0x03
        assert coord.volume == 0x0004
        assert coord.page == 0x0005

    def test_index_empty_string(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        coord = indexer.index("")
        assert isinstance(coord, Coordinate)

    def test_index_unicode_content(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        coord = indexer.index("héllo wörld 你好")
        assert isinstance(coord, Coordinate)

    def test_index_long_content(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        content = "x" * 10_000
        coord = indexer.index(content)
        assert isinstance(coord, Coordinate)


# ===========================================================================
# PrpIndexer.index_artifact
# ===========================================================================


class TestPrpIndexerArtifact:
    def test_index_artifact_returns_all_coordinates(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        coords = indexer.index_artifact(
            artifact_id="aid-001",
            content="sample content",
            provenance_hash="a" * 64,
            version=1,
            trust_value=0.75,
        )
        assert isinstance(coords, ArtifactCoordinates)
        assert isinstance(coords.identity, Coordinate)
        assert isinstance(coords.semantic, Coordinate)
        assert isinstance(coords.provenance, Coordinate)
        assert isinstance(coords.version, Coordinate)
        assert isinstance(coords.trust_state, Coordinate)

    def test_index_artifact_deterministic(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        c1 = indexer.index_artifact(
            artifact_id="aid-det",
            content="deterministic",
            provenance_hash="b" * 64,
            version=3,
            trust_value=0.5,
        )
        c2 = indexer.index_artifact(
            artifact_id="aid-det",
            content="deterministic",
            provenance_hash="b" * 64,
            version=3,
            trust_value=0.5,
        )
        assert c1.identity == c2.identity
        assert c1.semantic == c2.semantic
        assert c1.provenance == c2.provenance
        assert c1.version == c2.version
        assert c1.trust_state == c2.trust_state

    def test_index_artifact_coordinates_differ_by_type(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        coords = indexer.index_artifact(
            artifact_id="aid-002",
            content="content-002",
            provenance_hash="c" * 64,
            version=1,
            trust_value=0.9,
        )
        # All five coordinates address different spaces
        unique = {
            coords.identity,
            coords.semantic,
            coords.provenance,
            coords.version,
            coords.trust_state,
        }
        assert len(unique) == 5

    def test_index_artifact_version_sensitivity(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        c1 = indexer.index_artifact(
            artifact_id="aid-v", content="c", provenance_hash="d" * 64,
            version=1, trust_value=0.0,
        )
        c2 = indexer.index_artifact(
            artifact_id="aid-v", content="c", provenance_hash="d" * 64,
            version=2, trust_value=0.0,
        )
        assert c1.version != c2.version
        # identity is derived from artifact_id only, unchanged
        assert c1.identity == c2.identity

    def test_index_artifact_trust_sensitivity(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        c1 = indexer.index_artifact(
            artifact_id="aid-t", content="c", provenance_hash="e" * 64,
            version=1, trust_value=0.0,
        )
        c2 = indexer.index_artifact(
            artifact_id="aid-t", content="c", provenance_hash="e" * 64,
            version=1, trust_value=1.0,
        )
        assert c1.trust_state != c2.trust_state

    def test_index_artifact_content_independence_from_identity(self) -> None:
        indexer = PrpIndexer(key=_KEY)
        c1 = indexer.index_artifact(
            artifact_id="same-id", content="content A", provenance_hash="f" * 64,
            version=1, trust_value=0.5,
        )
        c2 = indexer.index_artifact(
            artifact_id="same-id", content="content B", provenance_hash="f" * 64,
            version=1, trust_value=0.5,
        )
        # Identity coordinate is derived from artifact_id, not content
        assert c1.identity == c2.identity
        # Semantic coordinate is derived from content
        assert c1.semantic != c2.semantic


# ===========================================================================
# ArtifactCoordinates
# ===========================================================================


class TestArtifactCoordinates:
    def test_construct_directly(self) -> None:
        coord = Coordinate(hexagon=1, wall=2, shelf=3, volume=4, page=5)
        ac = ArtifactCoordinates(
            identity=coord,
            semantic=coord,
            provenance=coord,
            version=coord,
            trust_state=coord,
        )
        assert ac.identity == coord
        assert ac.semantic == coord

    def test_mutable(self) -> None:
        coord = Coordinate(hexagon=0, wall=0, shelf=0, volume=0, page=0)
        new_coord = Coordinate(hexagon=1, wall=1, shelf=1, volume=1, page=1)
        ac = ArtifactCoordinates(
            identity=coord,
            semantic=coord,
            provenance=coord,
            version=coord,
            trust_state=coord,
        )
        ac.identity = new_coord
        assert ac.identity == new_coord
