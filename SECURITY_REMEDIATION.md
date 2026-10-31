# Thalos Prime Library Security Remediation Record

**Status date:** 31 October 2026  
**Branch:** `security/secure-runtime-and-api-2026-10-31`  
**Status:** Proposed changes committed for review; not merged, not deployed, and not security-certified.

## Changes proposed on this branch

- Remove the default NEXUS signing key. Genome signing now requires an explicitly configured `THALOS_NEXUS_SIGNING_KEY` with at least 32 UTF-8 bytes.
- Replace the hardcoded JWT-secret fallback with an ephemeral development secret and a required production secret.
- Require explicit, non-wildcard CORS origins in production; production origins must use HTTPS.
- Require a distinct strong `THALOS_ADMIN_API_KEY`; use constant-time comparison and fail closed if missing or weak.
- Require a stable configured `THALOS_PRP_KEY` for artifact indexing; no fixed key fallback is used.
- Require an explicit bearer token for protected `/api/v1/*` routes and the separate runtime `POST /execute` endpoint.
- Restrict the legacy `THALOS_AUTH_DISABLED=1` bypass to explicitly declared development/test environments.
- Remove the known default admin key from the browser client, disable browser-initiated server shutdown, and minimize public runtime health responses.
- Disable interactive OpenAPI/Swagger/ReDoc endpoints in production; retain them in development.
- Add security-focused regression tests and test-only credentials; no production secret values are included.

## Compatibility warnings

- Changing `THALOS_PRP_KEY` can change artifact coordinates. Do not rotate it without a tested data migration and recovery plan.
- Changing JWT or NEXUS signing keys affects existing tokens or historical signature verification. Plan key versioning, re-authentication, and rollback before deployment.
- API clients must send `Authorization: Bearer <THALOS_API_TOKEN>` to protected routes. The static browser UI does not yet implement production user login/session authentication; do not embed a shared API token into its JavaScript. Implement an identity-aware session/gateway layer before production browser access. The UI's server-stop button is intentionally disabled.

## Validation still required

The source and test changes have been committed to this review branch. A CI run must pass on the final branch head. Review every changed file, test the application locally, verify deployment settings, inspect the real hosting environment, and test API-client compatibility before merge. A successful GitHub commit is not proof that tests passed.

The GitHub integration could not retrieve logs or step summaries for the latest failed workflow jobs. Their precise failure causes remain undiagnosed; do not infer causes from short runtime alone. Full-history secret scanning can legitimately flag the old hardcoded development defaults in parent commits even after current source removes them. Do not broadly allowlist those strings: they are publicly known unsafe defaults. Determine whether any live deployment used them and rotate if confirmed.

## Scope limits

This remediation does not rotate deployed secrets, change repository visibility, rewrite Git history, change licenses, delete formal-model or patent-development documents, or prove that a running deployment is secure. Those operations require separate evidence and compatibility checks.
