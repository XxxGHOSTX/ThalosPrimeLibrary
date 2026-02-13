"""Validation tools for Thalos Prime Library.

This package contains validators to enforce coding standards:
- validate_lifecycle.py: Check lifecycle method implementation
- validate_determinism.py: Detect non-deterministic operations
- validate_state.py: Validate state management patterns
- validate_docs.py: Verify documentation completeness
- detect_prohibited_patterns.py: Find prohibited code patterns
"""

__all__ = [
    "validate_lifecycle",
    "validate_determinism",
    "validate_state",
    "validate_docs",
    "detect_prohibited_patterns",
]
