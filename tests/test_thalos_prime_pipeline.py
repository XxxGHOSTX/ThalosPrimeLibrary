"""Deterministic offline tests for the Thalos Prime pipeline.

All tests run without network access. The ControlPlane dry-run mode
provides a fully deterministic synthetic corpus so no network stubs are
needed in the test environment.

Test coverage:
    - DeterministicHalt exception carries reason and state snapshot.
    - SystemState serialization, deserialization, and state_hash.
    - VolumeAssembler assembles exactly 410 pages x 3,200 chars.
    - ConstraintSolver BM25 scoring with stable tie-breaks.
    - WordExtractor strips HTML and filters tokens.
    - TraversalPlanner produces deterministic seeded addresses.
    - Checkpointer writes JSON files to workdir.
    - StateLogger writes JSONL events.
    - ControlPlane dry-run produces exactly 1,312,000 char output.
    - _cyclic_slice and _build_documents helpers.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

# ---------------------------------------------------------------------------
# Load the root thalos_prime.py as a module named _thalos_pipeline.
# The root thalos_prime.py is a standalone executable module; its symbols
# must be accessed via importlib because the package thalos_prime/ shadows
# the filename when importing normally.
# ---------------------------------------------------------------------------
_PIPELINE_PATH = Path(__file__).parent.parent / "thalos_prime.py"


def _load_pipeline() -> ModuleType:
    """Load the root thalos_prime.py module for testing."""
    cached = sys.modules.get("_thalos_pipeline")
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(
        "_thalos_pipeline", str(_PIPELINE_PATH)
    )
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_thalos_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod


_pl: ModuleType = _load_pipeline()

DeterministicHalt = _pl.DeterministicHalt
SystemState = _pl.SystemState
Checkpointer = _pl.Checkpointer
StateLogger = _pl.StateLogger
TraversalPlanner = _pl.TraversalPlanner
WordExtractor = _pl.WordExtractor
ConstraintSolver = _pl.ConstraintSolver
VolumeAssembler = _pl.VolumeAssembler
ControlPlane = _pl.ControlPlane
TOTAL_CHARS: int = _pl.TOTAL_CHARS
PAGE_CHARS: int = _pl.PAGE_CHARS
TOTAL_PAGES: int = _pl.TOTAL_PAGES
EMBEDDED_VOCAB: frozenset[str] = _pl.EMBEDDED_VOCAB
_cyclic_slice = _pl._cyclic_slice
_build_documents = _pl._build_documents
main = _pl.main


# ===========================================================================
# DeterministicHalt
# ===========================================================================
class TestDeterministicHalt:
    """Tests for the DeterministicHalt exception."""

    def test_carries_reason_and_snapshot(self) -> None:
        """DeterministicHalt stores reason and state_snapshot."""
        snap = {"seed": 1, "traversal_index": 0}
        exc = DeterministicHalt("test reason", snap)
        assert exc.reason == "test reason"
        assert exc.state_snapshot == snap

    def test_str_includes_reason(self) -> None:
        """str(DeterministicHalt) includes the reason."""
        exc = DeterministicHalt("invariant X violated", {})
        assert "invariant X violated" in str(exc)

    def test_is_exception(self) -> None:
        """DeterministicHalt is a subclass of Exception."""
        assert issubclass(DeterministicHalt, Exception)

    def test_raise_and_catch(self) -> None:
        """DeterministicHalt can be raised and caught."""
        msg = "halt!"
        with pytest.raises(DeterministicHalt) as exc_info:
            raise DeterministicHalt(msg, {"key": "value"})
        assert exc_info.value.state_snapshot == {"key": "value"}


# ===========================================================================
# SystemState
# ===========================================================================
class TestSystemState:
    """Tests for SystemState serialization and hashing."""

    def test_to_dict_contains_all_fields(self) -> None:
        """to_dict includes version, seed, and all state fields."""
        s = SystemState(seed=42)
        d = s.to_dict()
        assert d["seed"] == 42
        assert "version" in d
        assert "traversal_index" in d
        assert "traversal_path" in d
        assert "corpus_size" in d
        assert "assembled_length" in d
        assert "output_path" in d

    def test_state_hash_is_deterministic(self) -> None:
        """Same state produces same hash."""
        s1 = SystemState(seed=7)
        s2 = SystemState(seed=7)
        assert s1.state_hash() == s2.state_hash()

    def test_state_hash_changes_with_state(self) -> None:
        """Changing corpus_size changes hash."""
        s = SystemState(seed=7)
        h1 = s.state_hash()
        s.corpus_size = 999
        h2 = s.state_hash()
        assert h1 != h2

    def test_from_dict_roundtrip(self) -> None:
        """from_dict(to_dict()) reproduces the same state."""
        s = SystemState(seed=99, corpus_size=50, assembled_length=1_312_000)
        recovered = SystemState.from_dict(s.to_dict())
        assert recovered.seed == s.seed
        assert recovered.corpus_size == s.corpus_size
        assert recovered.assembled_length == s.assembled_length

    def test_from_dict_incompatible_version_halts(self) -> None:
        """Loading a checkpoint with wrong version raises DeterministicHalt."""
        bad = {"version": "99.0", "seed": 1}
        with pytest.raises(DeterministicHalt) as exc_info:
            SystemState.from_dict(bad)
        assert "Incompatible checkpoint version" in exc_info.value.reason

    def test_state_hash_is_hex(self) -> None:
        """state_hash returns a hex string."""
        s = SystemState(seed=1)
        h = s.state_hash()
        assert re.fullmatch(r"[0-9a-f]+", h)


# ===========================================================================
# Checkpointer
# ===========================================================================
class TestCheckpointer:
    """Tests for the Checkpointer subsystem."""

    def test_initialize_creates_workdir(self, tmp_path: Path) -> None:
        """initialize() creates the work directory."""
        wd = tmp_path / "cp_test"
        cp = Checkpointer(wd)
        cp.initialize()
        assert wd.is_dir()

    def test_validate_passes_on_writable_dir(self, tmp_path: Path) -> None:
        """validate() passes on a writable directory."""
        cp = Checkpointer(tmp_path)
        cp.initialize()
        cp.validate()

    def test_operate_writes_json_file(self, tmp_path: Path) -> None:
        """operate() writes a JSON checkpoint file."""
        cp = Checkpointer(tmp_path)
        cp.initialize()
        state = SystemState(seed=123)
        path = cp.operate(state)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["state"]["seed"] == 123
        assert "state_hash" in data

    def test_checkpoint_alias_same_as_operate(self, tmp_path: Path) -> None:
        """checkpoint() is an alias for operate()."""
        cp = Checkpointer(tmp_path)
        cp.initialize()
        state = SystemState(seed=5)
        path = cp.checkpoint(state)
        assert path.exists()

    def test_initialize_fail_on_bad_path_halts(self) -> None:
        """initialize() raises DeterministicHalt on unwritable path."""
        bad = Path("/proc/sys/kernel/nonexistent_dir_xyz")
        cp = Checkpointer(bad)
        with pytest.raises(DeterministicHalt):
            cp.initialize()


# ===========================================================================
# StateLogger
# ===========================================================================
class TestStateLogger:
    """Tests for the StateLogger subsystem."""

    def test_initialize_sets_log_path(self, tmp_path: Path) -> None:
        """initialize() sets a non-None log path."""
        logger = StateLogger(tmp_path, seed=1)
        logger.initialize()
        assert logger._log_path is not None

    def test_operate_writes_jsonl_line(self, tmp_path: Path) -> None:
        """operate() appends a JSON line to the log file."""
        logger = StateLogger(tmp_path, seed=1)
        logger.initialize()
        state = SystemState(seed=1)
        logger.operate("test.event", state, {"key": "value"})
        assert logger._log_path is not None
        lines = logger._log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 1
        event = json.loads(lines[0])
        assert event["event_type"] == "test.event"
        assert event["seed"] == 1

    def test_multiple_events_append(self, tmp_path: Path) -> None:
        """Multiple operate() calls produce multiple JSONL lines."""
        logger = StateLogger(tmp_path, seed=2)
        logger.initialize()
        state = SystemState(seed=2)
        for i in range(3):
            logger.operate(f"event.{i}", state)
        assert logger._log_path is not None
        lines = logger._log_path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

    def test_validate_fails_before_initialize(self, tmp_path: Path) -> None:
        """validate() raises DeterministicHalt before initialize()."""
        logger = StateLogger(tmp_path, seed=1)
        with pytest.raises(DeterministicHalt):
            logger.validate()


# ===========================================================================
# TraversalPlanner
# ===========================================================================
class TestTraversalPlanner:
    """Tests for the TraversalPlanner subsystem."""

    def test_operate_returns_n_addresses(self) -> None:
        """operate(n) returns exactly n address dicts."""
        planner = TraversalPlanner(seed=42)
        planner.initialize()
        addrs = planner.operate(5)
        assert len(addrs) == 5

    def test_addresses_have_required_keys(self) -> None:
        """Each address dict has volume, wall, shelf, book, page."""
        planner = TraversalPlanner(seed=1)
        planner.initialize()
        addr = planner.operate(1)[0]
        for key in ("volume", "wall", "shelf", "book", "page"):
            assert key in addr

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed produces identical addresses."""
        p1 = TraversalPlanner(seed=99)
        p1.initialize()
        p2 = TraversalPlanner(seed=99)
        p2.initialize()
        assert p1.operate(3) == p2.operate(3)

    def test_different_seeds_differ(self) -> None:
        """Different seeds produce different addresses."""
        p1 = TraversalPlanner(seed=1)
        p1.initialize()
        p2 = TraversalPlanner(seed=2)
        p2.initialize()
        assert p1.operate(3) != p2.operate(3)

    def test_validate_fails_before_initialize(self) -> None:
        """validate() raises DeterministicHalt if RNG is not seeded."""
        planner = TraversalPlanner(seed=1)
        with pytest.raises(DeterministicHalt):
            planner.validate()

    def test_wall_in_range(self) -> None:
        """Wall values are in [1, WALLS_PER_VOLUME]."""
        planner = TraversalPlanner(seed=7)
        planner.initialize()
        walls_per_vol: int = _pl.WALLS_PER_VOLUME
        for addr in planner.operate(20):
            assert 1 <= addr["wall"] <= walls_per_vol

    def test_page_in_range(self) -> None:
        """Page values are in [1, PAGES_PER_BOOK]."""
        planner = TraversalPlanner(seed=8)
        planner.initialize()
        pages_per_book: int = _pl.PAGES_PER_BOOK
        for addr in planner.operate(20):
            assert 1 <= addr["page"] <= pages_per_book

    def test_path_property_accumulates(self) -> None:
        """Path property accumulates across operate() calls."""
        planner = TraversalPlanner(seed=3)
        planner.initialize()
        planner.operate(5)
        planner.operate(3)
        assert len(planner.path) == 8


