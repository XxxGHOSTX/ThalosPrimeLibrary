"""Root conftest.py - skip tests that require optional dependencies."""

collect_ignore_glob = []

try:
    import fastapi  # noqa: F401
except ImportError:
    collect_ignore_glob += [
        "tests/test_api_chat.py",
        "tests/test_api_search.py",
        "tests/test_babel_endpoints.py",
        "tests/test_main.py",
    ]
