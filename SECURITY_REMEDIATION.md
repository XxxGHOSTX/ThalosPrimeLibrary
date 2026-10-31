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
- Add security-focused regression tests and test-only credentials; no production secret values are included.

## Compatibility warnings

- Changing `THALOS_PRP_KEY` can change artifact coordinates. Do not rotate it without a tested data migration and recovery plan.
- Changing JWT or NEXUS signing keys affects existing tokens or historical signature verification. Plan key versioning, re-authentication, and rollback before deployment.
- API clients must send `Authorization: Bearer <THALOS_API_TOKEN>` to protected routes. Update clients and health/integration checks deliberately.

## Validation still required

The source and test changes have been committed to this review branch. A CI run must pass on the final branch head. Review every changed file, test the application locally, verify deployment settings, inspect the real hosting environment, and test API-client compatibility before merge. A successful GitHub commit is not proof that tests passed.

The GitHub integration could not retrieve logs for several prior failed workflow jobs. Their precise failure causes remain undiagnosed; do not infer causes from short runtime alone.

## Scope limits

This remediation does not rotate deployed secrets, change repository visibility, rewrite Git history, change licenses, delete formal-model or patent-development documents, or prove that a running deployment is secure. Those operations require separate evidence and compatibility checks.