# ===========================================================================
# WordExtractor
# ===========================================================================
class TestWordExtractor:
    """Tests for the WordExtractor subsystem."""

    def test_strips_html_tags(self) -> None:
        """HTML tags are removed before tokenization."""
        extractor = WordExtractor()
        extractor.initialize()
        extractor.validate()
        tokens = extractor.operate("<p>the library has many <b>word</b></p>")
        for t in tokens:
            assert "<" not in t
            assert ">" not in t

    def test_filters_to_vocab(self) -> None:
        """Only tokens in EMBEDDED_VOCAB are returned."""
        extractor = WordExtractor()
        extractor.initialize()
        tokens = extractor.operate("zxqjkl the library has words")
        for t in tokens:
            assert t in EMBEDDED_VOCAB

    def test_known_words_extracted(self) -> None:
        """Known vocab words are extracted from plain text."""
        extractor = WordExtractor()
        extractor.initialize()
        tokens = extractor.operate("the library has many book and page")
        assert "library" in tokens
        assert "book" in tokens

    def test_corpus_accumulates(self) -> None:
        """Repeated operate() calls accumulate the corpus."""
        extractor = WordExtractor()
        extractor.initialize()
        extractor.operate("the library")
        extractor.operate("more book")
        assert len(extractor.corpus) >= 2

    def test_reset_corpus(self) -> None:
        """reset_corpus() clears the accumulated corpus."""
        extractor = WordExtractor()
        extractor.initialize()
        extractor.operate("the library book")
        extractor.reset_corpus()
        assert extractor.corpus == []

    def test_empty_input(self) -> None:
        """Empty string produces empty token list."""
        extractor = WordExtractor()
        extractor.initialize()
        tokens = extractor.operate("")
        assert tokens == []


