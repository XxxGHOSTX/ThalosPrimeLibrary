"""Tests for the CLI commands module.

Covers argument parsing (build_parser), run_cli dispatch, and each
individual handler function using direct function calls to avoid
subprocess overhead.
"""

import json

import pytest

from thalos_prime.cli.commands import build_parser, run_cli


def test_build_parser_returns_parser() -> None:
    """build_parser() returns a non-None ArgumentParser."""
    parser = build_parser()
    assert parser is not None
    assert parser.prog == "thalos-prime"


def test_parser_has_generate_subcommand() -> None:
    """generate subcommand accepts --address and --output."""
    parser = build_parser()
    args = parser.parse_args(["generate", "--address", "abc123"])
    assert args.command == "generate"
    assert args.address == "abc123"
    assert args.output is None


def test_parser_has_enumerate_subcommand() -> None:
    """enumerate subcommand accepts --query, --max-results, --depth."""
    parser = build_parser()
    args = parser.parse_args(["enumerate", "--query", "hello world"])
    assert args.command == "enumerate"
    assert args.query == "hello world"
    assert args.max_results == 20
    assert args.depth == 1


def test_parser_has_decode_subcommand() -> None:
    """decode subcommand accepts --address and optional --query."""
    parser = build_parser()
    args = parser.parse_args(["decode", "--address", "def456", "--query", "test"])
    assert args.command == "decode"
    assert args.address == "def456"
    assert args.query == "test"


def test_parser_has_search_subcommand() -> None:
    """search subcommand accepts --query, --max-results, --output."""
    parser = build_parser()
    args = parser.parse_args(["search", "--query", "find this", "--max-results", "5"])
    assert args.command == "search"
    assert args.query == "find this"
    assert args.max_results == 5


def test_parser_has_serve_subcommand() -> None:
    """serve subcommand accepts --host and --port."""
    parser = build_parser()
    args = parser.parse_args(["serve", "--host", "0.0.0.0", "--port", "9000"])
    assert args.command == "serve"
    assert args.host == "0.0.0.0"
    assert args.port == 9000


def test_run_cli_generate_succeeds(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli generate produces a 3200-character page on stdout."""
    rc = run_cli(["generate", "--address", "abc123"])

    assert rc == 0
    captured = capsys.readouterr()
    assert len(captured.out.strip()) == 3200


def test_run_cli_enumerate_produces_json(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli enumerate outputs valid JSON."""
    rc = run_cli(["enumerate", "--query", "hello", "--max-results", "3"])

    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)


def test_run_cli_decode_produces_json(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli decode outputs valid JSON with a score field."""
    rc = run_cli(["decode", "--address", "abc123"])

    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "overall_score" in data
    assert "confidence_level" in data


def test_run_cli_search_produces_sorted_results(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli search outputs a sorted list of results."""
    rc = run_cli(["search", "--query", "the quick brown fox", "--max-results", "3"])

    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    scores = [float(r["score"]) for r in data]
    assert scores == sorted(scores, reverse=True)


def test_run_cli_generate_with_output_file(tmp_path: pytest.TempPathFactory) -> None:
    """run_cli generate writes page content to the specified output file."""
    out_path = tmp_path / "page.txt"  # type: ignore[operator]
    rc = run_cli(["generate", "--address", "abc123", "--output", str(out_path)])

    assert rc == 0
    assert out_path.exists()
    assert len(out_path.read_text()) == 3200


def test_run_cli_missing_required_arg_returns_nonzero() -> None:
    """run_cli returns non-zero exit code when required argument is missing."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli(["generate"])
    assert exc_info.value.code != 0


def test_run_cli_no_command_returns_nonzero() -> None:
    """run_cli returns non-zero exit code when no subcommand is given."""
    with pytest.raises(SystemExit) as exc_info:
        run_cli([])
    assert exc_info.value.code != 0


def test_run_cli_enumerate_respects_max_results(capsys: pytest.CaptureFixture[str]) -> None:
    """run_cli enumerate --max-results limits the number of returned addresses."""
    rc = run_cli(["enumerate", "--query", "test", "--max-results", "5"])

    assert rc == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data) <= 5


def test_run_cli_search_with_output_file(tmp_path: pytest.TempPathFactory) -> None:
    """run_cli search --output writes JSON results to a file."""
    out_path = tmp_path / "results.json"  # type: ignore[operator]
    rc = run_cli(
        ["search", "--query", "hello", "--max-results", "2", "--output", str(out_path)]
    )

    assert rc == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text())
    assert isinstance(data, list)
