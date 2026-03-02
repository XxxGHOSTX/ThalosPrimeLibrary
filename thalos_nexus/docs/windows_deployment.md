# Windows Deployment Guide — Thalos Prime NEXUS Core v1

## Prerequisites

| Requirement | Minimum version |
|-------------|----------------|
| Python | 3.12 |
| Windows | 10 Home (build 19041+) |
| pip | 23.0+ |

Administrator privileges are required for Windows Firewall rule management
during isolated `evolve` runs.

---

## Bootstrap

### 1. Install the package

```powershell
pip install -e ".[dev,nexus]"
```

The `dev,nexus` extras install:

- `jsonschema>=4.21.0` — manifest schema validation
- `cryptography>=42.0.0` — ed25519 key generation and signing
- `ruff`, `mypy` — required by the static-analysis gate
- `pytest`, `hypothesis` — required by the acceptance and property-tests gates
- `pip-audit` — required by the security gate
- `mutmut` — required by the mutation-tests gate

### 2. Verify the installation

```powershell
python -m thalos_nexus.cli --help
```

Expected output lists the three sub-commands: `ingest-genome`, `evolve`, `replay`.

---

## Generating ed25519 Keys

Keys are generated automatically on first use and stored in
`%USERPROFILE%\.thalos_nexus\keys\` (default).  To use a custom location:

```powershell
python -m thalos_nexus.cli ingest-genome --path genome.bin --key-dir C:\keys\nexus
```

The key directory will contain:

- `private.pem` — PKCS#8 PEM-encoded private key (**keep this secret**)
- `public.pem` — SubjectPublicKeyInfo PEM-encoded public key

To retrieve the hex-encoded public key for use with `replay --key`:

```python
from thalos_nexus.attest.signing import KeyPair
from pathlib import Path
kp = KeyPair.load(Path(r"C:\keys\nexus"))
print(kp.public_key_hex())
```

---

## Running the CLI

### ingest-genome

Ingests a genome file, computes its SHA-256 hash, creates a zip bundle
(`trait_bundle.zip`), generates a CycloneDX SBOM, and writes a signed
`repro_manifest.json` to `nexus_runs\{genome_hash}\`.

```powershell
python -m thalos_nexus.cli ingest-genome `
    --path C:\data\genome.bin `
    --key-dir C:\keys\nexus `
    --out-dir C:\nexus_runs
```

Output: the genome SHA-256 hash printed to stdout.

### evolve

Runs all six hard gates against a target directory, writes `gate_results.json`,
`event_log.jsonl`, and a signed `repro_manifest.json` to the run directory.

```powershell
python -m thalos_nexus.cli evolve `
    --genome <genome_sha256_hex> `
    --task "my_task" `
    --seed 42 `
    --target-dir C:\my_project `
    --key-dir C:\keys\nexus
```

On Windows, the `IsolationAdapter` is activated automatically, running gate
subprocesses inside ephemeral workspaces with Job Object limits and firewall
network-egress blocking.  On non-Windows platforms the `evolve` command
exits immediately with a non-zero exit code.

### replay

Verifies artifact integrity, event-log hash chain, and (optionally) the
ed25519 signature of a repro_manifest.

```powershell
python -m thalos_nexus.cli replay `
    --repro-manifest C:\nexus_runs\<run_id>\repro_manifest.json `
    --key <public_key_hex>
```

Prints `PASS` or `FAIL`.  Exit code is 0 for PASS, 1 for FAIL.

---

## Windows Sandbox Internals

### Job Objects (memory and CPU limits)

The `IsolationAdapter` creates a Windows Job Object for each subprocess via
`CreateJobObjectW` and `SetInformationJobObject` (ctypes, no third-party
dependency).  The following limits are enforced:

| Limit | Default |
|-------|---------|
| `ProcessMemoryLimit` | `max_memory_mb` × 1 MiB (default 512 MiB) |
| `JobMemoryLimit` | same |

If the ctypes calls fail (e.g. insufficient privilege), a warning is logged
and execution continues without memory limits inside the ephemeral workspace.

### Firewall rules (network isolation)

When `enable_network=False` (the default), an outbound-block rule is added
before the subprocess starts:

```
netsh advfirewall firewall add rule name="thalos_nexus_{uuid}_block" \
    dir=out action=block program="{executable_path}"
```

The rule is removed in the `finally` block regardless of outcome:

```
netsh advfirewall firewall delete rule name="thalos_nexus_{uuid}_block"
```

Rule names are unique per run (UUID4) to avoid collisions under parallel
execution.

### Ephemeral workspaces

Each `IsolationAdapter.run()` call creates a temporary directory under
`config.workspace_base` using `tempfile.mkdtemp`.  The directory is deleted
in the `finally` block, even on subprocess failure or timeout.

---

## Verifying Replay

After an `evolve` run, the repro_manifest embeds SHA-256 digests of every
artifact.  `replay` re-derives each digest and verifies the event-log
hash chain:

```
chain_hash[n] = SHA-256(prev_hash_bytes || canonical_json(entry_core[n]))
```

where `entry_core` contains `seq`, `timestamp`, `event_type`, `payload`,
and `prev_hash`.  The genesis entry uses `"0" * 64` as `prev_hash`.

Any modification to a log entry — including timestamp or payload — breaks
the chain and is reported as an error.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `WindowsRequiredError` | Running `evolve` on Linux/macOS | Run `evolve` on Windows 10+ (or in a Windows VM); the `evolve` command requires Windows for isolation and is not supported on other platforms |
| `CreateJobObjectW returned NULL` | Insufficient privilege | Run as Administrator |
| `cyclonedx-py unavailable` | Tool not installed | `pip install cyclonedx-bom`; otherwise the minimal fallback SBOM is used |
| `Signature verification failed` | Wrong `--key` value | Retrieve the correct public key hex from the key directory |
