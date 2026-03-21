<!-- PROPRIETARY AND CONFIDENTIAL -->
<!-- Copyright © 2026 Tony Ray Macier III. All Rights Reserved. -->

# Core Module Interface Contract

## Rules
1. Core modules **CANNOT** depend on experimental modules.
2. Core modules **MUST** be stable (no breaking changes) before inclusion in a release.
3. Every engine **MUST** accept an `ExecutionContext` and return a dict with `state_hash`.

## Standard Response Format
```json
{
  "result": {},
  "state_hash": "<sha256>",
  "version": "2.0.0",
  "session_id": "<uuid>",
  "seed": 12345678901234567
}
```

## API Documentation Format
Every public function must have a docstring with:
- Args
- Returns
- Raises
- Example
