# Thalos Prime NEXUS v3.0 — Full-Stack Specification

---

## Overview

Thalos Prime NEXUS v3.0 is a deterministic genome evolution toolkit implementing strict control-plane / data-plane separation. It provides a complete pipeline from genome ingestion through gate-enforced quality evolution to reproducible artifact generation.

---

## Architecture Layers

### Layer 0 — Determinism Spine (`thalos_nexus.spine`)

The spine is the authoritative state surface for all evolution runs.

**Outputs:**
- `repro_manifest.json` — seed, config hash, version, platform, genome hash
- `event_log.jsonl` — hash-chained append-only event log
- `gate_results.json` — per-gate results with pass/fail, exit codes, durations
- `artifacts.json` — artifact inventory with paths and metadata

**Hash Chain:** Each JSONL entry includes `prev_hash` (SHA-256 of the previous entry) and `entry_hash` (SHA-256 of the current entry's canonical JSON). The chain root uses `"0" * 64` as the genesis hash.

---

### Layer 1 — Nucleus (`thalos_nexus.nucleus`)

Handles genome ingestion and signing.

**Inputs:** A JSON genome file with four sections: `intent`, `policy`, `fitness`, `lineages`.

**Validation:** Each section is validated against its canonical JSON Schema (stored in `thalos_nexus/schemas/`).

**Hashing:** The canonical genome JSON (sorted keys, no whitespace) is hashed with SHA-256.

**Signing:** The bundle is signed with HMAC-SHA256 using a key from the `THALOS_NEXUS_SIGNING_KEY` environment variable (default: `thalos-nexus-dev-key-v1` for development).

**Output:** `GenomeBundle` dataclass with `genome_id`, `genome_hash`, `signature`, `intent`, `policy`, `fitness`, `lineages`, `created_at`.

---

### Layer 2 — Lysosome (`thalos_nexus.lysosome`)

Deterministic gate runner with Windows isolation adapter.

**Gate Execution:** Each gate is a list of subprocess commands run in order. Each command runs as a child process with explicit timeout.

**Windows Isolation Adapter:** Uses `subprocess.run()` with `capture_output=True`, `text=True`, `timeout=<budget>`. No shell=True. No Docker or WSL required.

**Gate Results:** Per-gate: name, passed, exit_code, stdout, stderr, duration_seconds, fatal.

**Fatal Handling:** If a fatal gate fails, execution halts immediately. Remaining gates are recorded as skipped.

---

### Layer 3 — Membrane (`thalos_nexus.membrane`)

Capability gateway with default-deny network enforcement.

**Windows Firewall:** Uses `netsh advfirewall firewall add rule` to create a temporary block rule before gate execution. Uses `netsh advfirewall firewall delete rule` to remove it after (guaranteed via try/finally).

**Rule Isolation:** Each `MembraneGateway` instance generates a UUID-based rule name to prevent conflicts.

**Dry-Run:** On non-Windows or when elevation is unavailable, operates in dry_run mode — logs all operations without executing netsh.

**Context Manager:** `with MembraneGateway(allowed_hosts=["pypi.org"]) as gw:` — adds rule on enter, removes on exit.

---

### Layer 4 — Mitochondria (`thalos_nexus.mitochondria`)

Scheduler and budget governor.

**Budget Tracking:** Tracks wall-clock elapsed time against a total budget in seconds.

**Gate Allocation:** Divides remaining budget equally among remaining gates.

**Over-Budget:** `is_over_budget()` returns True when elapsed > total_budget. Does not forcibly kill processes; signals to the caller that budget is exhausted.

---

### Layer 5 — Cytoplasm (`thalos_nexus.cytoplasm`)

Tool registry for local tool envelopes.

**ToolEnvelope:** `name`, `command`, `default_args`, `description`.

**ToolRegistry:** Registers, retrieves, lists, and executes tools. Uses `subprocess.run()` for execution. Raises `ToolNotFoundError` for missing tools.

**Built-in Tools:** ruff, mypy, pytest, pip-audit, mutmut.

---

### Layer 6 — ER (`thalos_nexus.er`)

Artifact folding and SBOM generation.

**Artifact Folding:** Zips specified files into a `bundle.zip` in the output directory. Missing files are recorded in a `missing_files` list and logged as warnings.

**SBOM Generation:** Generates a JSON Software Bill of Materials with entries for each installed package (name, version, license if available). Uses `importlib.metadata` for installed package info.

**SBOMEntry:** `name`, `version`, `license`.

---

### Layer 7 — Gates (`thalos_nexus.gates`)

Hard gate definitions.

| Gate | Fatal | Description |
|------|-------|-------------|
| no-placeholder-scan | Yes | Scans for TODO/FIXME/STUB/PLACEHOLDER/MOCK markers |
| static-analysis | No | ruff check + mypy --strict |
| security-scan | No | pip-audit for known vulnerabilities |
| acceptance-tests | No | pytest test suite |
| property-tests | No | pytest with hypothesis |
| mutation-resilience | No | mutmut mutation testing |
| deterministic-replay | Yes | Verifies replay hash matches |
| coverage-enforcement | No | pytest --cov-fail-under=80 |

---

### Layer 8 — CLI (`thalos_nexus.cli`)

**Entry point:** `python -m thalos_nexus.cli`

**Subcommands:**

| Command | Description |
|---------|-------------|
| `ingest-genome <file>` | Ingest, validate, sign genome; print bundle summary |
| `evolve` | Run full gate suite; emit all artifacts |
| `replay` | Load repro_manifest; verify replay determinism |
| `traits` | Show genome traits (intent objectives, policy rules, fitness thresholds) |
| `immunome` | Show gate health from gate_results.json |

**Flags:**
- `--log-level {DEBUG,INFO,WARNING,ERROR}` — logging verbosity
- `--version` — show version
- `--genome <file>` — genome file for evolve/traits
- `--output-dir <dir>` — output directory for evolve (default: `nexus_out`)
- `--manifest <file>` — repro_manifest.json for replay

---

## Canonical Formats

See `docs/NEXUS_CANONICAL_FORMATS.md` for JSON schema details.

---

## Deterministic Guarantees

- Evolution with identical genome + seed + config always produces identical `gate_results.json`.
- The event log hash chain is verifiable offline.
- `replay` re-runs evolution and compares the gate results SHA-256 hash against the stored hash in `repro_manifest.json`.

---

## State Surfaces

| Surface | Location | Format |
|---------|----------|--------|
| Repro manifest | `<output_dir>/repro_manifest.json` | JSON |
| Event log | `<output_dir>/event_log.jsonl` | JSONL (hash chain) |
| Gate results | `<output_dir>/gate_results.json` | JSON |
| Artifact inventory | `<output_dir>/artifacts.json` | JSON |
| SBOM | `<output_dir>/sbom.json` | JSON |
| Artifact bundle | `<output_dir>/bundle.zip` | ZIP |

---

## Security

- No secrets in source code. Signing key from `THALOS_NEXUS_SIGNING_KEY` env var.
- All inputs validated against JSON Schema before use.
- No shell=True in any subprocess call.
- Firewall rules cleaned up even on error.
