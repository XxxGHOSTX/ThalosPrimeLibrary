"""Tests for data plane components."""

import json
import pickle
from pathlib import Path

import numpy as np
import pytest
from sklearn.feature_extraction.text import TfidfVectorizer

from src.data_plane import DeterministicGenerator, TFIDFRetriever


@pytest.fixture
def test_corpus(tmp_path: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Create test corpus and index."""
    # Create corpus
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()

    docs = [
        "The quick brown fox jumps over the lazy dog.",
        "A journey of a thousand miles begins with a single step.",
        "To be or not to be, that is the question.",
    ]

    documents = []
    for i, content in enumerate(docs):
        doc_file = corpus_dir / f"doc_{i:03d}.txt"
        doc_file.write_text(content)
        documents.append({
            "doc_id": f"doc_{i:03d}",
            "content": content,
            "metadata": {"filename": doc_file.name}
        })

    # Create TF-IDF index
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(docs)

    index_path = tmp_path / "index.pkl"
    with open(index_path, "wb") as f:
        pickle.dump({
            "vectorizer": vectorizer,
            "tfidf_matrix": tfidf_matrix,
        }, f)

    # Create manifest
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(documents, f)

    return index_path, manifest_path


class TestTFIDFRetriever:
    """Test TF-IDF retriever."""

    def test_load_index(self, test_corpus: tuple[Path, Path]) -> None:
        """Test loading index."""
        index_path, manifest_path = test_corpus

        retriever = TFIDFRetriever(index_path, manifest_path)
        retriever.load()

        assert retriever.loaded
        assert retriever.vectorizer is not None
        assert retriever.tfidf_matrix is not None
        assert len(retriever.documents) == 3

    def test_retrieve_documents(self, test_corpus: tuple[Path, Path]) -> None:
        """Test document retrieval."""
        index_path, manifest_path = test_corpus

        retriever = TFIDFRetriever(index_path, manifest_path)
        retriever.load()

        results = retriever.retrieve("fox dog", top_k=2)

        assert len(results) <= 2
        assert all("doc_id" in r for r in results)
        assert all("content" in r for r in results)
        assert all("score" in r for r in results)

    def test_retrieve_ordering(self, test_corpus: tuple[Path, Path]) -> None:
        """Test that results are ordered by score."""
        index_path, manifest_path = test_corpus

        retriever = TFIDFRetriever(index_path, manifest_path)
        retriever.load()

        results = retriever.retrieve("journey miles step", top_k=3)

        # Scores should be in descending order
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


class TestDeterministicGenerator:
    """Test deterministic generator."""

    def test_same_seed_same_output(self) -> None:
        """Test that same seed produces same output."""
        docs = [
            {"doc_id": "doc1", "content": "Test content 1", "score": 0.8},
            {"doc_id": "doc2", "content": "Test content 2", "score": 0.6},
        ]

        gen1 = DeterministicGenerator(seed=42, max_sentences=3)
        gen2 = DeterministicGenerator(seed=42, max_sentences=3)

        result1 = gen1.generate(docs)
        result2 = gen2.generate(docs)

        assert result1 == result2

    def test_different_seed_different_output(self) -> None:
        """Test that different seeds may produce different output."""
        docs = [
            {"doc_id": "doc1", "content": "Test content 1", "score": 0.8},
            {"doc_id": "doc2", "content": "Test content 2", "score": 0.6},
        ]

        gen1 = DeterministicGenerator(seed=42, max_sentences=3)
        gen2 = DeterministicGenerator(seed=99, max_sentences=3)

        result1 = gen1.generate(docs)
        result2 = gen2.generate(docs)

        # May be different (depends on random selection)
        # But both should be valid
        assert result1 is not None
        assert result2 is not None

    def test_empty_docs(self) -> None:
        """Test generation with empty documents."""
        gen = DeterministicGenerator(seed=42, max_sentences=3)
        result = gen.generate([])

        assert "No relevant information found" in result

    def test_generate_tokens(self) -> None:
        """Test token generation."""
        gen = DeterministicGenerator(seed=42, max_sentences=3)

        tokens = gen.generate_tokens("hello world test", max_tokens=2)

        assert len(tokens) == 2
        assert all(isinstance(t, str) for t in tokens)

    def test_deterministic_tokens(self) -> None:
        """Test token generation is deterministic."""
        gen1 = DeterministicGenerator(seed=42, max_sentences=3)
        gen2 = DeterministicGenerator(seed=42, max_sentences=3)

        tokens1 = gen1.generate_tokens("hello world test", max_tokens=5)
        tokens2 = gen2.generate_tokens("hello world test", max_tokens=5)

        assert tokens1 == tokens2
