# Thalos Prime NEXUS Constitution v3.0.1

**Windows-Amended Isolation Wording**

---

## Preamble

The Thalos Prime NEXUS Constitution defines the absolute operating principles, invariants, and governance rules for the NEXUS v3.0 runtime. All implementations must conform to this constitution. This version (v3.0.1) amends isolation wording for Windows 10 Home compatibility.

---

## Article I — Determinism Principle

**Section 1.1 — Absolute Determinism**
Identical inputs with identical seeds must produce identical outputs, gate results, and internal state transitions across all executions, platforms, and time.

**Section 1.2 — Seed Persistence**
All randomness must be seeded deterministically. Seeds must be persisted in `repro_manifest.json` and included in every event log entry.

**Section 1.3 — Replay Invariant**
Any evolution run must be replayable from its `repro_manifest.json`. Replay must produce gate results with a matching hash.

---

## Article II — Gate Governance

**Section 2.1 — Gate Authority**
Gates are the authoritative enforcement mechanism for all quality, security, and fitness invariants. Gate decisions are final.

**Section 2.2 — Fatal Gates**
The No-Placeholder scan gate and the Deterministic Replay gate are fatal. A fatal gate failure immediately halts execution.

**Section 2.3 — Gate Ordering**
Gates execute in declared order. No gate may be skipped except by explicit policy allowance recorded in `gate_results.json`.

**Section 2.4 — Coverage Floor**
A minimum of 80% line coverage for all required packages is a hard gate. This floor may only be raised, never lowered (ratchet principle).

---

## Article III — Isolation (Windows-Amended)

**Section 3.1 — Windows Isolation Adapter**
On Windows 10 Home, process isolation is achieved via subprocess execution with explicit timeouts. Each gate runs as a child process with bounded CPU and wall-clock time.

**Section 3.2 — Network Enforcement**
Default-deny network enforcement is implemented via Windows Firewall (netsh advfirewall) temporary rules. Rules are added before gate execution and removed after, even on error (guaranteed cleanup via try/finally).

**Section 3.3 — Rule Naming**
All temporary firewall rules are named with a unique UUID prefix (`ThalosPrime-NEXUS-{uuid}`) to prevent conflicts with existing rules.

**Section 3.4 — Dry-Run Mode**
On non-Windows platforms or when elevated privileges are unavailable, the membrane operates in dry-run mode, logging rule operations without executing netsh commands.

**Section 3.5 — No Docker Required**
The Windows isolation adapter does not require Docker, WSL, or Hyper-V. It operates natively on Windows 10 Home.

---

## Article IV — Artifact Integrity

**Section 4.1 — Required Artifacts**
Every evolution run must produce all four canonical artifacts:
- `repro_manifest.json` — reproducibility manifest
- `gate_results.json` — gate execution results
- `event_log.jsonl` — hash-chained event log
- `artifacts.json` — artifact inventory

**Section 4.2 — Hash Chain Integrity**
The event log is a hash chain. Each event entry includes the SHA-256 hash of the previous entry. The chain must be verifiable.

**Section 4.3 — Artifact Folding**
Artifacts may be folded into a zip bundle by the ER module. The bundle must include all four canonical artifacts and an SBOM.

---

## Article V — Schema Enforcement

**Section 5.1 — Strict Validation**
All genome inputs (intent, policy, fitness, lineages) must be validated against their canonical JSON Schema before ingestion. Invalid inputs are rejected with explicit error messages.

**Section 5.2 — Schema Versioning**
All schemas carry an `$id` with a version suffix. Schema changes require a new version.

---

## Article VI — Logging and Observability

**Section 6.1 — Event Log**
All state transitions, lifecycle milestones, gate executions, and reconciliation actions must be recorded in the event log.

**Section 6.2 — Event Schema**
Every event must include: `event_id`, `timestamp`, `event_type`, `data`, `prev_hash`, `entry_hash`.

**Section 6.3 — No Silent Operations**
No operation affecting system state may proceed without logging.

---

## Article VII — Prohibited Patterns

The following patterns are unconditionally prohibited:
- TODO, FIXME, STUB, PLACEHOLDER, MOCK markers in production code
- Bare `except:` or `except Exception:` without re-raise
- Silent retries without logging
- Bypassed gate enforcement
- Non-deterministic operations without explicit seeding

---

## Amendments

### Amendment 1 — Windows 10 Home Compatibility (v3.0.1)
Sections 3.1–3.5 replace the original Linux container isolation model with the Windows subprocess isolation adapter. All other articles remain unchanged.

---

*Thalos Prime NEXUS Constitution v3.0.1 — Effective immediately upon adoption.*
