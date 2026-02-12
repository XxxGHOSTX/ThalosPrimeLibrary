"""Utility functions for Thalos Prime."""

import hashlib
import time
from typing import Optional


def generate_deterministic_seed(
    session_id: str,
    user_input: str,
    salt: str,
    time_bucket_seconds: int = 3600,
    timestamp: Optional[float] = None,
) -> int:
    """
    Generate a deterministic seed from session, input, salt, and time bucket.

    Args:
        session_id: Unique session identifier
        user_input: User input text
        salt: Salt for hashing
        time_bucket_seconds: Time bucket size in seconds (default 3600 = 1 hour)
        timestamp: Optional timestamp (defaults to current time)

    Returns:
        Deterministic seed as 32-bit integer
    """
    if timestamp is None:
        timestamp = time.time()

    # Compute time bucket
    time_bucket = int(timestamp // time_bucket_seconds)

    # Create combined string
    combined = f"{session_id}|{user_input}|{salt}|{time_bucket}"

    # Hash to get deterministic seed
    hash_obj = hashlib.sha256(combined.encode("utf-8"))
    hash_bytes = hash_obj.digest()

    # Convert first 4 bytes to unsigned 32-bit integer
    seed = int.from_bytes(hash_bytes[:4], byteorder="big", signed=False)

    # Ensure seed fits in numpy's int32 range (0 to 2^31 - 1)
    seed = seed % (2**31)

    return seed


def truncate_to_sentences(text: str, max_sentences: int) -> str:
    """
    Truncate text to maximum number of sentences.

    Args:
        text: Input text
        max_sentences: Maximum number of sentences

    Returns:
        Truncated text
    """
    if not text:
        return ""

    # Simple sentence splitting on . ! ?
    sentences = []
    current = ""

    for char in text:
        current += char
        if char in ".!?":
            sentences.append(current.strip())
            current = ""

    # Add remaining text if any
    if current.strip():
        sentences.append(current.strip())

    # Return up to max_sentences
    return " ".join(sentences[:max_sentences])


def compute_file_hash(filepath: str) -> str:
    """
    Compute SHA256 hash of a file.

    Args:
        filepath: Path to file

    Returns:
        Hex digest of file hash
    """
    hash_obj = hashlib.sha256()

    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()
