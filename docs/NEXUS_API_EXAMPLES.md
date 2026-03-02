# Thalos Prime NEXUS v3.0 — API Integration Examples & CLI Usage

---

## CLI Reference

### Global Options

```
usage: thalos-nexus [-h] [--version] [--log-level {DEBUG,INFO,WARNING,ERROR}] COMMAND ...

options:
  --version                     Show version and exit
  --log-level {DEBUG,INFO,WARNING,ERROR}
                                Logging verbosity (default: WARNING)
```

---

### `ingest-genome`

Ingest, validate, and sign a genome file.

```cmd
python -m thalos_nexus.cli ingest-genome <genome_file>
```

**Arguments:**
- `genome_file` — Path to a JSON genome file

**Example:**
```cmd
python -m thalos_nexus.cli ingest-genome my_genome.json
```

**Output:**
```
Genome ingested successfully.
  ID:        my-first-genome
  Hash:      sha256:a3f1c2d4e5...
  Signature: hmac-sha256:7b8e9f0a...
  Signed at: 2026-03-02T17:54:28.982Z
```

---

### `evolve`

Run the full gate suite and emit all artifacts.

```cmd
python -m thalos_nexus.cli evolve [--genome <file>] [--output-dir <dir>] [--seed <int>]
```

**Options:**
- `--genome <file>` — Genome file (default: `genome.json`)
- `--output-dir <dir>` — Output directory (default: `nexus_out`)
- `--seed <int>` — Deterministic seed (default: 42)

**Example:**
```cmd
python -m thalos_nexus.cli evolve --genome my_genome.json --output-dir ./results --seed 42
```

**Output files in `./results/`:**
- `repro_manifest.json`
- `gate_results.json`
- `event_log.jsonl`
- `artifacts.json`
- `sbom.json`
- `bundle.zip`

---

### `replay`

Verify deterministic replay from a repro_manifest.json.

```cmd
python -m thalos_nexus.cli replay [--manifest <file>] [--output-dir <dir>]
```

**Options:**
- `--manifest <file>` — Path to repro_manifest.json (default: `nexus_out/repro_manifest.json`)
- `--output-dir <dir>` — Output directory for replay artifacts (default: `nexus_replay`)

**Example:**
```cmd
python -m thalos_nexus.cli replay --manifest ./results/repro_manifest.json
```

**Output:**
```
Replay verification: PASSED
  Original hash:  sha256:abc123...
  Replayed hash:  sha256:abc123...
  Match: True
```

---

### `traits`

Show genome traits summary.

```cmd
python -m thalos_nexus.cli traits [--genome <file>]
```

**Options:**
- `--genome <file>` — Genome file (default: `genome.json`)

**Example:**
```cmd
python -m thalos_nexus.cli traits --genome my_genome.json
```

**Output:**
```
Genome Traits
  Intent ID:     my-first-genome
  Description:   My first NEXUS genome
  Objectives:    2
    - validate code quality
    - ensure test coverage
  Policy ID:     default-policy
  Rules:         1
  Global Floor:  80.0%
  Ratchet:       True
  Lineages:      1
```

---

### `immunome`

Show gate health / immunome status from gate_results.json.

```cmd
python -m thalos_nexus.cli immunome [--output-dir <dir>]
```

**Options:**
- `--output-dir <dir>` — Output directory containing gate_results.json (default: `nexus_out`)

**Example:**
```cmd
python -m thalos_nexus.cli immunome --output-dir ./results
```

**Output:**
```
Immunome Status
  Overall: PASSED
  Total duration: 42.7s

  Gate Results:
  ✓ no-placeholder-scan      0.3s  [FATAL]
  ✓ static-analysis          5.1s
  ✓ security-scan            8.2s
  ✓ acceptance-tests        12.4s
  ✓ property-tests           4.1s
  ✗ mutation-resilience      9.2s  [SKIPPED]
  ✓ deterministic-replay     1.1s  [FATAL]
  ✓ coverage-enforcement     2.3s
```

---

## Python API Examples

### Ingesting a Genome

```python
from thalos_nexus.nucleus import ingest_genome

bundle = ingest_genome("my_genome.json")
print(f"Genome ID: {bundle.genome_id}")
print(f"Hash: sha256:{bundle.genome_hash}")
print(f"Signature: hmac-sha256:{bundle.signature}")
```

### Running Gates

```python
from thalos_nexus.lysosome import GateRunner
from thalos_nexus.gates import STANDARD_GATES

runner = GateRunner(gates=STANDARD_GATES, timeout_seconds=300.0)
results = runner.run(cwd=".")
print(f"All passed: {results.all_passed}")
for gate in results.results:
    status = "✓" if gate.passed else "✗"
    print(f"  {status} {gate.gate_name}: {gate.duration_seconds:.1f}s")
```

### Using the Budget Governor

```python
from thalos_nexus.mitochondria import BudgetGovernor
from thalos_nexus.gates import STANDARD_GATES

governor = BudgetGovernor(total_budget_seconds=600.0)
governor.start()

for gate in STANDARD_GATES:
    budget = governor.allocate_gate_budget(gate.name)
    print(f"Gate {gate.name}: budget {budget:.1f}s")
    if governor.is_over_budget():
        print("Budget exhausted, stopping")
        break
```

### Using the Determinism Spine

```python
import pathlib
from thalos_nexus.spine import DeterminismSpine

spine = DeterminismSpine(output_dir=pathlib.Path("nexus_out"))
spine.emit_event("evolution_started", {"seed": 42})
spine.write_repro_manifest(
    seed=42,
    config_hash="sha256:abc123",
    genome_hash="sha256:def456",
)
```

### Folding Artifacts

```python
from thalos_nexus.er import ArtifactFolder

folder = ArtifactFolder(output_dir="nexus_out")
bundle_path = folder.fold(
    files=["nexus_out/repro_manifest.json", "nexus_out/gate_results.json"]
)
print(f"Bundle: {bundle_path}")

sbom_path = folder.generate_sbom(
    packages=["jsonschema", "ruff", "mypy"],
    output_path="nexus_out/sbom.json",
)
```

### Tool Registry

```python
from thalos_nexus.cytoplasm import ToolRegistry, ToolEnvelope

registry = ToolRegistry()
registry.register(ToolEnvelope(
    name="ruff",
    command="ruff",
    default_args=["check", "."],
    description="Fast Python linter",
))

result = registry.execute("ruff", extra_args=["--output-format=text"])
print(result.stdout)
```

### Membrane Gateway (Windows Firewall)

```python
from thalos_nexus.membrane import MembraneGateway

# dry_run=True on non-Windows or without elevation
with MembraneGateway(allowed_hosts=["pypi.org"], dry_run=False) as gw:
    print(f"Active rule: {gw.rule_name}")
    # Run gated operations here
# Rule is removed here (guaranteed cleanup)
```
