<!-- PROPRIETARY AND CONFIDENTIAL -->
<!-- Copyright © 2026 Tony Ray Macier III. All Rights Reserved. -->

# AI Agent Instructions — ThalosPrime

**Owner:** Tony Ray Macier III

## How Agents Modify Files
1. Always include the IP header at the top of every new file.
2. Never modify `core/` or `system/` files without owner approval.
3. Always log modifications to `STATELOG/events.jsonl`.
4. Use the `--seed` argument for all deterministic operations.

## How Agents Create PRs
1. Branch from `main` using `feature/` or `fix/` prefix.
2. Reference the STATELOG event ID in the PR description.
3. Include the execution seed in the PR title.
4. Use the `.github/PULL_REQUEST_TEMPLATE.md`.

## How Agents Extend Modules
1. Use `automation/module_generator.py` to scaffold new modules.
2. Add new modules to `registry/manifest.yml`.
3. Update `docs/platform/ARCHITECTURE.md` with new module boundaries.

## Task Templates

### Discovery Scan Task
```
@discovery Run a full shadow AI scan on the provided network logs.
Seed: <64-bit integer>
Log file: <path>
Output: STATELOG/discovery.jsonl
```

### Remediation Task
```
@remediator Generate a firewall rule for the following finding:
Finding: <JSON from STATELOG>
Seed: <64-bit integer>
Output: Open PR with patch
```
