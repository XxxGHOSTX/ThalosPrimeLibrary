# Security Configuration Migration Note

**Scope:** the pending security-hardening pull request; not a declaration that a deployment is already secure.

## NEXUS signing key

NEXUS no longer accepts a built-in development signing key. Configure `THALOS_NEXUS_SIGNING_KEY` before invoking `ingest-genome` or any command that signs a genome bundle. Use a randomly generated secret with at least 32 UTF-8 bytes. Generate a value locally with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Save the result in a secret manager or a local environment setting that is excluded from version control. Do not commit the actual secret, include it in logs, or paste it into issues. Use a stable key for a system that must verify previously generated HMAC signatures. If a real deployment previously relied on the known public fallback key, assume its signatures are forgeable and plan a controlled key rotation / re-signing procedure. Do not silently change a production verification key without considering existing signed artifacts.

PowerShell (current terminal only):

```powershell
$env:THALOS_NEXUS_SIGNING_KEY = "<paste locally generated value here>"
```

CMD (current terminal only):

```cmd
set THALOS_NEXUS_SIGNING_KEY=<paste-locally-generated-value-here>
```

## API secret and CORS settings

For production set all of the following through the deployment secret/configuration manager:

- `THALOS_ENV=production`
- `THALOS_SECRET_KEY` to a random value with at least 32 UTF-8 bytes
- `THALOS_CORS_ORIGINS` to a comma-separated list of exact allowed origins, including scheme and host (and port where applicable); the wildcard `*` is rejected in production.

The development configuration generates an ephemeral random JWT secret and permits only localhost origins. Restarting the development process can invalidate locally issued tokens, which is expected for an ephemeral development secret.

## Pre-merge and deployment gate

Do not merge or deploy until:

1. CI passes on the latest pull-request head, including pytest, type checks, lint, dependency/security checks, and Windows NEXUS tests.
2. The source and deployment configuration are reviewed against the real runtime.
3. A staging deployment successfully signs and verifies a newly generated bundle with the configured key.
4. A migration plan exists for any historical signatures/tokens and actual deployed keys.
5. Production origins are documented and verified; no wildcard CORS is allowed.

## Security status

This patch prevents use of a published default in the newly patched source path. It does not rotate a secret in a deployed environment, purge old Git blobs, prove that the prior development key was never used operationally, or establish that every Thalos Prime repository is secure.