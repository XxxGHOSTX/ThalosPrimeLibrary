"""Tests for knowledge_engine.ingestion."""

from __future__ import annotations

import pytest

from thalos_prime.knowledge_engine.ingestion.source_ingester import IngestionManager
from thalos_prime.knowledge_engine.ingestion.text_extractor import TextExtractor
from thalos_prime.knowledge_engine.ingestion.translator import TranslationService
from thalos_prime.knowledge_engine.models import ArtifactRecord, SourceRecord, SourceType


def test_ingestion_manager_lifecycle() -> None:
    mgr = IngestionManager()
    mgr.initialize()
    mgr.validate()
    mgr.operate()
    mgr.reconcile()
    cp = mgr.checkpoint()
    assert cp["component"] == "IngestionManager"
    assert cp["ingested_count"] == 0
    mgr.terminate()


def test_ingest_text_basic() -> None:
    mgr = IngestionManager()
    mgr.initialize()
    record = mgr.ingest_text("Hello, this is a test sentence.")
    assert record.source_type == SourceType.TEXT
    assert len(record.content_hash) == 64
    mgr.terminate()


def test_ingest_text_with_metadata() -> None:
    mgr = IngestionManager()
    mgr.initialize()
    record = mgr.ingest_text("Some content", metadata={"key": "value"})
    assert record.metadata == {"key": "value"}
    mgr.terminate()


def test_ingest_text_empty_raises() -> None:
    mgr = IngestionManager()
    mgr.initialize()
    with pytest.raises(ValueError, match="must not be empty"):
        mgr.ingest_text("   ")
    mgr.terminate()


def test_ingest_text_not_initialized_raises() -> None:
    mgr = IngestionManager()
    with pytest.raises(RuntimeError, match="not initialized"):
        mgr.ingest_text("hello world")


def test_ingest_url_not_initialized_raises() -> None:
    mgr = IngestionManager()
    with pytest.raises(RuntimeError, match="not initialized"):
        mgr.ingest_url("https://example.com")


def test_validate_not_initialized_raises() -> None:
    mgr = IngestionManager()
    with pytest.raises(RuntimeError, match="not initialized"):
        mgr.validate()


def test_reconcile_not_initialized_raises() -> None:
    mgr = IngestionManager()
    with pytest.raises(RuntimeError, match="not initialized"):
        mgr.reconcile()


def test_ingest_count_increments() -> None:
    mgr = IngestionManager()
    mgr.initialize()
    mgr.ingest_text("First sentence here.")
    mgr.ingest_text("Second sentence here.")
    cp = mgr.checkpoint()
    assert cp["ingested_count"] == 2
    mgr.terminate()


def test_text_extractor_lifecycle() -> None:
    extractor = TextExtractor()
    extractor.initialize()
    extractor.validate()
    extractor.operate()
    extractor.reconcile()
    cp = extractor.checkpoint()
    assert cp["component"] == "TextExtractor"
    extractor.terminate()


def test_text_extractor_plain() -> None:
    extractor = TextExtractor()
    extractor.initialize()
    source = SourceRecord(
        id="s1", text_content="Hello world", source_type=SourceType.TEXT,
        content_hash="abc",
    )
    artifact = extractor.extract(source)
    assert artifact.extracted_text == "Hello world"
    assert artifact.extraction_method == "plain"
    extractor.terminate()


def test_text_extractor_html() -> None:
    extractor = TextExtractor()
    extractor.initialize()
    source = SourceRecord(
        id="s2", text_content="<html><body><p>Hello world</p></body></html>",
        source_type=SourceType.URL, content_hash="def",
    )
    artifact = extractor.extract(source)
    assert "Hello world" in artifact.extracted_text
    assert artifact.extraction_method == "beautifulsoup4"
    extractor.terminate()


def test_text_extractor_not_initialized_raises() -> None:
    extractor = TextExtractor()
    source = SourceRecord(
        id="s1", text_content="text", source_type=SourceType.TEXT,
        content_hash="abc",
    )
    with pytest.raises(RuntimeError, match="not initialized"):
        extractor.extract(source)


def test_translation_service_lifecycle() -> None:
    svc = TranslationService()
    svc.initialize()
    svc.validate()
    svc.operate()
    svc.reconcile()
    cp = svc.checkpoint()
    assert cp["component"] == "TranslationService"
    svc.terminate()


def test_translation_service_ascii() -> None:
    svc = TranslationService()
    svc.initialize()
    artifact = ArtifactRecord(
        id="a1", source_id="s1",
        extracted_text="This is plain English text.", extraction_method="plain",
    )
    _, stability = svc.translate(artifact)
    assert stability == 1.0
    svc.terminate()


def test_translation_service_not_initialized_raises() -> None:
    svc = TranslationService()
    artifact = ArtifactRecord(
        id="a1", source_id="s1", extracted_text="text", extraction_method="plain",
    )
    with pytest.raises(RuntimeError, match="not initialized"):
        svc.translate(artifact)
