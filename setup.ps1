#Requires -Version 5.1
<#
.SYNOPSIS
    ThalosPrimeLibrary — Windows-first automated setup and launch script.

.DESCRIPTION
    One-shot setup for Windows (PowerShell 5.1+).
    - Validates Python >= 3.12
    - Creates/reuses a virtual environment
    - Installs all dependencies from pyproject.toml
    - Writes a .env file if one does not exist
    - Offers to launch the API server, run tests, or clean build artifacts

    Other OS users: run `bash setup.sh` (Linux / macOS) or
    `python launch.py` (cross-platform).

.PARAMETER Action
    What to do after setup.
    Valid values: serve, test, validate, clean, none  (default: serve)

.PARAMETER Host
    API server bind host  (default: 127.0.0.1)

.PARAMETER Port
    API server bind port  (default: 8000)

.PARAMETER LogLevel
    Logging verbosity: DEBUG | INFO | WARNING | ERROR | CRITICAL  (default: INFO)

.PARAMETER Dev
    Install development dependencies as well  (default: true)

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 -Action test
    .\setup.ps1 -Action serve -Port 9000
    .\setup.ps1 -Action clean

.NOTES
    Run from the repository root:
        Set-Location <repo-root>; .\setup.ps1

    If execution policy blocks the script:
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#>
[CmdletBinding()]
param (
    [ValidateSet("serve", "test", "validate", "clean", "none")]
    [string]$Action   = "serve",

    [string]$Host     = "127.0.0.1",
    [int]   $Port     = 8000,

    [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")]
    [string]$LogLevel = "INFO",

    [bool]  $Dev      = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ─── Helpers ──────────────────────────────────────────────────────────────────

function Write-Header ([string]$text) {
    Write-Host ""
    Write-Host ("=" * 62) -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host ("=" * 62) -ForegroundColor Cyan
}

function Write-Step ([string]$text) {
    Write-Host "  >> $text" -ForegroundColor Yellow
}

function Write-OK ([string]$text) {
    Write-Host "  [OK] $text" -ForegroundColor Green
}

function Write-Warn ([string]$text) {
    Write-Host "  [WARN] $text" -ForegroundColor Magenta
}

function Write-Fail ([string]$text) {
    Write-Host "  [FAIL] $text" -ForegroundColor Red
}

# ─── Locate repository root ───────────────────────────────────────────────────

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Header "ThalosPrimeLibrary — Windows Setup & Launch"
Write-Host "  Repository : $RepoRoot"
Write-Host "  Action     : $Action"
Write-Host "  Host:Port  : ${Host}:${Port}"
Write-Host "  Log level  : $LogLevel"

# ─── 1. Check Python >= 3.12 ─────────────────────────────────────────────────

Write-Header "Step 1 — Python version check"

$PythonCandidates = @("python", "python3", "py")
$PythonExe = $null

foreach ($candidate in $PythonCandidates) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 12)) {
                $PythonExe = $candidate
                Write-OK "Found $ver ($candidate)"
                break
            }
            else {
                Write-Warn "$ver is below 3.12 — skipping '$candidate'"
            }
        }
    }
    catch {
        # not found — try next
    }
}

if (-not $PythonExe) {
    Write-Fail "Python >= 3.12 not found. Download from https://www.python.org/downloads/"
    Write-Host ""
    Write-Host "  After installing Python 3.12+, re-run this script." -ForegroundColor Yellow
    exit 1
}

# ─── 2. Virtual environment ───────────────────────────────────────────────────

Write-Header "Step 2 — Virtual environment"

$VenvDir = Join-Path $RepoRoot ".venv"

if (Test-Path $VenvDir) {
    Write-OK "Existing .venv found — reusing"
}
else {
    Write-Step "Creating .venv ..."
    & $PythonExe -m venv $VenvDir
    Write-OK ".venv created"
}

# Locate venv python/pip
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip    = Join-Path $VenvDir "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    # Fallback for some venv layouts
    $VenvPython = Join-Path $VenvDir "bin\python"
    $VenvPip    = Join-Path $VenvDir "bin\pip"
}

Write-OK "venv python : $VenvPython"

