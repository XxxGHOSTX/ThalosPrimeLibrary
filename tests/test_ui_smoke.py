"""UI smoke tests — headless-friendly.

Validates:
- UI template and static asset files exist on disk.
- FastAPI app serves the root (/) endpoint and returns HTML.
- FastAPI app serves the /api/v1/status endpoint.
- Key JS/CSS assets are present in the expected locations.
- The UI module is importable.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[1]
_UI_DIR = _REPO_ROOT / "thalos_prime" / "ui"
_TEMPLATES_DIR = _UI_DIR / "templates"
_STATIC_DIR = _UI_DIR / "static"
_CSS_DIR = _STATIC_DIR / "css"
_JS_DIR = _STATIC_DIR / "js"


# ---------------------------------------------------------------------------
# Static asset existence
# ---------------------------------------------------------------------------

def test_ui_directory_exists() -> None:
    """The thalos_prime/ui directory must exist."""
    assert _UI_DIR.exists(), f"UI directory missing: {_UI_DIR}"
    assert _UI_DIR.is_dir()


def test_index_html_exists() -> None:
    """The main UI template (index.html) must exist."""
    index = _TEMPLATES_DIR / "index.html"
    assert index.exists(), f"index.html missing: {index}"
    assert index.stat().st_size > 0, "index.html must not be empty"


def test_matrix_css_exists() -> None:
    """matrix.css must exist and contain Matrix theme variables."""
    css = _CSS_DIR / "matrix.css"
    assert css.exists(), f"matrix.css missing: {css}"
    content = css.read_text(encoding="utf-8")
    assert "--matrix-primary" in content, "matrix.css must define --matrix-primary"


def test_console_css_exists() -> None:
    """console.css must exist."""
    css = _CSS_DIR / "console.css"
    assert css.exists(), f"console.css missing: {css}"
    assert css.stat().st_size > 0


def test_animations_css_exists() -> None:
    """animations.css must exist."""
    css = _CSS_DIR / "animations.css"
    assert css.exists(), f"animations.css missing: {css}"


def test_main_js_exists() -> None:
    """main.js must exist."""
    js = _JS_DIR / "main.js"
    assert js.exists(), f"main.js missing: {js}"
    assert js.stat().st_size > 0


def test_matrix_background_js_exists() -> None:
    """matrix-background.js must exist and reference canvas animation."""
    js = _JS_DIR / "matrix-background.js"
    assert js.exists(), f"matrix-background.js missing: {js}"
    content = js.read_text(encoding="utf-8")
    assert "canvas" in content.lower(), (
        "matrix-background.js must contain canvas-based animation"
    )


def test_api_client_js_exists() -> None:
    """api-client.js must exist."""
    js = _JS_DIR / "api-client.js"
    assert js.exists(), f"api-client.js missing: {js}"


def test_ui_manager_js_exists() -> None:
    """ui-manager.js must exist."""
    js = _JS_DIR / "ui-manager.js"
    assert js.exists(), f"ui-manager.js missing: {js}"


def test_console_handler_js_exists() -> None:
    """console-handler.js must exist."""
    js = _JS_DIR / "console-handler.js"
    assert js.exists(), f"console-handler.js missing: {js}"


# ---------------------------------------------------------------------------
# UI module importability
# ---------------------------------------------------------------------------

def test_ui_module_importable() -> None:
    """thalos_prime.ui must be importable."""
    import thalos_prime.ui

    assert thalos_prime.ui is not None


# ---------------------------------------------------------------------------
# FastAPI endpoint smoke tests (headless — no browser required)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a TestClient for the Thalos Prime FastAPI app."""
    from thalos_prime.api.server import app

    return TestClient(app, raise_server_exceptions=False)


def test_root_returns_html(client: TestClient) -> None:
    """GET / must return 200 with text/html content."""
    response = client.get("/")
    assert response.status_code == 200
    content_type = response.headers.get("content-type", "")
    assert "text/html" in content_type, (
        f"Expected text/html, got {content_type!r}"
    )


def test_root_html_contains_thalos(client: TestClient) -> None:
    """The root HTML page must mention 'Thalos' (case-insensitive)."""
    response = client.get("/")
    assert response.status_code == 200
    assert "thalos" in response.text.lower(), (
        "Root page must reference 'Thalos'"
    )


def test_api_status_endpoint(client: TestClient) -> None:
    """GET /api/v1/status must return 200 with JSON status='online'."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "online"


def test_openapi_docs_available(client: TestClient) -> None:
    """GET /docs must return 200 (OpenAPI docs available)."""
    response = client.get("/docs")
    assert response.status_code == 200
