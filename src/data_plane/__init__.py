"""Data plane for TF-IDF retrieval and deterministic text generation."""

import json
import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.observability import get_logger
from src.utils import truncate_to_sentences

logger = get_logger(__name__)


class TFIDFRetriever:
    """TF-IDF based document retriever with deterministic ranking."""

    def __init__(self, index_path: Path, manifest_path: Path) -> None:
        """Initialize retriever."""
        self.index_path = index_path
        self.manifest_path = manifest_path
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[np.ndarray] = None
        self.documents: list[dict[str, str]] = []
        self.loaded = False

    def load(self) -> None:
        """Load index and manifest."""
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index not found: {self.index_path}")
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {self.manifest_path}")

        # Load TF-IDF index
        with open(self.index_path, "rb") as f:
            index_data = pickle.load(f)
            self.vectorizer = index_data["vectorizer"]
            self.tfidf_matrix = index_data["tfidf_matrix"]

        # Load manifest
        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.documents = json.load(f)

        self.loaded = True
        logger.info(
            "Index loaded",
            num_documents=len(self.documents),
            vocab_size=len(self.vectorizer.vocabulary_) if self.vectorizer else 0,
        )

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        Retrieve top-k documents for a query.

        Args:
            query: Query text
            top_k: Number of documents to retrieve

        Returns:
            List of documents with scores, sorted by score (descending)
        """
        if not self.loaded:
            self.load()

        if not self.vectorizer or self.tfidf_matrix is None:
            return []

        # Vectorize query
        query_vector = self.vectorizer.transform([query])

        # Compute cosine similarity
        similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

        # Get top-k indices (sorted in descending order)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Build results with stable ordering
        results = []
        for idx in top_indices:
            doc = self.documents[int(idx)]
            score = float(similarities[int(idx)])
            results.append(
                {
                    "doc_id": doc.get("doc_id", f"doc_{idx}"),
                    "content": doc.get("content", ""),
                    "score": score,
                    "metadata": doc.get("metadata", {}),
                }
            )

        return results


class DeterministicGenerator:
    """Deterministic text generator using seeded random selection."""

    def __init__(self, seed: int, max_sentences: int = 5) -> None:
        """Initialize generator with seed."""
        self.seed = seed
        self.max_sentences = max_sentences
        self.rng = np.random.RandomState(seed)

    def generate(self, retrieved_docs: list[dict[str, Any]]) -> str:
        """
        Generate text from retrieved documents.

        Args:
            retrieved_docs: Retrieved documents with content and scores

        Returns:
            Generated text (deterministic based on seed)
        """
        if not retrieved_docs:
            return "No relevant information found."

        # Collect all content
        all_content = []
        for doc in retrieved_docs:
            content = doc.get("content", "")
            if content:
                all_content.append(content)

        if not all_content:
            return "No content available."

        # Deterministic selection based on seed
        selected_idx = self.rng.choice(len(all_content))
        selected_content = all_content[selected_idx]

        # Truncate to max sentences
        truncated = truncate_to_sentences(selected_content, self.max_sentences)

        # Add document reference
        doc_id = retrieved_docs[selected_idx].get("doc_id", "unknown")
        score = retrieved_docs[selected_idx].get("score", 0.0)

        result = f"{truncated}\n\n[Source: {doc_id}, Relevance: {score:.3f}]"

        return result

    def generate_tokens(self, text: str, max_tokens: int = 50) -> list[str]:
        """
        Generate tokens deterministically from text.

        Args:
            text: Input text
            max_tokens: Maximum tokens to generate

        Returns:
            List of tokens
        """
        words = text.split()
        if not words:
            return []

        # Deterministic token selection
        selected_tokens = []
        for _ in range(min(max_tokens, len(words))):
            idx = self.rng.choice(len(words))
            selected_tokens.append(words[idx])

        return selected_tokens
