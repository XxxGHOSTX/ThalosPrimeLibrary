# Thalos Prime NEXUS v3.0 — Windows 10 Home Install & Deploy Guide

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Windows 10 Home | 1903+ | All editions supported |
| Python | 3.12+ | From python.org |
| Git | Any | Optional, for cloning |

No Docker, WSL, Hyper-V, or admin rights required for basic operation.
> **Note:** The `membrane` module (Windows Firewall enforcement) requires elevated privileges (Run as Administrator). All other modules work without elevation.

---

## Installation

### Step 1 — Install Python 3.12

Download from [python.org](https://www.python.org/downloads/) and install.

Verify:
```cmd
python --version
```

### Step 2 — Clone or Download the Repository

```cmd
git clone https://github.com/XxxGHOSTX/ThalosPrimeLibrary.git
cd ThalosPrimeLibrary
```

Or download and extract the ZIP from GitHub.

### Step 3 — Install the Package

Install with dev dependencies:
```cmd
pip install -e ".[dev]"
```

Install core only:
```cmd
pip install -e .
```

### Step 4 — Verify Installation

```cmd
python -m thalos_nexus.cli --help
```

Expected output:
```
usage: thalos-nexus [-h] [--version] [--log-level {DEBUG,INFO,WARNING,ERROR}] COMMAND ...

Thalos Prime NEXUS v3.0.0 — deterministic genome evolution toolkit
...
```

---

## Quick Start

### Create a Genome File

Create `my_genome.json`:
```json
{
  "intent": {
    "version": "1.0.0",
    "id": "my-first-genome",
    "description": "My first NEXUS genome",
    "objectives": ["validate code quality", "ensure test coverage"]
  },
  "policy": {
    "version": "1.0.0",
    "id": "default-policy",
    "rules": [
      {"id": "r1", "effect": "allow", "action": "run-gate"}
    ]
  },
  "fitness": {
    "version": "1.0.0",
    "global_floor": 80.0,
    "thresholds": {"coverage": 80.0},
    "ratchet": true
  },
  "lineages": [
    {"id": "gen-0", "parent_id": null, "version": "1.0.0"}
  ]
}
```

### Ingest the Genome

```cmd
python -m thalos_nexus.cli ingest-genome my_genome.json
```

Output:
```
Genome ingested successfully.
  ID:        my-first-genome
  Hash:      sha256:abc123...
  Signature: hmac-sha256:def456...
  Signed at: 2026-03-02T17:54:28.982Z
```

### Run the Gate Suite (Evolve)

```cmd
python -m thalos_nexus.cli evolve --genome my_genome.json --output-dir nexus_out
```

Output directory will contain:
- `repro_manifest.json`
- `gate_results.json`
- `event_log.jsonl`
- `artifacts.json`
- `sbom.json`
- `bundle.zip`

### Verify Deterministic Replay

```cmd
python -m thalos_nexus.cli replay --manifest nexus_out\repro_manifest.json
```

### Show Genome Traits

```cmd
python -m thalos_nexus.cli traits --genome my_genome.json
```

### Show Gate Health (Immunome)

```cmd
python -m thalos_nexus.cli immunome --output-dir nexus_out
```

---

## Running Tests

```cmd
python -m pytest tests/test_thalos_nexus.py -v
```

With coverage:
```cmd
python -m pytest tests/test_thalos_nexus.py -v --cov=thalos_nexus --cov-report=term-missing
```

---

## Windows Firewall (Membrane Module)

The membrane module uses `netsh advfirewall` for temporary network enforcement.

**Requires:** Run as Administrator

To use in code:
```python
from thalos_nexus.membrane import MembraneGateway

with MembraneGateway(allowed_hosts=["pypi.org"]) as gw:
    # Temporary block rule is active
    pass  # Rule is removed here (even on error)
```

On Windows 10 Home without elevation, membrane operates in **dry-run mode** — it logs operations but does not execute netsh commands.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `THALOS_NEXUS_SIGNING_KEY` | `thalos-nexus-dev-key-v1` | HMAC-SHA256 signing key for genome bundles |

> **Security:** Always set `THALOS_NEXUS_SIGNING_KEY` to a strong random value in production:
> ```cmd
> set THALOS_NEXUS_SIGNING_KEY=my-strong-random-key-here
> ```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'thalos_nexus'`
Run `pip install -e .` from the repository root.

### `jsonschema not found`
Run `pip install jsonschema>=4.21.0` or reinstall with `pip install -e ".[dev]"`.

### `netsh command not found` / Firewall errors
The membrane module requires elevated privileges. Run your terminal as Administrator, or accept dry-run mode for development.

### `mutmut not found`
Install with: `pip install mutmut>=2.4.0`

---

## Linting and Type Checking

```cmd
ruff check thalos_nexus/
mypy thalos_nexus/ --strict
```
