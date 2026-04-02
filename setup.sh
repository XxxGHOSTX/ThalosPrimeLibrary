#!/usr/bin/env bash
# ThalosPrimeLibrary — Unix/macOS automated setup and launch script.
#
# Usage:
#   bash setup.sh                   # setup + serve
#   bash setup.sh --action test     # setup + run tests
#   bash setup.sh --action validate # setup + validators
#   bash setup.sh --action clean    # clean build artifacts
#   bash setup.sh --action none     # setup only
#
# Options:
#   --action   serve|test|validate|clean|none  (default: serve)
#   --host     bind host                        (default: 127.0.0.1)
#   --port     bind port                        (default: 8000)
#   --log-level DEBUG|INFO|WARNING|ERROR        (default: INFO)
#   --no-dev   skip dev-dependency installation
#
# Windows users: run .\setup.ps1 in PowerShell.
# Cross-platform: python launch.py --help
set -euo pipefail

# ─── Defaults ─────────────────────────────────────────────────────────────────
ACTION="serve"
HOST="127.0.0.1"
PORT=8000
LOG_LEVEL="INFO"
DEV=1

# ─── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --action)   ACTION="$2"; shift 2 ;;
        --host)     HOST="$2";   shift 2 ;;
        --port)     PORT="$2";   shift 2 ;;
        --log-level)LOG_LEVEL="$2"; shift 2 ;;
        --no-dev)   DEV=0; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'

header() { echo -e "\n${CYAN}$(printf '=%.0s' {1..62})${NC}\n  ${CYAN}$1${NC}\n${CYAN}$(printf '=%.0s' {1..62})${NC}"; }
step()   { echo -e "  ${YELLOW}>> $1${NC}"; }
ok()     { echo -e "  ${GREEN}[OK]${NC} $1"; }
warn()   { echo -e "  ${YELLOW}[WARN]${NC} $1"; }
fail()   { echo -e "  ${RED}[FAIL]${NC} $1"; exit 1; }

# ─── Locate repo root ─────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

header "ThalosPrimeLibrary — Unix Setup & Launch"
echo "  Repository : $REPO_ROOT"
echo "  Action     : $ACTION"
echo "  Host:Port  : ${HOST}:${PORT}"
echo "  Log level  : $LOG_LEVEL"

# ─── 1. Python >= 3.12 ────────────────────────────────────────────────────────
header "Step 1 — Python version check"

PYTHON_EXE=""
for candidate in python3.13 python3.12 python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" --version 2>&1 | grep -oP '\d+\.\d+')
        major="${ver%%.*}"; minor="${ver##*.}"
        if [[ "$major" -gt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -ge 12 ]]; }; then
            PYTHON_EXE="$candidate"
            ok "Found $("$candidate" --version 2>&1) ($candidate)"
            break
        else
            warn "$("$candidate" --version 2>&1) < 3.12 — skipping"
        fi
    fi
done

[[ -z "$PYTHON_EXE" ]] && fail "Python >= 3.12 not found. Install from https://www.python.org/downloads/"

# ─── 2. Virtual environment ───────────────────────────────────────────────────
header "Step 2 — Virtual environment"

VENV_DIR="$REPO_ROOT/.venv"

if [[ -d "$VENV_DIR" ]]; then
    ok "Existing .venv found — reusing"
else
    step "Creating .venv ..."
    "$PYTHON_EXE" -m venv "$VENV_DIR"
    ok ".venv created"
fi

# Activate (source for this script's shell; subshells use explicit paths)
if [[ -f "$VENV_DIR/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    VENV_PYTHON="$VENV_DIR/bin/python"
else
    VENV_PYTHON="$VENV_DIR/Scripts/python"   # Git Bash / MSYS2 on Windows
fi

ok "venv python: $VENV_PYTHON"

# ─── 3. Install dependencies ──────────────────────────────────────────────────
header "Step 3 — Install dependencies"

step "Upgrading pip ..."
"$VENV_PYTHON" -m pip install --upgrade pip --quiet

if [[ "$DEV" -eq 1 ]]; then
    step "Installing package + dev extras ..."
    "$VENV_PYTHON" -m pip install -e ".[dev]" --quiet
else
    step "Installing package (production) ..."
    "$VENV_PYTHON" -m pip install . --quiet
fi
ok "Dependencies installed"

# ─── 4. .env file ─────────────────────────────────────────────────────────────
header "Step 4 — Environment configuration"

if [[ -f "$REPO_ROOT/.env" ]]; then
    ok ".env already exists — preserving"
elif [[ -f "$REPO_ROOT/.env.example" ]]; then
    cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
    ok "Created .env from .env.example — edit if needed"
else
    step "Writing minimal .env ..."
    printf 'THALOS_LIBRARY_PATH=./data\nTHALOS_LOG_LEVEL=%s\n' "$LOG_LEVEL" > "$REPO_ROOT/.env"
    ok "Minimal .env written"
fi

# data/ directory
DATA_DIR="$REPO_ROOT/data"
if [[ ! -d "$DATA_DIR" ]]; then
    step "Creating data/ ..."
    mkdir -p "$DATA_DIR"
    ok "data/ created"
else
    ok "data/ directory exists"
fi

# ─── 5. Action dispatch ───────────────────────────────────────────────────────
header "Step 5 — Action: '$ACTION'"

case "$ACTION" in
    clean)
        step "Cleaning build artifacts ..."
        rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov/ .coverage
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true
        ok "Clean complete"
        ;;

    test)
        step "Running test suite ..."
        "$VENV_PYTHON" -m pytest tests -v --tb=short
        ok "Tests complete"
        ;;

    validate)
        step "Running validators ..."
        "$VENV_PYTHON" tools/validate_lifecycle.py
        "$VENV_PYTHON" tools/validate_determinism.py
        "$VENV_PYTHON" tools/validate_state.py
        "$VENV_PYTHON" tools/validate_docs.py
        "$VENV_PYTHON" tools/detect_prohibited_patterns.py
        ok "Validation complete"
        ;;

    serve)
        step "Starting API server on http://${HOST}:${PORT} ..."
        echo ""
        echo "  API docs  : http://${HOST}:${PORT}/docs"
        echo "  Status    : http://${HOST}:${PORT}/api/v1/status"
        echo ""
        echo -e "  ${YELLOW}Press Ctrl+C to stop.${NC}"
        echo ""
        "$VENV_PYTHON" launch.py --host "$HOST" --port "$PORT" --log-level "$LOG_LEVEL"
        ;;

    none)
        ok "Setup complete — no action taken."
        echo ""
        echo "  Start server  : bash setup.sh --action serve"
        echo "  Run tests     : bash setup.sh --action test"
        echo "  Clean         : bash setup.sh --action clean"
        echo "  Cross-platform: python launch.py --help"
        ;;

    *)
        fail "Unknown action: $ACTION"
        ;;
esac

echo ""
ok "Done."
