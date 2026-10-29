# Thalos Prime Library security remediation record

**Status date:** 29 October 2026

This branch adds an explicit bearer-token boundary around all routers mounted under `/api/v1/*` and protects the separate runtime `POST /execute` endpoint.

- Required variable: `THALOS_API_TOKEN`; configure a cryptographically random value of at least 32 UTF-8 bytes through a secret manager.
- Missing/weak server configuration returns HTTP 503 rather than silently allowing protected operations.
- Missing or invalid bearer credentials return HTTP 401.
- The admin router retains its distinct `THALOS_ADMIN_API_KEY` requirement; configure a separate strong key.
- Artifact ingestion no longer uses an embedded fixed indexing key. It returns HTTP 503 until a stable `THALOS_PRP_KEY` of at least 32 UTF-8 bytes is configured.
- Keep the PRP key stable and backed up. Rotating it may change coordinates and requires a migration plan.
- Tests use fake test-only values, not production secrets.

The source changes have been committed to the open security proposal branch. They are not merged or deployed and are not independently certified. Run all CI checks, inspect deployment configurations, and review API-client changes before merging.