# ─── 3. Install dependencies ──────────────────────────────────────────────────

Write-Header "Step 3 — Install dependencies"

Write-Step "Upgrading pip ..."
& $VenvPython -m pip install --upgrade pip --quiet

if ($Dev) {
    Write-Step "Installing package + dev extras ..."
    & $VenvPython -m pip install -e ".[dev]" --quiet
}
else {
    Write-Step "Installing package (production) ..."
    & $VenvPython -m pip install . --quiet
}

Write-OK "Dependencies installed"

# ─── 4. Ensure .env file ─────────────────────────────────────────────────────

Write-Header "Step 4 — Environment configuration"

$EnvFile    = Join-Path $RepoRoot ".env"
$EnvExample = Join-Path $RepoRoot ".env.example"

if (Test-Path $EnvFile) {
    Write-OK ".env already exists — preserving"
}
elseif (Test-Path $EnvExample) {
    Copy-Item $EnvExample $EnvFile
    Write-OK "Created .env from .env.example — edit if needed"
}
else {
    Write-Step "Writing minimal .env ..."
    @"
THALOS_LIBRARY_PATH=./data
THALOS_LOG_LEVEL=$LogLevel
"@ | Set-Content $EnvFile -Encoding UTF8
    Write-OK "Minimal .env written"
}

# ─── 5. Data directory ───────────────────────────────────────────────────────

$DataDir = Join-Path $RepoRoot "data"
if (-not (Test-Path $DataDir)) {
    Write-Step "Creating data/ directory ..."
    New-Item -ItemType Directory -Path $DataDir | Out-Null
    Write-OK "data/ created"
}
else {
    Write-OK "data/ directory exists"
}

# ─── 6. Action dispatch ───────────────────────────────────────────────────────

Write-Header "Step 5 — Action: '$Action'"

switch ($Action) {

    "clean" {
        Write-Step "Cleaning build artifacts ..."
        $targets = @("build", "dist", "*.egg-info", ".pytest_cache", ".mypy_cache",
                     ".ruff_cache", "htmlcov", ".coverage")
        foreach ($t in $targets) {
            Get-ChildItem -Path $RepoRoot -Include $t -Recurse -Force -ErrorAction SilentlyContinue |
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        }
        Get-ChildItem -Path $RepoRoot -Include "__pycache__" -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        Get-ChildItem -Path $RepoRoot -Include "*.pyc" -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
        Write-OK "Clean complete"
    }

    "test" {
        Write-Step "Running test suite ..."
        & $VenvPython -m pytest tests -v --tb=short
        Write-OK "Tests complete"
    }

    "validate" {
        Write-Step "Running lifecycle validator ..."
        & $VenvPython tools/validate_lifecycle.py
        Write-Step "Running determinism validator ..."
        & $VenvPython tools/validate_determinism.py
        Write-Step "Running state validator ..."
        & $VenvPython tools/validate_state.py
        Write-Step "Running docs validator ..."
        & $VenvPython tools/validate_docs.py
        Write-Step "Running prohibited-patterns detector ..."
        & $VenvPython tools/detect_prohibited_patterns.py
        Write-OK "Validation complete"
    }

    "serve" {
        Write-Step "Starting API server on http://${Host}:${Port} ..."
        Write-Host ""
        Write-Host "  API docs  : http://${Host}:${Port}/docs"
        Write-Host "  Status    : http://${Host}:${Port}/api/v1/status"
        Write-Host ""
        Write-Host "  Press Ctrl+C to stop." -ForegroundColor Yellow
        Write-Host ""
        & $VenvPython launch.py --host $Host --port $Port --log-level $LogLevel
    }

    "none" {
        Write-OK "Setup complete — no action taken."
        Write-Host ""
        Write-Host "  To start the server:  .\setup.ps1 -Action serve" -ForegroundColor Cyan
        Write-Host "  To run tests:         .\setup.ps1 -Action test"  -ForegroundColor Cyan
        Write-Host "  To clean artifacts:   .\setup.ps1 -Action clean" -ForegroundColor Cyan
        Write-Host "  Cross-platform:       python launch.py --help"    -ForegroundColor Cyan
    }

}

Write-Host ""
Write-OK "Done."
