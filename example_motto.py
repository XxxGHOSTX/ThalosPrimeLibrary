#!/usr/bin/env python3
"""
Example demonstrating access to the Library of Babel philosophical motto.

The motto captures the essence of the Library of Babel:
- Infinite possibilities exist in fragmentary form
- Asking/querying reveals patterns in the noise
- Meaning is always present, waiting to be discovered
"""

import thalos_prime


def main() -> None:
    """Display the philosophical motto of the Library."""
    print("=" * 80)
    print("ThalosPrime Library - Philosophical Foundation")
    print("=" * 80)
    print()
    print(thalos_prime.LIBRARY_MOTTO)
    print()
    print("-" * 80)
    print(f"Version: {thalos_prime.__version__}")
    print(f"Author: {thalos_prime.__author__}")
    print("-" * 80)
    print()
    print("This motto reflects the core principle of the Library of Babel:")
    print("All possible text exists in fragmented form, and through querying")
    print("and coherence scoring, we can find meaningful patterns in what")
    print("appears to be noise.")
    print("=" * 80)


if __name__ == "__main__":
    main()
