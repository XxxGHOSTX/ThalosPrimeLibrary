#!/usr/bin/env python3
"""Build TF-IDF index from corpus documents."""

import json
import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

from configs.config import get_settings


def build_index() -> None:
    """Build TF-IDF index from corpus."""
    settings = get_settings()

    print("Building TF-IDF index...")

    # Get corpus directory
    corpus_dir = settings.get_corpus_path()

    if not corpus_dir.exists():
        print(f"Error: Corpus directory not found: {corpus_dir}")
        return

    # Read all documents
    documents = []
    doc_files = sorted(corpus_dir.glob("*.txt"))

    if not doc_files:
        print(f"Error: No .txt files found in {corpus_dir}")
        return

    print(f"Found {len(doc_files)} documents")

    for doc_file in doc_files:
        with open(doc_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            documents.append({
                "doc_id": doc_file.stem,
                "content": content,
                "metadata": {
                    "filename": doc_file.name,
                    "path": str(doc_file),
                }
            })

    print(f"Loaded {len(documents)} documents")

    # Create TF-IDF vectorizer
    vectorizer = TfidfVectorizer(
        max_features=1000,
        stop_words="english",
        ngram_range=(1, 2),
    )

    # Fit and transform documents
    corpus_texts = [doc["content"] for doc in documents]
    tfidf_matrix = vectorizer.fit_transform(corpus_texts)

    print(f"TF-IDF matrix shape: {tfidf_matrix.shape}")
    print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")

    # Save index
    index_path = settings.get_index_path()
    index_path.parent.mkdir(parents=True, exist_ok=True)

    index_data = {
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
    }

    with open(index_path, "wb") as f:
        pickle.dump(index_data, f)

    print(f"Index saved to: {index_path}")

    # Save manifest
    manifest_path = settings.get_manifest_path()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(documents, f, indent=2)

    print(f"Manifest saved to: {manifest_path}")

    print("Index build complete!")


if __name__ == "__main__":
    build_index()
