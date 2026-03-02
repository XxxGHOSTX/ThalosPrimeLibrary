# Thalos Prime NEXUS v3.0 — Canonical Formats

---

## 1. Genome File Format

A genome file is a JSON object with four top-level keys. Each section is validated against its canonical schema.

```json
{
  "intent": { ... },
  "policy": { ... },
  "fitness": { ... },
  "lineages": [ ... ]
}
```

### 1.1 Intent Section

Schema: `thalos_nexus/schemas/intent.schema.json`

```json
{
  "version": "1.0.0",
  "id": "my-intent-001",
  "description": "Evolve a deterministic analysis pipeline",
  "objectives": [
    "achieve 95% test coverage",
    "pass all hard gates",
    "maintain deterministic replay"
  ]
}
```

### 1.2 Policy Section

Schema: `thalos_nexus/schemas/policy.schema.json`

```json
{
  "version": "1.0.0",
  "id": "my-policy-001",
  "rules": [
    {"id": "r1", "effect": "allow", "action": "run-gate"},
    {"id": "r2", "effect": "deny", "action": "skip-fatal-gate"}
  ]
}
```

### 1.3 Fitness Section

Schema: `thalos_nexus/schemas/fitness.schema.json`

```json
{
  "version": "1.0.0",
  "global_floor": 80.0,
  "thresholds": {
    "coverage": 80.0,
    "mutation_score": 60.0
  },
  "ratchet": true
}
```

`ratchet: true` means the global_floor can only increase over time (never decrease).

### 1.4 Lineages Section

Schema: `thalos_nexus/schemas/lineages.schema.json`

```json
[
  {"id": "gen-0", "parent_id": null, "version": "1.0.0"},
  {"id": "gen-1", "parent_id": "gen-0", "version": "1.0.1", "tags": ["stable"]}
]
```

---

## 2. Genome Bundle (Signed)

Produced by `nucleus.ingest_genome()`. This is the in-memory representation after ingestion.

```json
{
  "genome_id": "my-intent-001",
  "genome_hash": "a3f1c2d4...",
  "signature": "7b8e9f0a...",
  "intent": { ... },
  "policy": { ... },
  "fitness": { ... },
  "lineages": [ ... ],
  "created_at": "2026-03-02T17:54:28.982Z"
}
```

---

## 3. Repro Manifest

File: `<output_dir>/repro_manifest.json`
Schema: `thalos_nexus/schemas/repro_manifest.schema.json`

```json
{
  "schema_version": "1.0.0",
  "seed": 42,
  "config_hash": "sha256:abc123...",
  "thalos_nexus_version": "3.0.0",
  "python_version": "3.12.0",
  "platform": "Windows-10-...",
  "created_at": "2026-03-02T17:54:28.982Z",
  "genome_hash": "a3f1c2d4..."
}
```

---

## 4. Gate Results

File: `<output_dir>/gate_results.json`
Schema: `thalos_nexus/schemas/gate_results.schema.json`

```json
{
  "schema_version": "1.0.0",
  "all_passed": true,
  "total_duration_seconds": 42.7,
  "gates": [
    {
      "name": "no-placeholder-scan",
      "passed": true,
      "exit_code": 0,
      "duration_seconds": 0.3,
      "fatal": true,
      "stdout": "",
      "stderr": ""
    }
  ]
}
```

---

## 5. Event Log

File: `<output_dir>/event_log.jsonl`

Each line is a JSON object. The log is a hash chain — each entry's `entry_hash` is SHA-256 of the entry's canonical JSON (sorted keys), and `prev_hash` references the previous entry's `entry_hash`.

```json
{"event_id": "evt-001", "timestamp": "2026-03-02T17:54:28Z", "event_type": "evolution_started", "data": {"seed": 42}, "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000", "entry_hash": "d4e5f6..."}
{"event_id": "evt-002", "timestamp": "2026-03-02T17:54:29Z", "event_type": "gate_started", "data": {"gate": "no-placeholder-scan"}, "prev_hash": "d4e5f6...", "entry_hash": "a1b2c3..."}
```

---

## 6. Artifact Inventory

File: `<output_dir>/artifacts.json`

```json
{
  "artifacts": [
    {
      "name": "repro_manifest.json",
      "path": "nexus_out/repro_manifest.json",
      "size_bytes": 312,
      "sha256": "abc123..."
    }
  ]
}
```

---

## 7. SBOM Format

File: `<output_dir>/sbom.json`

```json
{
  "sbom_version": "1.0.0",
  "generated_at": "2026-03-02T17:54:28Z",
  "packages": [
    {"name": "jsonschema", "version": "4.21.0", "license": "MIT"},
    {"name": "ruff", "version": "0.2.0", "license": "MIT"}
  ]
}
```
