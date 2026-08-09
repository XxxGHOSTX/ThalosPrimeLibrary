#!/usr/bin/env bash
# Thalos Prime — macOS launcher
# Double-click this file in Finder (or run from Terminal) to start Thalos Prime.
# Requires Python 3.12+ to be installed (https://www.python.org/downloads/).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_MIN_MAJOR=3
PYTHON_MIN_MINOR=12

_find_python() {
    for cmd in python3.12 python3.13 python3.14 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            local version
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
            local major minor
            major="${version%%.*}"
            minor="${version#*.}"
            minor="${minor%%.*}"
            if [[ "$major" -gt "$PYTHON_MIN_MAJOR" ]] || \
               { [[ "$major" -eq "$PYTHON_MIN_MAJOR" ]] && [[ "$minor" -ge "$PYTHON_MIN_MINOR" ]]; }; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    echo ""
    return 1
}

PYTHON=$(_find_python || true)
if [[ -z "$PYTHON" ]]; then
    osascript -e 'display alert "Python 3.12+ not found" message "Please install Python 3.12 or later from https://www.python.org/downloads/ and try again." as critical' 2>/dev/null || true
    echo "ERROR: Python 3.12+ is required. Install from https://www.python.org/downloads/" >&2
    exit 1
fi

cd "$SCRIPT_DIR"

# Create / reuse virtual environment
VENV_DIR="$SCRIPT_DIR/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

VENV_PYTHON="$VENV_DIR/bin/python"

# Install / upgrade dependencies once
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
if [[ -f "$SCRIPT_DIR/pyproject.toml" ]]; then
    "$VENV_PYTHON" -m pip install --quiet -e "$SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/requirements.txt" ]]; then
    "$VENV_PYTHON" -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
fi

# Copy .env from .env.example if not present
if [[ ! -f "$SCRIPT_DIR/.env" ]] && [[ -f "$SCRIPT_DIR/.env.example" ]]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
fi

# Load .env into environment
if [[ -f "$SCRIPT_DIR/.env" ]]; then
    set -o allexport
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env" || true
    set +o allexport
fi

HOST="${THALOS_HOST:-127.0.0.1}"
PORT="${THALOS_PORT:-8000}"

echo "Starting Thalos Prime on http://${HOST}:${PORT}"
echo "All background workers active: coherence enforcement, adaptive search, benchmarking, audit health."
echo "Press Ctrl+C to stop."

# Open browser after brief delay (macOS)
(sleep 3 && open "http://${HOST}:${PORT}") &

exec "$VENV_PYTHON" -m thalos_prime --host "$HOST" --port "$PORT"