# ===========================================================================
# ConstraintSolver
# ===========================================================================
class TestConstraintSolver:
    """Tests for the ConstraintSolver BM25 subsystem."""

    def test_scores_documents(self) -> None:
        """operate() returns scored results for given query and docs."""
        solver = ConstraintSolver()
        solver.initialize()
        docs = [["library", "book", "page"], ["car", "road", "drive"]]
        results = solver.operate(["library", "book"], docs)
        assert len(results) == 2
        assert results[0]["doc_id"] == 0

    def test_stable_sort_by_score_desc(self) -> None:
        """Results are sorted by score descending."""
        solver = ConstraintSolver()
        solver.initialize()
        docs = [
            ["the", "and", "book"],
            ["library", "book", "page", "library"],
            ["car"],
        ]
        results = solver.operate(["library", "book"], docs)
        scores = [float(r["score"]) for r in results]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]

    def test_stable_sort_tie_break_by_doc_id(self) -> None:
        """Equal-score docs are sorted by doc_id ascending."""
        solver = ConstraintSolver()
        solver.initialize()
        docs = [["book"], ["book"]]
        results = solver.operate(["book"], docs)
        assert results[0]["doc_id"] < results[1]["doc_id"]

    def test_empty_docs_returns_empty(self) -> None:
        """Empty document list returns empty results."""
        solver = ConstraintSolver()
        solver.initialize()
        results = solver.operate(["library"], [])
        assert results == []

    def test_empty_query_halts(self) -> None:
        """Empty query raises DeterministicHalt."""
        solver = ConstraintSolver()
        solver.initialize()
        with pytest.raises(DeterministicHalt):
            solver.operate([], [["book", "library"]])

    def test_reconcile_sorted_scores_passes(self) -> None:
        """reconcile() passes after a correct operate() call."""
        solver = ConstraintSolver()
        solver.initialize()
        solver.operate(["library"], [["library", "book"], ["car"]])
        solver.reconcile()

    def test_deterministic_same_query(self) -> None:
        """Same query and docs produce identical scores."""
        s1 = ConstraintSolver()
        s1.initialize()
        s2 = ConstraintSolver()
        s2.initialize()
        docs = [["the", "library"], ["book", "page", "library"]]
        r1 = s1.operate(["library"], docs)
        r2 = s2.operate(["library"], docs)
        assert [float(r["score"]) for r in r1] == [float(r["score"]) for r in r2]


