<!-- PROPRIETARY AND CONFIDENTIAL -->
<!-- Copyright © 2026 Tony Ray Macier III. All Rights Reserved. -->

# Core Module

**Version:** 2.0.0
**Owner:** Tony Ray Macier III
**Stability:** Stable

## Purpose
Contains fundamental logic and reusable system primitives for the ThalosPrime platform.

## Modules
- `base_engine.py` — Abstract base class for all engine implementations
- `utilities.py` — Shared utility functions (hashing, JSONL I/O, seed validation)

## Rules
- Core modules **cannot** depend on experimental modules
- Must be stable before release (no breaking changes)
- All functions must be deterministic given the same seed

## Extension Guidelines
To add a new core primitive:
1. Create a new `.py` file in `core/`
2. Include the IP header
3. Add it to `dependency_manifest.yml`
4. Add tests in `tests/test_core/`

## Failure Handling
- All functions raise `ValueError` for invalid inputs
- `validate_seed()` must be called before any seeded operation
