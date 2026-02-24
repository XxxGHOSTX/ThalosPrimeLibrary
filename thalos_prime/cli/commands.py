"""CLI commands for the Thalos Prime Library of Babel toolkit.

Provides an ``argparse``-based command-line interface with the following
subcommands:

- ``generate``  — generate a page from a hex address
- ``enumerate`` — enumerate candidate addresses for a query
- ``decode``    — score coherence of a page at a given address
- ``search``    — full pipeline: enumerate → generate → decode → rank
- ``serve``     — start the FastAPI server

All subcommands delegate to the real Thalos Prime modules (BabelGenerator,
BabelEnumerator, BabelDecoder). Output is written to stdout or to a file
when ``--output`` is specified.

Control Plane boundary: CLI dispatches to Data Plane modules; it does not
implement any generation or scoring logic itself.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Create and return the top-level argument parser with all subcommands.

    Returns:
        Configured ArgumentParser with generate, enumerate, decode, search,
        and serve subcommands.

    """
    parser = argparse.ArgumentParser(
        prog="thalos-prime",
        description="Thalos Prime — deterministic Library of Babel exploration toolkit",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: WARNING)",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # ------------------------------------------------------------------
    # generate
    # ------------------------------------------------------------------
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate a Library of Babel page from a hexadecimal address",
    )
    gen_parser.add_argument(
        "--address",
        required=True,
        help="Hexadecimal address of the page to generate",
    )
    gen_parser.add_argument(
        "--output",
        default=None,
        help="Path to write the generated page (default: stdout)",
    )

    # ------------------------------------------------------------------
    # enumerate
    # ------------------------------------------------------------------
    enum_parser = subparsers.add_parser(
        "enumerate",
        help="Enumerate candidate page addresses for a query string",
    )
    enum_parser.add_argument(
        "--query",
        required=True,
        help="Text to search for in the Library of Babel",
    )
    enum_parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        metavar="N",
        help="Maximum number of candidate addresses (default: 20)",
    )
    enum_parser.add_argument(
        "--depth",
        type=int,
        default=1,
        metavar="D",
        help="Search depth — higher values produce more address variants (default: 1)",
    )

    # ------------------------------------------------------------------
    # decode
    # ------------------------------------------------------------------
    dec_parser = subparsers.add_parser(
        "decode",
        help="Decode a page and compute its coherence score",
    )
    dec_parser.add_argument(
        "--address",
        required=True,
        help="Hexadecimal address of the page to decode",
    )
    dec_parser.add_argument(
        "--query",
        default=None,
        help="Optional query for relevance scoring",
    )

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------
    search_parser = subparsers.add_parser(
        "search",
        help="Full pipeline: enumerate addresses → generate pages → decode → rank",
    )
    search_parser.add_argument(
        "--query",
        required=True,
        help="Text to search for",
    )
    search_parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        metavar="N",
        help="Maximum results to return (default: 10)",
    )
    search_parser.add_argument(
        "--output",
        default=None,
        help="Path to write JSON results (default: stdout)",
    )

    # ------------------------------------------------------------------
    # serve
    # ------------------------------------------------------------------
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the Thalos Prime FastAPI server",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="TCP port (default: 8000)",
    )

    return parser


def _write_output(content: str, path: str | None) -> None:
    """Write content to a file or stdout.

    Args:
        content: Text to write.
        path: File path, or None to write to stdout.

    """
    if path is None:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        logger.info("Output written to %s", path)


def _handle_generate(args: argparse.Namespace) -> int:
    """Handle the generate subcommand.

    Args:
        args: Parsed arguments containing address and optional output path.

    Returns:
        Exit code (0 on success, 1 on error).

    """
    from thalos_prime.lob_babel_generator import BabelGenerator

    generator = BabelGenerator()
    page = generator.address_to_page(args.address)
    _write_output(page, args.output)
    return 0


def _handle_enumerate(args: argparse.Namespace) -> int:
    """Handle the enumerate subcommand.

    Args:
        args: Parsed arguments containing query, max_results, and depth.

    Returns:
        Exit code (0 on success, 1 on error).

    """
    from thalos_prime.lob_babel_enumerator import BabelEnumerator

    enumerator = BabelEnumerator()
    candidates = enumerator.enumerate_addresses(
        args.query,
        max_results=args.max_results,
        depth=args.depth,
    )
    output = json.dumps(candidates, indent=2)
    _write_output(output, None)
    return 0