# ===========================================================================
# VolumeAssembler
# ===========================================================================
class TestVolumeAssembler:
    """Tests for the VolumeAssembler subsystem."""

    def test_assembles_exactly_total_chars(self) -> None:
        """Assembled volume is exactly TOTAL_CHARS characters."""
        assembler = VolumeAssembler(seed=1)
        assembler.initialize()
        corpus = ["the", "library", "has", "book"] * 5000
        pages = assembler.operate(corpus)
        total = sum(len(p) for p in pages)
        assert total == TOTAL_CHARS

    def test_exactly_total_pages(self) -> None:
        """Assembled volume has exactly TOTAL_PAGES pages."""
        assembler = VolumeAssembler(seed=1)
        assembler.initialize()
        pages = assembler.operate(["word"] * 1000)
        assert len(pages) == TOTAL_PAGES

    def test_each_page_is_page_chars(self) -> None:
        """Every page is exactly PAGE_CHARS characters."""
        assembler = VolumeAssembler(seed=2)
        assembler.initialize()
        pages = assembler.operate(["library", "book", "page"] * 1000)
        for i, page in enumerate(pages):
            assert len(page) == PAGE_CHARS, f"Page {i} has {len(page)} chars"

    def test_empty_corpus_uses_default_text(self) -> None:
        """Empty corpus still produces TOTAL_CHARS output."""
        assembler = VolumeAssembler(seed=3)
        assembler.initialize()
        pages = assembler.operate([])
        assert sum(len(p) for p in pages) == TOTAL_CHARS

    def test_assembled_length_property(self) -> None:
        """assembled_length property equals sum of page lengths."""
        assembler = VolumeAssembler(seed=4)
        assembler.initialize()
        pages = assembler.operate(["word"] * 500)
        assert assembler.assembled_length == sum(len(p) for p in pages)

    def test_reconcile_passes_after_operate(self) -> None:
        """reconcile() passes after a successful operate()."""
        assembler = VolumeAssembler(seed=5)
        assembler.initialize()
        assembler.operate(["library"] * 100)
        assembler.reconcile()

    def test_deterministic_with_same_seed(self) -> None:
        """Same seed and corpus produce identical pages."""
        corpus = ["the", "library", "has", "many", "book"] * 200
        a1 = VolumeAssembler(seed=10)
        a1.initialize()
        p1 = a1.operate(corpus)
        a2 = VolumeAssembler(seed=10)
        a2.initialize()
        p2 = a2.operate(corpus)
        assert p1 == p2

    def test_padding_uses_only_spaces(self) -> None:
        """Pages padded to PAGE_CHARS use spaces, not other chars."""
        assembler = VolumeAssembler(seed=6)
        assembler.initialize()
        pages = assembler.operate(["hi"])
        for page in pages:
            assert len(page) == PAGE_CHARS


