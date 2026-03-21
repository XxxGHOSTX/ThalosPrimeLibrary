<!-- PROPRIETARY AND CONFIDENTIAL -->
<!-- Copyright © 2026 Tony Ray Macier III. All Rights Reserved. -->

# Execution Flow

## Pipeline Overview

```mermaid
flowchart TD
    A[Schedule Trigger / API Request] --> B[Orchestrator.run_discovery_pipeline]
    B --> C{Seed Valid?}
    C -- No --> Z[FAIL: Exit 1]
    C -- Yes --> D[SentinelScanner.audit_bulk]
    D --> E[RiskAnalyzer.analyze]
    E --> F{Risk >= CRITICAL?}
    F -- Yes --> G[ArtifactRepairEngine.generate_firewall_rule]
    G --> H[Open PR with STATELOG hash]
    F -- No --> I[Log to STATELOG/events.jsonl]
    H --> I
    I --> J[PipelineController.complete]
```

## Environment Variables
| Variable | Required | Description |
|---|---|---|
| `THALOS_SEED` | Yes | 64-bit execution seed |
| `OWNER` | Yes | Must be "Tony Ray Macier III" |
| `DATABASE_URL` | No | SQLite WAL path (default: STATELOG/state.db) |
| `THALOS_API_KEY` | No | API authentication key (from GitHub Secrets) |