def _handle_decode(args: argparse.Namespace) -> int:
    """Handle the decode subcommand.

    Args:
        args: Parsed arguments containing address and optional query.

    Returns:
        Exit code (0 on success, 1 on error).

    """
    from thalos_prime.lob_babel_generator import BabelGenerator
    from thalos_prime.lob_decoder import BabelDecoder

    generator = BabelGenerator()
    decoder = BabelDecoder()
    page_text = generator.address_to_page(args.address)
    decoded = decoder.decode_page(args.address, page_text, query=args.query)
    result: dict[str, Any] = {
        "address": decoded.address,
        "overall_score": decoded.coherence.overall_score,
        "confidence_level": decoded.coherence.confidence_level,
        "language_score": decoded.coherence.language_score,
        "structure_score": decoded.coherence.structure_score,
        "ngram_score": decoded.coherence.ngram_score,
        "exact_match_score": decoded.coherence.exact_match_score,
    }
    _write_output(json.dumps(result, indent=2), None)
    return 0


def _handle_search(args: argparse.Namespace) -> int:
    """Handle the search subcommand (enumerate → generate → decode → rank).

    Args:
        args: Parsed arguments containing query, max_results, and optional output.

    Returns:
        Exit code (0 on success, 1 on error).

    """
    from thalos_prime.lob_babel_enumerator import BabelEnumerator
    from thalos_prime.lob_babel_generator import BabelGenerator
    from thalos_prime.lob_decoder import BabelDecoder

    enumerator = BabelEnumerator()
    generator = BabelGenerator()
    decoder = BabelDecoder()

    candidates = enumerator.enumerate_addresses(args.query, max_results=args.max_results)

    results: list[dict[str, Any]] = []
    for candidate in candidates:
        address = str(candidate.get("address", ""))
        page_text = generator.address_to_page(address)
        decoded = decoder.decode_page(address, page_text, query=args.query)
        results.append(
            {
                "address": address,
                "score": decoded.coherence.overall_score,
                "confidence_level": decoded.coherence.confidence_level,
                "snippet": page_text[:240].replace("\n", " "),
            }
        )

    results.sort(key=lambda r: float(r.get("score", 0.0)), reverse=True)
    output = json.dumps(results, indent=2)
    _write_output(output, args.output)
    return 0


def _handle_serve(args: argparse.Namespace) -> int:
    """Handle the serve subcommand — start the FastAPI server.

    Args:
        args: Parsed arguments containing host and port.

    Returns:
        Exit code (0 on success, 1 on error).

    """
    try:
        import uvicorn  # pyright: ignore[reportMissingImports]
    except ImportError:
        logger.error("uvicorn is required to start the server: pip install uvicorn")
        sys.stderr.write(
            "Error: uvicorn is not installed. Install it with: pip install uvicorn\n"
        )
        return 1

    uvicorn.run(
        "thalos_prime.api.server:app",
        host=args.host,
        port=args.port,
        log_level="info",
    )
    return 0


_DISPATCH: dict[str, Any] = {
    "generate": _handle_generate,
    "enumerate": _handle_enumerate,
    "decode": _handle_decode,
    "search": _handle_search,
    "serve": _handle_serve,
}


def run_cli(argv: list[str] | None = None) -> int:
    """Parse arguments and dispatch to the appropriate handler.

    Args:
        argv: Argument list to parse. Defaults to ``sys.argv[1:]`` when None.

    Returns:
        Exit code: 0 on success, 1 on error.

    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level, logging.WARNING),
        format="%(levelname)s %(name)s: %(message)s",
    )

    handler = _DISPATCH.get(args.command)
    if handler is None:
        parser.print_help(sys.stderr)
        return 1

    try:
        return int(handler(args))
    except (RuntimeError, ValueError, ImportError, OSError) as exc:
        logger.error("Command %r failed: %s", args.command, exc)
        sys.stderr.write(f"Error: {exc}\n")
        return 1