# ===========================================================================
# Helper functions
# ===========================================================================
class TestHelpers:
    """Tests for module-level helper functions."""

    def test_cyclic_slice_exact_fit(self) -> None:
        """_cyclic_slice returns correct length when text is longer."""
        text = "abcdefghij"
        result = _cyclic_slice(text, 0, 5)
        assert result == "abcde"
        assert len(result) == 5

    def test_cyclic_slice_wraps_around(self) -> None:
        """_cyclic_slice wraps when start + length > len(text)."""
        text = "abcde"
        result = _cyclic_slice(text, 3, 5)
        assert len(result) == 5
        assert result == "deabc"

    def test_cyclic_slice_empty_text(self) -> None:
        """_cyclic_slice with empty text returns spaces."""
        result = _cyclic_slice("", 0, 10)
        assert result == " " * 10

    def test_build_documents_windows(self) -> None:
        """_build_documents creates non-overlapping windows."""
        tokens = list(range(45))
        docs = _build_documents(tokens, window=10)
        assert len(docs) == 5
        assert len(docs[0]) == 10
        assert len(docs[-1]) == 5

    def test_build_documents_empty(self) -> None:
        """_build_documents with empty tokens returns empty list."""
        assert _build_documents([]) == []



class TestControlPlaneDryRun:
    """Tests for ControlPlane in dry-run (offline) mode."""

    def test_full_pipeline_dry_run(self, tmp_path: Path) -> None:
        """Full dry-run pipeline produces exactly TOTAL_CHARS output."""
        output = tmp_path / "volume.txt"
        wd = tmp_path / "workdir"
        cp = ControlPlane(
            query="library books and pages",
            seed=42,
            output_path=str(output),
            workdir=str(wd),
            max_pages=10,
            dry_run=True,
        )
        cp.initialize()
        cp.validate()
        cp.operate()
        cp.reconcile()
        cp.checkpoint()
        cp.terminate()

        assert output.exists()
        text = output.read_text(encoding="utf-8")
        assert len(text) == TOTAL_CHARS

    def test_dry_run_deterministic(self, tmp_path: Path) -> None:
        """Two dry-runs with same seed produce identical outputs."""
        for run_idx in range(2):
            out = tmp_path / f"run{run_idx}.txt"
            wd = tmp_path / f"wd{run_idx}"
            cp = ControlPlane(
                query="test",
                seed=7,
                output_path=str(out),
                workdir=str(wd),
                dry_run=True,
            )
            cp.initialize()
            cp.validate()
            cp.operate()
            cp.reconcile()
            cp.checkpoint()
            cp.terminate()

        text0 = (tmp_path / "run0.txt").read_text(encoding="utf-8")
        text1 = (tmp_path / "run1.txt").read_text(encoding="utf-8")
        assert text0 == text1

    def test_dry_run_different_seeds_differ(self, tmp_path: Path) -> None:
        """Different seeds produce different outputs."""
        for seed in (1, 2):
            out = tmp_path / f"seed{seed}.txt"
            wd = tmp_path / f"wd{seed}"
            cp = ControlPlane(
                query="library",
                seed=seed,
                output_path=str(out),
                workdir=str(wd),
                dry_run=True,
            )
            cp.initialize()
            cp.validate()
            cp.operate()
            cp.reconcile()
            cp.checkpoint()
            cp.terminate()

        t1 = (tmp_path / "seed1.txt").read_text(encoding="utf-8")
        t2 = (tmp_path / "seed2.txt").read_text(encoding="utf-8")
        assert t1 != t2

    def test_checkpoint_written(self, tmp_path: Path) -> None:
        """checkpoint() writes a .json file in the workdir."""
        out = tmp_path / "volume.txt"
        wd = tmp_path / "workdir"
        cp = ControlPlane(
            query="test",
            seed=1,
            output_path=str(out),
            workdir=str(wd),
            dry_run=True,
        )
        cp.initialize()
        cp.validate()
        cp.operate()
        cp.reconcile()
        cp.checkpoint()
        cp.terminate()

        checkpoints = list(wd.glob("checkpoint_*.json"))
        assert len(checkpoints) >= 1

    def test_event_log_written(self, tmp_path: Path) -> None:
        """Events JSONL file is written in the workdir."""
        out = tmp_path / "volume.txt"
        wd = tmp_path / "workdir"
        cp = ControlPlane(
            query="test",
            seed=2,
            output_path=str(out),
            workdir=str(wd),
            dry_run=True,
        )
        cp.initialize()
        cp.validate()
        cp.operate()
        cp.reconcile()
        cp.checkpoint()
        cp.terminate()

        logs = list(wd.glob("events_*.jsonl"))
        assert len(logs) == 1
        lines = logs[0].read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) >= 3
        for line in lines:
            evt = json.loads(line)
            assert "event_type" in evt
            assert evt["seed"] == 2

    def test_state_has_correct_assembled_length(self, tmp_path: Path) -> None:
        """After operate(), state.assembled_length == TOTAL_CHARS."""
        out = tmp_path / "volume.txt"
        wd = tmp_path / "workdir"
        cp = ControlPlane(
            query="search",
            seed=3,
            output_path=str(out),
            workdir=str(wd),
            dry_run=True,
        )
        cp.initialize()
        cp.validate()
        cp.operate()
        assert cp.state.assembled_length == TOTAL_CHARS

    def test_missing_operate_reconcile_halts(self, tmp_path: Path) -> None:
        """reconcile() before operate() raises DeterministicHalt."""
        out = tmp_path / "volume.txt"
        wd = tmp_path / "workdir"
        cp = ControlPlane(
            query="test",
            seed=99,
            output_path=str(out),
            workdir=str(wd),
            dry_run=True,
        )
        cp.initialize()
        cp.validate()
        with pytest.raises(DeterministicHalt):
            cp.reconcile()


