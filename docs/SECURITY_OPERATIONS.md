# Thalos Prime Security Operations

**Status:** Operational guidance for review. This document does not certify a live deployment.

## Required production configuration

Set `THALOS_ENV=production`. Store secrets in the deployment platform's secret manager, not in Git, container images, build logs, issue comments, or committed `.env` files.

Generate independent random values of at least 32 UTF-8 bytes for each of these variables:

- `THALOS_API_TOKEN` — bearer token protecting the main `/api/v1/*` routes and runtime `POST /execute`.
- `THALOS_ADMIN_API_KEY` — separate administrative API key.
- `THALOS_SECRET_KEY` — JWT/signing secret required by production API configuration.
- `THALOS_NEXUS_SIGNING_KEY` — NEXUS genome-bundle signing key.
- `THALOS_PRP_KEY` — stable artifact-index key.

Never reuse one secret for multiple purposes. Never put real values in `.env.example`. A missing or short required secret is intended to stop the protected feature or application from starting, rather than silently use a known default.

Production CORS must list only the exact HTTPS origins used by the deployment, for example `https://app.example.com,https://admin.example.com`. Wildcard origins, HTTP origins, and entries containing a path or query are rejected by the strict CORS parser. Replace example domains with the real approved frontend origins before deployment.

## Development configuration

Use `THALOS_ENV=development` for local work. Development CORS defaults are loopback-only. The legacy `THALOS_AUTH_DISABLED=1` bypass is permitted only when `THALOS_ENV` is explicitly set to `development`, `dev`, or `test`. Do not set it in production, staging, CI deployment, or an environment whose mode is unknown. CI should use test-only credentials, never deployment secrets.

## Key lifecycle and compatibility

- Keep `THALOS_PRP_KEY` stable and back it up securely. Changing it can change artifact coordinates and break lookups. Design and test a migration before rotating it.
- Rotating `THALOS_SECRET_KEY` can invalidate existing JWTs. Plan token expiry/re-authentication and deployment rollback.
- Rotating `THALOS_NEXUS_SIGNING_KEY` can prevent verification of historical genome signatures. Preserve verification capability for old key versions or re-sign artifacts through a documented migration.
- Rotate any key only after identifying where it is used, checking whether it is deployed, planning compatibility, and confirming recovery access. Do not paste secrets into this repository or this document.

## Deployment controls

Before enabling external access, verify all of the following in the actual hosting environment:

1. TLS is enforced at the public edge; admin endpoints and execution endpoints are not exposed to the public internet unless explicitly required.
2. Database and cache ports are private. Database files and backups are stored outside public/static directories and protected by least-privilege filesystem permissions.
3. Backups are encrypted, access-controlled, and periodically restored in a test environment.
4. The application runs with the least privileges required; containers, if used, should avoid privileged mode and run as a non-root user where compatible.
5. Rate limits, request-size limits, timeouts, and resource budgets are enforced at the application and/or trusted gateway.
6. Logs do not contain credentials, authorization headers, sensitive prompts, or unnecessary personal data.
7. Dependency inventories and vulnerability scans are reviewed, not merely run. Updates are tested before deployment.
8. Deployment secrets are present and valid. No real secret is committed to the repository.

## Repository controls

The default branch currently includes a CODEOWNERS file, Dependabot configuration, CodeQL workflow, and full-history Gitleaks workflow. Their presence does not prove every check is passing or every alert is resolved.

Configure GitHub branch protection or a repository ruleset in the GitHub interface. Require pull requests, at least one independent review where available, successful required checks, resolved review conversations, and restrictions on force-push and branch deletion. Verify the rules on the actual default branch; this repository's connected integration could not read the branch-protection endpoint during the current review.

Never merge a security PR while required checks are failing, skipped unexpectedly, or unavailable for review. If a workflow's logs cannot be obtained, record the failure as undiagnosed and use GitHub's Actions UI to inspect it rather than guessing at its cause.

## Incident response and history

If a real credential is confirmed in source, logs, artifacts, or deployment output, revoke or rotate it first using its provider's supported process, then assess where it was used. Preserve evidence and timestamps. A Git-history rewrite does not revoke a credential and does not automatically remove copies from forks, clones, caches, or releases. Coordinate cleanup separately and do not rewrite shared history without a recovery plan.

## Verification status

This branch contains proposed code and test changes. It is not merged, is not deployed, and is not a security certification. Verify CI, deployment settings, actual secret storage, network exposure, backups, and runtime behaviour before representing the system as secured.
