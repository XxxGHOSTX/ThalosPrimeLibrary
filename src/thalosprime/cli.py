"""Thalos Prime CLI entrypoint.

Delegates to the ControlPlane pipeline defined in thalos_prime.py.
Accepts the same arguments:
    --query     Query string (required)
    --seed      Deterministic seed (required)
    --output    Output file path (required)
    --workdir   Working directory for checkpoints and logs (required)
    --max-pages Maximum pages to fetch (default: 5)
    --dry-run   Run offline without network access

Exit codes:
    0  Success
    1  Usage / argument error
    2  DeterministicHalt (invariant violation with state snapshot on stderr)
"""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


def _load_pipeline() -> ModuleType:
    """Load the root thalos_prime.py module using importlib.

    Returns:
        ModuleType: The loaded thalos_prime pipeline module.

    Raises:
        FileNotFoundError: If thalos_prime.py cannot be located.

    """
    # Locate thalos_prime.py relative to this file:
    # src/thalosprime/cli.py -> ../../thalos_prime.py
    pipeline_path = Path(__file__).parent.parent.parent / "thalos_prime.py"
    if not pipeline_path.exists():
        msg = f"thalos_prime.py not found at {pipeline_path}"
        raise FileNotFoundError(msg)

    cached = sys.modules.get("_thalos_pipeline_cli")
    if cached is not None:
        return cached

    spec = importlib.util.spec_from_file_location("_thalos_pipeline_cli", str(pipeline_path))
    if spec is None or spec.loader is None:
        msg = f"Could not create module spec for {pipeline_path}"
        raise ImportError(msg)

    mod = importlib.util.module_from_spec(spec)
    sys.modules["_thalos_pipeline_cli"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def main() -> int:
    """Delegate to the Thalos Prime pipeline in thalos_prime.py.

    All argument parsing and lifecycle management is handled by the
    pipeline's main() function. This entrypoint loads thalos_prime.py
    using importlib and forwards execution to its main().

    Returns:
        int: Exit code (0 = success, 1 = usage error, 2 = DeterministicHalt).

    """
    pipeline = _load_pipeline()
    return pipeline.main()  # type: ignore[no-any-return]


if __name__ == '__main__':
    raise SystemExit(main())