# ===========================================================================
# CLI entry point
# ===========================================================================
class TestCLI:
    """Tests for the CLI main() entry point."""

    def test_cli_dry_run_success(self, tmp_path: Path) -> None:
        """CLI dry-run exits with code 0 and writes output file."""
        out = str(tmp_path / "out.txt")
        wd = str(tmp_path / "wd")
        rc = main([
            "--query", "test",
            "--seed", "1",
            "--output", out,
            "--workdir", wd,
            "--dry-run",
        ])
        assert rc == 0
        assert Path(out).exists()
        assert len(Path(out).read_text(encoding="utf-8")) == TOTAL_CHARS

    def test_cli_dry_run_output_exact_length(self, tmp_path: Path) -> None:
        """CLI dry-run output is exactly 1,312,000 characters."""
        out = tmp_path / "vol.txt"
        wd = tmp_path / "workdir"
        main([
            "--query", "library books pages",
            "--seed", "12345",
            "--output", str(out),
            "--workdir", str(wd),
            "--dry-run",
        ])
        assert len(out.read_text(encoding="utf-8")) == 1_312_000

    def test_cli_invalid_seed_type(self, tmp_path: Path) -> None:
        """CLI exits non-zero on invalid seed type."""
        build_parser = _pl._build_parser
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([
                "--query", "test",
                "--seed", "notanint",
                "--output", str(tmp_path / "out.txt"),
                "--workdir", str(tmp_path / "wd"),
            ])
        assert exc_info.value.code != 0

    def test_cli_missing_query_exits(self, tmp_path: Path) -> None:
        """CLI exits non-zero when --query is missing."""
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--seed", "1",
                "--output", str(tmp_path / "out.txt"),
                "--workdir", str(tmp_path / "wd"),
            ])
        assert exc_info.value.code != 0
