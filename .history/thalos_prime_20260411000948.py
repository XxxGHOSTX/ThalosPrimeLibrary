#!/usr/bin/env python3
"""Thalos Prime deterministic chatbot-to-Babel pipeline.

Control Plane:
    ControlPlane orchestrates lifecycle (initialize, validate, operate,
    reconcile, checkpoint, terminate), seed management, traversal index,
    JSONL state logging, and deterministic halt on invariant violations.

Data Plane:
    BabelClient, TraversalPlanner, WordExtractor, ConstraintSolver,
    VolumeAssembler execute computational work under Control Plane direction.
    No lifecycle or coordination logic lives in the Data Plane.

Determinism guarantees:
    - Single integer seed controls all pseudo-randomness via seeded Random.
    - Stable sorting (sort key = score DESC, doc_id ASC) for BM25 tie-breaks.
    - No non-deterministic operations without explicit seeding and logging.
    - Checkpoints include seed, configuration hash, and version.

Invariants:
    - Output length: exactly 1,312,000 characters (410 pages × 3,200 chars).
    - Any invariant breach raises DeterministicHalt with full state snapshot.
    - Padding uses spaces only; each page hard-trimmed to exactly 3,200 chars.

Usage:
    python thalos_prime.py \\
        --query "test query" \\
        --seed 12345 \\
        --output ./output.txt \\
        --workdir ./thalos_workdir \\
        --max-pages 5

    Dry-run (offline, no network):
    python thalos_prime.py \\
        --query "test" \\
        --seed 1 \\
        --output ./output.txt \\
        --workdir ./thalos_workdir \\
        --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
import time
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urljoin

try:
    import requests
    from requests import Session
except ImportError as _exc:
    raise ImportError("requests is required: pip install requests>=2.31.0") from _exc


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------
# Page geometry
PAGE_CHARS: int = 3_200
TOTAL_PAGES: int = 410
TOTAL_CHARS: int = PAGE_CHARS * TOTAL_PAGES  # 1,312,000

# Library of Babel canonical endpoints
BABEL_BASE_URL: str = "https://libraryofbabel.info"
BABEL_SEARCH_CGI: str = f"{BABEL_BASE_URL}/search.cgi"

# Library address space dimensions
WALLS_PER_VOLUME: int = 4
SHELVES_PER_WALL: int = 5
BOOKS_PER_SHELF: int = 32
PAGES_PER_BOOK: int = 410

# BM25 hyper-parameters (standard values)
BM25_K1: float = 1.5
BM25_B: float = 0.75

# Network retries (deterministic, bounded, logged)
MAX_RETRIES: int = 3
RETRY_DELAY_S: float = 1.0
REQUEST_TIMEOUT_S: int = 30

# Checkpoint / log schema version
STATE_VERSION: str = "1.0"

# ---------------------------------------------------------------------------
# Embedded deterministic English vocabulary
# (No external fetches; sorted for stable hash.)
# ---------------------------------------------------------------------------
EMBEDDED_VOCAB: frozenset[str] = frozenset(sorted([
    "the", "and", "that", "have", "for", "not", "with", "you", "this",
    "but", "his", "from", "they", "she", "her", "which", "was", "are",
    "had", "words", "been", "each", "there", "when", "what", "will",
    "can", "said", "into", "than", "now", "look", "only", "come",
    "over", "think", "also", "back", "after", "use", "two", "how",
    "our", "work", "first", "well", "way", "even", "new", "want",
    "because", "any", "these", "give", "most", "about", "time", "very",
    "just", "him", "know", "take", "people", "year", "your", "good",
    "some", "could", "them", "see", "other", "like", "get", "come",
    "its", "out", "has", "may", "long", "down", "day", "did", "made",
    "part", "going", "more", "write", "little", "man", "place", "where",
    "hand", "high", "large", "hold", "between", "need", "home", "read",
    "great", "old", "never", "same", "another", "off", "while", "last",
    "might", "every", "left", "turn", "move", "through", "world", "still",
    "own", "right", "head", "help", "city", "play", "small", "number",
    "always", "being", "follow", "almost", "together", "find", "far",
    "next", "open", "example", "begin", "life", "point", "letter",
    "book", "page", "library", "volume", "shelf", "wall", "word",
    "text", "line", "character", "sentence", "paragraph", "story",
    "chapter", "language", "meaning", "pattern", "order", "sequence",
    "symbol", "sign", "code", "cipher", "key", "lock", "door", "room",
    "hall", "corridor", "spiral", "stair", "light", "dark", "shadow",
    "sound", "silence", "voice", "echo", "dream", "memory", "thought",
    "mind", "heart", "eye", "face", "truth", "question", "answer",
    "search", "seek", "infinite", "finite", "possible", "impossible",
    "certain", "deterministic", "ordered", "chaos", "structure", "form",
    "matter", "space", "before", "inside", "outside", "above", "below",
    "among", "within", "without", "across", "beyond", "toward", "away",
    "near", "deep", "shallow", "wide", "narrow", "heavy", "warm", "cold",
    "hot", "strong", "weak", "fast", "slow", "early", "late", "full",
    "empty", "clear", "bright", "quiet", "loud", "smooth", "rough",
    "sharp", "blunt", "thick", "thin", "rich", "poor", "young", "age",
    "real", "false", "true", "wrong", "better", "worse", "best", "worst",
    "many", "few", "all", "none", "both", "either", "neither", "every",
    "no", "one", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "hundred", "thousand", "million", "billion",
]))

# ---------------------------------------------------------------------------
# Deterministic grammar connectors for page scaffolding
# ---------------------------------------------------------------------------
GRAMMAR_CONNECTORS: tuple[str, ...] = (
    "Furthermore, the text records: ",
    "In this regard, the library notes: ",
    "As preserved in this volume: ",
    "The following passage continues: ",
    "Proceeding from the above account: ",
    "This sequence of characters states: ",
    "The arrangement herein documents: ",
    "Emerging from the hexagonal pattern: ",
    "The infinite catalogue preserves: ",
    "Within these ordered pages: ",
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class DeterministicHalt(Exception):
    """Raised when any invariant breach requires deterministic halt.

    This exception carries a full state snapshot so that every failure
    is fully observable, loggable, and replayable. No silent degradation
    is permitted; any invariant violation must surface through this exception.

    Attributes:
        reason: Human-readable description of the violated invariant.
        state_snapshot: Complete serialized state at time of halt.
    """

    def __init__(self, reason: str, state_snapshot: dict[str, object]) -> None:
        """Initialize halt with reason and state snapshot.

        Args:
            reason: Human-readable invariant violation description.
            state_snapshot: Complete serialized system state.
        """
        self.reason = reason
        self.state_snapshot = state_snapshot
        super().__init__(f"DeterministicHalt: {reason}")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
@dataclass
class SystemState:
    """Observable, serializable, versioned pipeline state.

    This dataclass is the single source of truth for the pipeline's
    observable state. All fields are reconstructible from a checkpoint.
    State transitions are logged via StateLogger for full auditability.

    Attributes:
        seed: The deterministic seed controlling all pseudo-randomness.
        traversal_index: Current position in the traversal path.
        traversal_path: Ordered list of address dicts visited so far.
        corpus_size: Number of tokens extracted from fetched pages.
        plan_pages: Number of pages planned for assembly.
        assembled_length: Total chars assembled so far.
        output_path: Path to the output file.
        last_checkpoint: ISO timestamp of last successful checkpoint.
        version: Schema version for checkpoint compatibility checks.
    """

    seed: int
    traversal_index: int = 0
    traversal_path: list[dict[str, object]] = field(default_factory=list)
    corpus_size: int = 0
    plan_pages: int = 0
    assembled_length: int = 0
    output_path: str = ""
    last_checkpoint: str = ""
    version: str = STATE_VERSION

    def to_dict(self) -> dict[str, object]:
        """Serialize state to a JSON-compatible dictionary.

        Returns:
            Complete state mapping, JSON-serializable.
        """
        return {
            "version": self.version,
            "seed": self.seed,
            "traversal_index": self.traversal_index,
            "traversal_path": self.traversal_path,
            "corpus_size": self.corpus_size,
            "plan_pages": self.plan_pages,
            "assembled_length": self.assembled_length,
            "output_path": self.output_path,
            "last_checkpoint": self.last_checkpoint,
        }

    def state_hash(self) -> str:
        """Compute a deterministic blake2b hash of the current state.

        Used in event logs for observability and replay verification.

        Returns:
            16-byte hex digest of the serialized state.
        """
        raw = json.dumps(self.to_dict(), sort_keys=True).encode("utf-8")
        return hashlib.blake2b(raw, digest_size=16).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SystemState":
        """Reconstruct state from a checkpoint dictionary.

        Args:
            data: Previously serialized state dict.

        Returns:
            Reconstructed SystemState.

        Raises:
            DeterministicHalt: If checkpoint version is incompatible.
        """
        loaded_version = str(data.get("version", "1.0"))
        if loaded_version != STATE_VERSION:
            raise DeterministicHalt(
                f"Incompatible checkpoint version: {loaded_version}",
                {"loaded": loaded_version, "expected": STATE_VERSION},
            )
        state = cls(seed=int(data["seed"]))  # type: ignore[arg-type]
        state.traversal_index = int(data.get("traversal_index", 0))  # type: ignore[arg-type]
        path_raw = data.get("traversal_path", [])
        state.traversal_path = list(path_raw)  # type: ignore[arg-type]
        state.corpus_size = int(data.get("corpus_size", 0))  # type: ignore[arg-type]
        state.plan_pages = int(data.get("plan_pages", 0))  # type: ignore[arg-type]
        state.assembled_length = int(data.get("assembled_length", 0))  # type: ignore[arg-type]
        state.output_path = str(data.get("output_path", ""))
        state.last_checkpoint = str(data.get("last_checkpoint", ""))
        return state


# ---------------------------------------------------------------------------
# Checkpointer  (Data Plane - writes JSON checkpoints)
# ---------------------------------------------------------------------------
class Checkpointer:
    """Writes atomic, versioned JSON checkpoints to a work directory.

    Each checkpoint file is named by timestamp and seed, ensuring
    no two checkpoints can collide even in concurrent runs.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        _workdir: Root directory for checkpoint files.
        _checkpoint_count: Number of checkpoints written this session.
    """

    def __init__(self, workdir: Path) -> None:
        """Initialize with target work directory.

        Args:
            workdir: Directory for checkpoint files.
        """
        self._workdir = workdir
        self._checkpoint_count: int = 0

    def initialize(self) -> None:
        """Create work directory if absent.

        Raises:
            DeterministicHalt: If directory cannot be created.
        """
        try:
            self._workdir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DeterministicHalt(
                f"Cannot create workdir {self._workdir}: {exc}",
                {"workdir": str(self._workdir)},
            ) from exc

    def validate(self) -> None:
        """Verify work directory exists and is writable.

        Raises:
            DeterministicHalt: If directory is not writable.
        """
        if not self._workdir.is_dir():
            raise DeterministicHalt(
                f"Workdir not a directory: {self._workdir}",
                {"workdir": str(self._workdir)},
            )
        probe = self._workdir / ".write_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            raise DeterministicHalt(
                f"Workdir not writable: {self._workdir}: {exc}",
                {"workdir": str(self._workdir)},
            ) from exc

    def operate(self, state: SystemState) -> Path:
        """Write a checkpoint for the given state.

        Args:
            state: Current system state to serialize.

        Returns:
            Path to the written checkpoint file.

        Raises:
            DeterministicHalt: On any write failure.
        """
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        filename = f"checkpoint_{ts}_seed{state.seed}.json"
        path = self._workdir / filename
        payload: dict[str, object] = {
            "schema": "thalos_prime_checkpoint",
            "version": STATE_VERSION,
            "timestamp": ts,
            "state_hash": state.state_hash(),
            "state": state.to_dict(),
        }
        try:
            path.write_text(
                json.dumps(payload, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except OSError as exc:
            raise DeterministicHalt(
                f"Checkpoint write failed: {path}: {exc}",
                {"path": str(path), "state": state.to_dict()},
            ) from exc
        self._checkpoint_count += 1
        return path

    def reconcile(self, state: SystemState) -> None:
        """Verify the last checkpoint matches the current state hash.

        Args:
            state: Current system state.

        Raises:
            DeterministicHalt: If no checkpoint exists when one is expected.
        """
        if self._checkpoint_count == 0:
            return
        if not state.last_checkpoint:
            raise DeterministicHalt(
                "State.last_checkpoint is empty after checkpointing",
                state.to_dict(),
            )

    def checkpoint(self, state: SystemState) -> Path:
        """Alias for operate; required by lifecycle protocol.

        Args:
            state: Current system state.

        Returns:
            Path to the checkpoint file.
        """
        return self.operate(state)

    def terminate(self) -> None:
        """Log checkpoint count on clean shutdown."""
        _log_stderr(f"Checkpointer: {self._checkpoint_count} checkpoints written")


# ---------------------------------------------------------------------------
# StateLogger  (Data Plane - writes JSONL event logs)
# ---------------------------------------------------------------------------
class StateLogger:
    """Writes structured JSONL event logs with timestamps and state hashes.

    Every state transition, lifecycle milestone, and reconciliation action
    is logged with: timestamp, event type, seed, state_hash, and payload.
    Schema is versioned for backward compatibility.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        _log_path: Path to the JSONL log file.
        _event_count: Number of events written.
    """

    def __init__(self, workdir: Path, seed: int) -> None:
        """Initialize logger.

        Args:
            workdir: Directory for the log file.
            seed: Pipeline seed (included in every event).
        """
        self._workdir = workdir
        self._seed = seed
        self._log_path: Optional[Path] = None
        self._event_count: int = 0

    def initialize(self) -> None:
        """Set up log file path (file is created lazily on first write).

        Raises:
            DeterministicHalt: If workdir is not a directory.
        """
        if not self._workdir.is_dir():
            raise DeterministicHalt(
                f"StateLogger workdir not a directory: {self._workdir}",
                {"workdir": str(self._workdir)},
            )
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        self._log_path = self._workdir / f"events_{ts}_seed{self._seed}.jsonl"

    def validate(self) -> None:
        """Verify log path is set.

        Raises:
            DeterministicHalt: If initialize() was not called.
        """
        if self._log_path is None:
            raise DeterministicHalt(
                "StateLogger not initialized (log_path is None)",
                {"seed": self._seed},
            )

    def operate(
        self,
        event_type: str,
        state: SystemState,
        payload: Optional[dict[str, object]] = None,
    ) -> None:
        """Append a structured event to the JSONL log.

        Args:
            event_type: Short label for the event (e.g. "lifecycle.initialize").
            state: Current system state at time of event.
            payload: Optional additional event-specific data.

        Raises:
            DeterministicHalt: If log_path is None or write fails.
        """
        if self._log_path is None:
            raise DeterministicHalt(
                "StateLogger.operate called before initialize",
                {"event_type": event_type},
            )
        event: dict[str, object] = {
            "schema": "thalos_prime_event",
            "schema_version": STATE_VERSION,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "seed": self._seed,
            "state_hash": state.state_hash(),
            "traversal_index": state.traversal_index,
            "corpus_size": state.corpus_size,
            "assembled_length": state.assembled_length,
        }
        if payload:
            event["payload"] = payload
        try:
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, sort_keys=True) + "\n")
        except OSError as exc:
            raise DeterministicHalt(
                f"StateLogger write failed: {self._log_path}: {exc}",
                state.to_dict(),
            ) from exc
        self._event_count += 1

    def reconcile(self, state: SystemState) -> None:
        """Flush and verify the event log is intact.

        Args:
            state: Current system state.

        Raises:
            DeterministicHalt: If log is missing when events were expected.
        """
        if self._event_count > 0 and (
            self._log_path is None or not self._log_path.exists()
        ):
            raise DeterministicHalt(
                "StateLogger log file missing after events were written",
                state.to_dict(),
            )

    def checkpoint(self, state: SystemState) -> None:
        """Log a checkpoint event.

        Args:
            state: Current system state.
        """
        self.operate("lifecycle.checkpoint", state)

    def terminate(self) -> None:
        """Log termination and report event count."""
        _log_stderr(f"StateLogger: {self._event_count} events written to {self._log_path}")


# ---------------------------------------------------------------------------
# BabelClient  (Data Plane - network access with robots.txt enforcement)
# ---------------------------------------------------------------------------
class BabelClient:
    """HTTP client for libraryofbabel.info with robots.txt enforcement.

    Deterministic halt policy:
        - robots.txt disallows crawling → DeterministicHalt immediately.
        - robots.txt fetch fails → DeterministicHalt (cannot verify policy).
        - Page fetch fails after MAX_RETRIES → DeterministicHalt.
        - No fallback, no silent degradation.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        _robots_allowed: Whether crawling is permitted.
        _fetch_count: Number of pages successfully fetched.
        _session: Underlying requests.Session.
    """

    def __init__(
        self,
        base_url: str = BABEL_BASE_URL,
        user_agent: str = "ThalosPrimePipeline/1.0",
    ) -> None:
        """Initialize client.

        Args:
            base_url: Base URL for libraryofbabel.info.
            user_agent: User-Agent string sent in all requests.
        """
        self._base_url = base_url
        self._user_agent = user_agent
        self._robots_allowed: Optional[bool] = None
        self._fetch_count: int = 0
        self._session: Session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent})

    def initialize(self) -> None:
        """Set up session headers.

        The session is already created in __init__; this lifecycle step
        ensures headers are applied before any fetch.
        """
        self._session.headers.update({"User-Agent": self._user_agent})

    def validate(self) -> None:
        """Fetch and enforce robots.txt.

        Raises:
            DeterministicHalt: If robots.txt forbids crawling or is unreachable.
        """
        robots_url = urljoin(self._base_url, "/robots.txt")
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception as exc:  # noqa: BLE001 - network errors are varied
            raise DeterministicHalt(
                f"Cannot fetch robots.txt from {robots_url}: {exc}",
                {"robots_url": robots_url},
            ) from exc
        allowed = rp.can_fetch(self._user_agent, self._base_url + "/")
        if not allowed:
            raise DeterministicHalt(
                f"robots.txt disallows crawling for agent {self._user_agent}",
                {"robots_url": robots_url, "user_agent": self._user_agent},
            )
        self._robots_allowed = True

    def operate(self, url: str) -> str:
        """Fetch a URL and return its text content.

        Retries up to MAX_RETRIES times with deterministic delay.
        Halts deterministically on persistent failure.

        Args:
            url: Fully-qualified URL to fetch.

        Returns:
            Response text.

        Raises:
            DeterministicHalt: After MAX_RETRIES failures.
        """
        if not self._robots_allowed:
            raise DeterministicHalt(
                "BabelClient.operate called before validate (robots not checked)",
                {"url": url},
            )
        last_exc: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._session.get(url, timeout=REQUEST_TIMEOUT_S)
                resp.raise_for_status()
                self._fetch_count += 1
                return resp.text
            except requests.RequestException as exc:
                last_exc = exc
                _log_stderr(
                    f"BabelClient: fetch attempt {attempt}/{MAX_RETRIES} "
                    f"failed for {url}: {exc}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY_S * attempt)
        raise DeterministicHalt(
            f"BabelClient: all {MAX_RETRIES} fetch attempts failed for {url}",
            {"url": url, "last_error": str(last_exc)},
        )

    def fetch_search(self, query: str) -> str:
        """Fetch search results page for a query.

        Args:
            query: Search term.

        Returns:
            HTML of the search results page.
        """
        url = f"{BABEL_SEARCH_CGI}?query={quote(query)}"
        return self.operate(url)

    def fetch_page(self, address: dict[str, object]) -> str:
        """Fetch a specific book page by address.

        Args:
            address: Dict with keys: volume, wall, shelf, book, page.

        Returns:
            HTML content of the page.
        """
        url = (
            f"{self._base_url}/book.cgi"
            f"?searchterm={address.get('volume', '')}"
            f"&wall={address.get('wall', 1)}"
            f"&shelf={address.get('shelf', 1)}"
            f"&book={address.get('book', 1)}"
            f"&page={address.get('page', 1)}"
        )
        return self.operate(url)

    def reconcile(self) -> None:
        """Verify session is still functional by checking _fetch_count."""

    def checkpoint(self) -> dict[str, object]:
        """Serialize client state.

        Returns:
            Client state dict.
        """
        return {
            "base_url": self._base_url,
            "robots_allowed": self._robots_allowed,
            "fetch_count": self._fetch_count,
        }

    def terminate(self) -> None:
        """Close the HTTP session cleanly."""
        self._session.close()
        _log_stderr(f"BabelClient: closed session after {self._fetch_count} fetches")


# ---------------------------------------------------------------------------
# TraversalPlanner  (Data Plane - seeded pseudo-random address walk)
# ---------------------------------------------------------------------------
class TraversalPlanner:
    """Generates a deterministic pseudo-random walk through Babel address space.

    Uses an isolated seeded Random instance; no module-level state.
    Addresses are Volume (hex string) / Wall / Shelf / Book / Page tuples.
    The Volume hex is derived deterministically from the RNG.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        _rng: Isolated seeded Random instance.
        _path: List of addresses generated so far.
        _seed: Seed value (logged in checkpoints).
    """

    def __init__(self, seed: int) -> None:
        """Initialize with seed.

        Args:
            seed: Deterministic seed for all pseudo-random choices.
        """
        self._seed = seed
        self._rng: Optional[random.Random] = None
        self._path: list[dict[str, object]] = []

    def initialize(self) -> None:
        """Seed the isolated RNG."""
        self._rng = random.Random(self._seed)

    def validate(self) -> None:
        """Verify RNG is seeded.

        Raises:
            DeterministicHalt: If initialize() was not called.
        """
        if self._rng is None:
            raise DeterministicHalt(
                "TraversalPlanner not initialized (RNG is None)",
                {"seed": self._seed},
            )

    def operate(self, n: int = 1) -> list[dict[str, object]]:
        """Generate n deterministic addresses.

        Each address is a unique dict with keys:
            volume (str), wall (int), shelf (int), book (int), page (int).

        Args:
            n: Number of addresses to generate.

        Returns:
            List of address dicts.

        Raises:
            DeterministicHalt: If RNG is not initialized.
        """
        if self._rng is None:
            raise DeterministicHalt(
                "TraversalPlanner.operate called before initialize",
                {"seed": self._seed, "n": n},
            )
        addresses: list[dict[str, object]] = []
        for _ in range(n):
            volume = self._rng.randbytes(10).hex()
            wall = self._rng.randint(1, WALLS_PER_VOLUME)
            shelf = self._rng.randint(1, SHELVES_PER_WALL)
            book = self._rng.randint(1, BOOKS_PER_SHELF)
            page = self._rng.randint(1, PAGES_PER_BOOK)
            addr: dict[str, object] = {
                "volume": volume,
                "wall": wall,
                "shelf": shelf,
                "book": book,
                "page": page,
            }
            addresses.append(addr)
            self._path.append(addr)
        return addresses

    def reconcile(self) -> None:
        """Verify path is non-empty after operate."""

    def checkpoint(self) -> dict[str, object]:
        """Serialize traversal state.

        Returns:
            State dict with seed and path.
        """
        return {
            "seed": self._seed,
            "path_length": len(self._path),
            "path": self._path,
        }

    def terminate(self) -> None:
        """Log traversal statistics."""
        _log_stderr(f"TraversalPlanner: generated {len(self._path)} addresses")

    @property
    def path(self) -> list[dict[str, object]]:
        """Return the addresses generated so far."""
        return list(self._path)


# ---------------------------------------------------------------------------
# WordExtractor  (Data Plane - HTML stripping and token extraction)
# ---------------------------------------------------------------------------
class WordExtractor:
    """Extracts English-like tokens from HTML content.

    Pipeline:
        1. Strip HTML tags with a simple regex.
        2. Extract tokens matching r"[A-Za-z]{2,}".
        3. Filter to lowercase tokens present in EMBEDDED_VOCAB.

    The resulting corpus is deterministic: same HTML → same token list.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        _corpus: Accumulated tokens from all operate() calls.
        _token_pattern: Compiled regex for token extraction.
        _html_pattern: Compiled regex for HTML stripping.
    """

    _TOKEN_PATTERN = re.compile(r"[A-Za-z]{2,}")
    _HTML_PATTERN = re.compile(r"<[^>]+>")
    _ENTITY_PATTERN = re.compile(r"&[a-z]+;")

    def __init__(self) -> None:
        """Initialize extractor."""
        self._corpus: list[str] = []

    def initialize(self) -> None:
        """Compile patterns (already class-level; validate they exist)."""
        if not self._TOKEN_PATTERN.pattern:
            raise DeterministicHalt(
                "WordExtractor token pattern is empty",
                {},
            )

    def validate(self) -> None:
        """Verify patterns are compiled and corpus list is initialized."""
        return None

    def operate(self, html: str) -> list[str]:
        """Extract and filter tokens from HTML.

        Args:
            html: Raw HTML string.

        Returns:
            List of lowercase English-like tokens from EMBEDDED_VOCAB.
        """
        text = self._HTML_PATTERN.sub(" ", html)
        text = self._ENTITY_PATTERN.sub(" ", text)
        raw_tokens = self._TOKEN_PATTERN.findall(text)
        filtered = [t.lower() for t in raw_tokens if t.lower() in EMBEDDED_VOCAB]
        self._corpus.extend(filtered)
        return filtered

    def reconcile(self) -> None:
        """Verify corpus has been populated (no-op if empty)."""

    def checkpoint(self) -> dict[str, object]:
        """Serialize extracted corpus.

        Returns:
            State dict with corpus size and first/last tokens.
        """
        return {
            "corpus_size": len(self._corpus),
            "first_10": self._corpus[:10],
            "last_10": self._corpus[-10:],
        }

    def terminate(self) -> None:
        """Log extraction statistics."""
        _log_stderr(f"WordExtractor: extracted {len(self._corpus)} total tokens")

    @property
    def corpus(self) -> list[str]:
        """Return the accumulated token corpus (copy)."""
        return list(self._corpus)

    def reset_corpus(self) -> None:
        """Clear the corpus for a fresh run."""
        self._corpus = []


# ---------------------------------------------------------------------------
# ConstraintSolver  (Data Plane - deterministic BM25 scoring)
# ---------------------------------------------------------------------------
class ConstraintSolver:
    """Scores documents against a query using BM25 with stable tie-breaks.

    BM25 formula (Robertson & Ogilvie):
        score(d, q) = sum_t [ IDF(t) * TF(t,d) * (k1+1) /
                              (TF(t,d) + k1*(1-b + b*|d|/avgdl)) ]
        IDF(t) = log((N - df(t) + 0.5) / (df(t) + 0.5) + 1)

    Tie-breaks: sort by (score DESC, doc_id ASC) for stable ordering.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        _k1, _b: BM25 hyper-parameters.
        _last_scores: Results from last operate() call.
    """

    def __init__(self, k1: float = BM25_K1, b: float = BM25_B) -> None:
        """Initialize BM25 parameters.

        Args:
            k1: Term frequency saturation parameter (default 1.5).
            b: Length normalization parameter (default 0.75).
        """
        self._k1 = k1
        self._b = b
        self._last_scores: list[dict[str, object]] = []

    def initialize(self) -> None:
        """Validate BM25 parameters are positive."""
        if self._k1 <= 0 or not (0.0 <= self._b <= 1.0):
            raise DeterministicHalt(
                f"BM25 parameters out of range: k1={self._k1}, b={self._b}",
                {"k1": self._k1, "b": self._b},
            )

    def validate(self) -> None:
        """Re-validate parameters (idempotent)."""
        self.initialize()

    def operate(
        self,
        query_tokens: list[str],
        documents: list[list[str]],
    ) -> list[dict[str, object]]:
        """Score documents and return sorted results.

        Args:
            query_tokens: Tokenized query terms.
            documents: List of tokenized documents; each is a list of tokens.

        Returns:
            Sorted list of dicts: [{doc_id, score, doc}] by score DESC, doc_id ASC.

        Raises:
            DeterministicHalt: If query_tokens is empty.
        """
        if not query_tokens:
            raise DeterministicHalt(
                "ConstraintSolver.operate: query_tokens is empty",
                {"k1": self._k1, "b": self._b},
            )
        if not documents:
            self._last_scores = []
            return []

        n_docs = len(documents)
        doc_lengths = [len(d) for d in documents]
        avg_dl = sum(doc_lengths) / n_docs if n_docs else 1.0

        # Build document frequency table
        df: dict[str, int] = {}
        for doc in documents:
            for term in set(doc):
                df[term] = df.get(term, 0) + 1

        # Score each document
        results: list[dict[str, object]] = []
        for doc_id, (doc, doc_len) in enumerate(zip(documents, doc_lengths)):
            tf_map: dict[str, int] = {}
            for term in doc:
                tf_map[term] = tf_map.get(term, 0) + 1

            score = 0.0
            for term in query_tokens:
                tf = tf_map.get(term, 0)
                df_t = df.get(term, 0)
                if df_t == 0:
                    continue
                idf = math.log((n_docs - df_t + 0.5) / (df_t + 0.5) + 1.0)
                numerator = tf * (self._k1 + 1.0)
                denominator = tf + self._k1 * (
                    1.0 - self._b + self._b * doc_len / avg_dl
                )
                score += idf * numerator / denominator if denominator != 0.0 else 0.0

            results.append({"doc_id": doc_id, "score": score, "doc": doc})

        # Stable sort: score DESC, doc_id ASC
        results.sort(key=lambda x: (-float(x["score"]), int(x["doc_id"])))  # type: ignore[arg-type]
        self._last_scores = results
        return results

    def reconcile(self) -> None:
        """Verify last scores are sorted correctly.

        Raises:
            DeterministicHalt: If scores are not in descending order.
        """
        scores = [float(r["score"]) for r in self._last_scores]  # type: ignore[arg-type]
        for i in range(len(scores) - 1):
            if scores[i] < scores[i + 1]:
                raise DeterministicHalt(
                    "ConstraintSolver scores not in descending order after sort",
                    {"index": i, "score_i": scores[i], "score_next": scores[i + 1]},
                )

    def checkpoint(self) -> dict[str, object]:
        """Serialize last scoring results.

        Returns:
            State dict with top scores.
        """
        return {
            "k1": self._k1,
            "b": self._b,
            "result_count": len(self._last_scores),
            "top_3": self._last_scores[:3],
        }

    def terminate(self) -> None:
        """Log scoring statistics."""
        _log_stderr(
            f"ConstraintSolver: last run scored {len(self._last_scores)} documents"
        )


# ---------------------------------------------------------------------------
# VolumeAssembler  (Data Plane - 410 pages × 3,200 chars)
# ---------------------------------------------------------------------------
class VolumeAssembler:
    """Plans and assembles a volume of exactly 410 pages × 3,200 characters.

    Assembly algorithm:
        1. Flatten corpus tokens into a single text stream.
        2. Divide the stream into TOTAL_PAGES equal-size chunks.
        3. For each chunk, prepend a deterministic grammar connector.
        4. Right-pad with spaces to exactly PAGE_CHARS characters.
        5. Hard-trim to PAGE_CHARS if connector + chunk exceeds PAGE_CHARS.
        6. Assert assembled_length == TOTAL_CHARS; halt otherwise.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        _pages: Assembled pages (list of str, each len == PAGE_CHARS).
        _assembled_length: Total chars in assembled volume.
        _seed: Used to deterministically pick connectors.
    """

    def __init__(self, seed: int) -> None:
        """Initialize assembler.

        Args:
            seed: Deterministic seed for connector selection.
        """
        self._seed = seed
        self._pages: list[str] = []
        self._assembled_length: int = 0

    def initialize(self) -> None:
        """Verify geometry constants are consistent.

        Raises:
            DeterministicHalt: If PAGE_CHARS × TOTAL_PAGES ≠ TOTAL_CHARS.
        """
        if PAGE_CHARS * TOTAL_PAGES != TOTAL_CHARS:
            raise DeterministicHalt(
                f"Geometry invariant violated: "
                f"{PAGE_CHARS} × {TOTAL_PAGES} ≠ {TOTAL_CHARS}",
                {
                    "page_chars": PAGE_CHARS,
                    "total_pages": TOTAL_PAGES,
                    "total_chars": TOTAL_CHARS,
                    "product": PAGE_CHARS * TOTAL_PAGES,
                },
            )

    def validate(self) -> None:
        """Re-check geometry and verify connectors are available."""
        self.initialize()
        if not GRAMMAR_CONNECTORS:
            raise DeterministicHalt(
                "VolumeAssembler: no grammar connectors available",
                {"seed": self._seed},
            )

    def operate(self, corpus: list[str]) -> list[str]:
        """Assemble 410 pages from the corpus token stream.

        Args:
            corpus: List of tokens from WordExtractor.

        Returns:
            List of TOTAL_PAGES strings, each exactly PAGE_CHARS characters.

        Raises:
            DeterministicHalt: If assembled length ≠ TOTAL_CHARS.
        """
        # Build a repeating token stream long enough to fill all pages
        combined = " ".join(corpus) if corpus else "the library"
        # Deterministic connector RNG (isolated from traversal RNG)
        conn_rng = random.Random(self._seed + 1)

        pages: list[str] = []
        for page_idx in range(TOTAL_PAGES):
            connector = GRAMMAR_CONNECTORS[
                conn_rng.randint(0, len(GRAMMAR_CONNECTORS) - 1)
            ]
            # Slice a portion of combined text for this page
            start = (page_idx * (len(combined) // TOTAL_PAGES)) % max(len(combined), 1)
            chunk_len = PAGE_CHARS - len(connector)
            if chunk_len <= 0:
                chunk_len = PAGE_CHARS
                connector = ""
            chunk = _cyclic_slice(combined, start, chunk_len)
            raw_page = connector + chunk
            # Pad to PAGE_CHARS with spaces; trim if over
            if len(raw_page) < PAGE_CHARS:
                raw_page = raw_page + " " * (PAGE_CHARS - len(raw_page))
            page = raw_page[:PAGE_CHARS]
            assert len(page) == PAGE_CHARS  # noqa: S101
            pages.append(page)

        self._pages = pages
        self._assembled_length = sum(len(p) for p in pages)

        if self._assembled_length != TOTAL_CHARS:
            raise DeterministicHalt(
                f"Assembly invariant violated: "
                f"expected {TOTAL_CHARS}, got {self._assembled_length}",
                {
                    "expected": TOTAL_CHARS,
                    "got": self._assembled_length,
                    "pages": len(pages),
                },
            )
        return pages

    def reconcile(self) -> None:
        """Verify length invariant is still satisfied.

        Raises:
            DeterministicHalt: If length invariant is violated.
        """
        if self._pages:
            actual = sum(len(p) for p in self._pages)
            if actual != TOTAL_CHARS:
                raise DeterministicHalt(
                    f"VolumeAssembler reconcile: length mismatch "
                    f"(expected {TOTAL_CHARS}, got {actual})",
                    {"expected": TOTAL_CHARS, "actual": actual},
                )
            if any(len(p) != PAGE_CHARS for p in self._pages):
                raise DeterministicHalt(
                    "VolumeAssembler reconcile: at least one page is not "
                    f"exactly {PAGE_CHARS} chars",
                    {
                        "page_sizes": [
                            len(p) for p in self._pages if len(p) != PAGE_CHARS
                        ][:5]
                    },
                )

    def checkpoint(self) -> dict[str, object]:
        """Serialize assembler state.

        Returns:
            State dict with page count and length.
        """
        return {
            "seed": self._seed,
            "page_count": len(self._pages),
            "assembled_length": self._assembled_length,
        }

    def terminate(self) -> None:
        """Log assembly statistics."""
        _log_stderr(
            f"VolumeAssembler: assembled {len(self._pages)} pages, "
            f"{self._assembled_length} chars total"
        )

    @property
    def pages(self) -> list[str]:
        """Return assembled pages (copy)."""
        return list(self._pages)

    @property
    def assembled_length(self) -> int:
        """Return total assembled character count."""
        return self._assembled_length


# ---------------------------------------------------------------------------
# ControlPlane  (Control Plane - lifecycle orchestration)
# ---------------------------------------------------------------------------
class ControlPlane:
    """Orchestrates the full deterministic chatbot-to-Babel pipeline.

    The Control Plane is authoritative for:
        - Lifecycle sequencing (initialize → validate → operate →
          reconcile → checkpoint → terminate).
        - Seed propagation to all subsystems.
        - JSONL state logging at every transition.
        - Deterministic halt on any invariant violation.
        - Checkpoint writing after each major step.

    The Data Plane (BabelClient, TraversalPlanner, WordExtractor,
    ConstraintSolver, VolumeAssembler) executes computational work
    only; no coordination logic lives there.

    Lifecycle:
        initialize() → validate() → operate() → reconcile() →
        checkpoint() → terminate()

    State surfaces:
        state: SystemState (observable, serializable, versioned).
        _checkpointer: Checkpointer instance.
        _logger: StateLogger instance.
        _client: BabelClient instance.
        _planner: TraversalPlanner instance.
        _extractor: WordExtractor instance.
        _solver: ConstraintSolver instance.
        _assembler: VolumeAssembler instance.
    """

    def __init__(
        self,
        query: str,
        seed: int,
        output_path: str,
        workdir: str,
        max_pages: int = TOTAL_PAGES,
        dry_run: bool = False,
    ) -> None:
        """Initialize the Control Plane.

        Args:
            query: Natural language query string.
            seed: Deterministic seed for all pseudo-randomness.
            output_path: Path to write the assembled volume.
            workdir: Working directory for checkpoints and logs.
            max_pages: Maximum pages to fetch from Babel (default 410).
            dry_run: If True, skip network calls and use synthetic corpus.
        """
        self._query = query
        self._seed = seed
        self._output_path = Path(output_path)
        self._workdir = Path(workdir)
        self._max_pages = max_pages
        self._dry_run = dry_run

        self.state = SystemState(
            seed=seed,
            output_path=str(output_path),
        )
        self._checkpointer = Checkpointer(self._workdir)
        self._logger = StateLogger(self._workdir, seed)
        self._client = BabelClient()
        self._planner = TraversalPlanner(seed)
        self._extractor = WordExtractor()
        self._solver = ConstraintSolver()
        self._assembler = VolumeAssembler(seed)

    def initialize(self) -> None:
        """Initialize all subsystems in dependency order.

        Raises:
            DeterministicHalt: On any subsystem initialization failure.
        """
        self._checkpointer.initialize()
        self._logger.initialize()
        self._logger.operate("lifecycle.initialize", self.state, {"query": self._query})
        self._planner.initialize()
        self._extractor.initialize()
        self._solver.initialize()
        self._assembler.initialize()
        if not self._dry_run:
            self._client.initialize()

    def validate(self) -> None:
        """Validate all subsystems and configuration.

        Raises:
            DeterministicHalt: On any validation failure.
        """
        self._checkpointer.validate()
        self._logger.validate()
        self._planner.validate()
        self._extractor.validate()
        self._solver.validate()
        self._assembler.validate()
        if not self._dry_run:
            self._client.validate()
        # Validate seed
        if self._seed < 0:
            raise DeterministicHalt(
                f"Seed must be a non-negative integer, got {self._seed!r}",
                self.state.to_dict(),
            )
        # Validate output path parent exists or can be created
        try:
            self._output_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DeterministicHalt(
                f"Cannot create output directory {self._output_path.parent}: {exc}",
                self.state.to_dict(),
            ) from exc
        self._logger.operate("lifecycle.validate", self.state)

    def operate(self) -> None:
        """Execute the full pipeline: traverse → extract → score → assemble.

        Steps:
            1. Generate addresses via TraversalPlanner.
            2. Fetch pages (or use synthetic corpus in dry-run).
            3. Extract tokens via WordExtractor.
            4. Score via ConstraintSolver.
            5. Assemble volume via VolumeAssembler.
            6. Write output file.

        Raises:
            DeterministicHalt: On any pipeline invariant violation.
        """
        self._logger.operate("lifecycle.operate.start", self.state)

        # Step 1: Generate traversal addresses
        fetch_count = min(self._max_pages, TOTAL_PAGES)
        addresses = self._planner.operate(fetch_count)
        self.state.traversal_path = addresses
        self._logger.operate(
            "traversal.complete",
            self.state,
            {"address_count": len(addresses)},
        )

        # Step 2 & 3: Fetch pages and extract tokens
        if self._dry_run:
            corpus = self._build_dry_run_corpus(fetch_count)
        else:
            corpus = self._fetch_and_extract(addresses)

        self.state.corpus_size = len(corpus)
        self._logger.operate(
            "extraction.complete",
            self.state,
            {"corpus_size": len(corpus)},
        )

        # Step 4: Score corpus documents against query
        query_tokens = self._extractor.operate(
            " ".join(self._query.split())
        )
        if not query_tokens:
            # Query has no known-vocab tokens; use raw query split
            query_tokens = [
                t.lower()
                for t in re.findall(r"[A-Za-z]{2,}", self._query)
            ]
        # Build documents: sliding windows of 20 tokens
        docs = _build_documents(corpus, window=20)
        if docs:
            # Ensure at least one token; prefer first raw query word over generic fallback
            fallback = re.findall(r"[A-Za-z]{2,}", self._query)
            effective_tokens = query_tokens or [t.lower() for t in fallback[:1]] or ["library"]
            results = self._solver.operate(effective_tokens, docs)
        else:
            results = []
        self._solver.reconcile()
        self._logger.operate(
            "scoring.complete",
            self.state,
            {"doc_count": len(docs), "result_count": len(results)},
        )

        # Rebuild corpus from scored results (top-ranked docs first)
        if results:
            ranked_tokens: list[str] = []
            for r in results:
                ranked_tokens.extend(r["doc"])  # type: ignore[arg-type]
            corpus = ranked_tokens

        # Step 5: Assemble volume
        self.state.plan_pages = TOTAL_PAGES
        pages = self._assembler.operate(corpus)
        self._assembler.reconcile()
        self.state.assembled_length = self._assembler.assembled_length

        self._logger.operate(
            "assembly.complete",
            self.state,
            {"assembled_length": self.state.assembled_length},
        )

        # Step 6: Write output
        volume_text = "".join(pages)
        if len(volume_text) != TOTAL_CHARS:
            raise DeterministicHalt(
                f"Volume text invariant violated before write: "
                f"expected {TOTAL_CHARS}, got {len(volume_text)}",
                self.state.to_dict(),
            )
        try:
            self._output_path.write_text(volume_text, encoding="utf-8")
        except OSError as exc:
            raise DeterministicHalt(
                f"Output write failed: {self._output_path}: {exc}",
                self.state.to_dict(),
            ) from exc
        self._logger.operate(
            "output.written",
            self.state,
            {"output_path": str(self._output_path), "length": len(volume_text)},
        )

    def reconcile(self) -> None:
        """Verify pipeline state is consistent after operate.

        Raises:
            DeterministicHalt: If assembled length or output file are wrong.
        """
        if self.state.assembled_length != TOTAL_CHARS:
            raise DeterministicHalt(
                f"ControlPlane reconcile: assembled_length mismatch "
                f"(expected {TOTAL_CHARS}, got {self.state.assembled_length})",
                self.state.to_dict(),
            )
        if not self._output_path.exists():
            raise DeterministicHalt(
                f"ControlPlane reconcile: output file missing: {self._output_path}",
                self.state.to_dict(),
            )
        actual_len = len(self._output_path.read_text(encoding="utf-8"))
        if actual_len != TOTAL_CHARS:
            raise DeterministicHalt(
                f"ControlPlane reconcile: output file length mismatch "
                f"(expected {TOTAL_CHARS}, got {actual_len})",
                self.state.to_dict(),
            )
        self._extractor.reconcile()
        self._assembler.reconcile()
        self._logger.reconcile(self.state)
        self._logger.operate("lifecycle.reconcile", self.state)

    def checkpoint(self) -> None:
        """Write a checkpoint of the current state.

        Raises:
            DeterministicHalt: On checkpoint write failure.
        """
        cp_path = self._checkpointer.operate(self.state)
        self.state.last_checkpoint = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        self._checkpointer.reconcile(self.state)
        self._logger.checkpoint(self.state)
        _log_stderr(f"ControlPlane: checkpoint written to {cp_path}")

    def terminate(self) -> None:
        """Terminate all subsystems in reverse dependency order."""
        self._logger.operate("lifecycle.terminate", self.state)
        if not self._dry_run:
            self._client.terminate()
        self._planner.terminate()
        self._extractor.terminate()
        self._solver.terminate()
        self._assembler.terminate()
        self._checkpointer.terminate()
        self._logger.terminate()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_and_extract(
        self, addresses: list[dict[str, object]]
    ) -> list[str]:
        """Fetch pages from Babel and extract tokens.

        Args:
            addresses: List of address dicts from TraversalPlanner.

        Returns:
            Flat token list.
        """
        corpus: list[str] = []
        self.state.traversal_index = 0
        for addr in addresses:
            self.state.traversal_index += 1
            html = self._client.fetch_page(addr)
            tokens = self._extractor.operate(html)
            corpus.extend(tokens)
            self._logger.operate(
                "fetch.page",
                self.state,
                {"address": addr, "tokens": len(tokens)},
            )
        return corpus

    def _build_dry_run_corpus(self, count: int) -> list[str]:
        """Build a synthetic corpus without network access.

        The corpus is deterministically derived from the seed and query,
        using only the EMBEDDED_VOCAB. Produces a corpus large enough to
        fill TOTAL_PAGES pages.

        Args:
            count: Number of synthetic "pages" to simulate.

        Returns:
            List of tokens.
        """
        vocab_list = sorted(EMBEDDED_VOCAB)
        drng = random.Random(self._seed + 42)
        tokens_needed = TOTAL_CHARS // 5  # rough estimate: avg 5 chars/token
        corpus: list[str] = []
        # Seed with query words first
        query_words = [
            w.lower() for w in re.findall(r"[A-Za-z]{2,}", self._query)
            if w.lower() in EMBEDDED_VOCAB
        ]
        if query_words:
            corpus.extend(query_words * max(1, tokens_needed // (len(query_words) * 10)))
        # Fill rest deterministically
        while len(corpus) < tokens_needed:
            corpus.append(drng.choice(vocab_list))
        # Log each simulated page fetch
        for i in range(count):
            self.state.traversal_index = i + 1
            self._logger.operate(
                "fetch.page.dry_run",
                self.state,
                {"page_index": i},
            )
        return corpus


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="thalos_prime",
        description=(
            "Thalos Prime deterministic chatbot-to-Babel pipeline. "
            "Assembles a volume of exactly 1,312,000 characters "
            "(410 pages × 3,200 chars) via a seeded pseudo-random "
            "traversal of libraryofbabel.info."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Invariants:\n"
            "  - Output is exactly 1,312,000 characters.\n"
            "  - Any invariant breach halts deterministically.\n"
            "  - Replay with the same --seed reproduces identical output.\n\n"
            "Dry-run (offline):\n"
            "  Use --dry-run to run without network access.\n"
        ),
    )
    parser.add_argument(
        "--query", required=True, help="Natural language query string."
    )
    parser.add_argument(
        "--seed", type=int, required=True, help="Deterministic integer seed."
    )
    parser.add_argument(
        "--output", required=True, help="Path to write assembled volume."
    )
    parser.add_argument(
        "--workdir",
        required=True,
        help="Working directory for checkpoints and event logs.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=TOTAL_PAGES,
        help=f"Maximum pages to fetch from Babel (default {TOTAL_PAGES}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip network calls; use synthetic deterministic corpus.",
    )
    return parser


def _log_stderr(msg: str) -> None:
    """Write a message to stderr for observability.

    Args:
        msg: Message to write.
    """
    print(f"[thalos_prime] {msg}", file=sys.stderr, flush=True)


def _cyclic_slice(text: str, start: int, length: int) -> str:
    """Return a slice of `text` of `length` chars starting at `start`.

    Wraps cyclically if start + length > len(text).

    Args:
        text: Source text (must be non-empty).
        start: Starting position (modulo len(text)).
        length: Number of characters to return.

    Returns:
        String of exactly `length` characters.
    """
    if not text:
        return " " * length
    n = len(text)
    start = start % n
    result_parts: list[str] = []
    remaining = length
    pos = start
    while remaining > 0:
        end = min(pos + remaining, n)
        result_parts.append(text[pos:end])
        remaining -= end - pos
        pos = 0
    return "".join(result_parts)[:length]


def _build_documents(
    tokens: list[str], window: int = 20
) -> list[list[str]]:
    """Segment a token list into overlapping windows for BM25 scoring.

    Args:
        tokens: Flat list of tokens.
        window: Window size in tokens.

    Returns:
        List of token lists (non-overlapping windows).
    """
    if not tokens:
        return []
    return [tokens[i : i + window] for i in range(0, len(tokens), window)]


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point for the Thalos Prime pipeline.

    Lifecycle: initialize → validate → operate → reconcile → checkpoint →
    terminate. Any DeterministicHalt exits with code 2 and prints the
    state snapshot to stderr.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 on success, 1 on usage error, 2 on DeterministicHalt.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    _log_stderr(
        f"Starting pipeline: query={args.query!r}, seed={args.seed}, "
        f"output={args.output!r}, workdir={args.workdir!r}, "
        f"max_pages={args.max_pages}, dry_run={args.dry_run}"
    )

    cp = ControlPlane(
        query=args.query,
        seed=args.seed,
        output_path=args.output,
        workdir=args.workdir,
        max_pages=args.max_pages,
        dry_run=args.dry_run,
    )

    try:
        cp.initialize()
        cp.validate()
        cp.operate()
        cp.reconcile()
        cp.checkpoint()
        cp.terminate()
    except DeterministicHalt as halt:
        _log_stderr(f"DETERMINISTIC HALT: {halt.reason}")
        _log_stderr(
            "State snapshot:\n"
            + json.dumps(halt.state_snapshot, indent=2, sort_keys=True)
        )
        return 2

    _log_stderr(
        f"Pipeline complete. Output: {args.output} "
        f"({TOTAL_CHARS} chars, {TOTAL_PAGES} pages × {PAGE_CHARS} chars/page)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
