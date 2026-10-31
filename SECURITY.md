# Security Policy

## Supported Versions

The following versions of Thalos Prime Library receive security updates:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Thalos Prime Library seriously. If you believe you have found a security
vulnerability, please report it to us as described below.

**Please do not report security vulnerabilities through public GitHub issues.**

### How to Report

Report security vulnerabilities via
[GitHub Security Advisories](https://github.com/XxxGHOSTX/ThalosPrimeLibrary/security/advisories/new).

Please include the following information in your report:

- **Type of vulnerability** (e.g., code injection, privilege escalation, data exposure)
- **Full paths** of the affected source file(s)
- **Location** of the affected code (tag, branch, commit, or direct URL)
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact** of the issue, including how an attacker might exploit it

This information helps us triage your report more quickly.

### Response Timeline

After you submit a report, you can expect:

- **Initial acknowledgement**: Within 48 hours
- **Status update**: Within 7 days with an assessment of the report
- **Resolution timeline**: Communicated once the issue is confirmed

### Disclosure Policy

Once a fix is ready and released:

- We will publish a security advisory on GitHub.
- Credit will be given to the reporter (unless anonymity is requested).
- We ask that you do not disclose the vulnerability publicly until the fix is released.

## Current Security Remediation Status

The default branch contains CodeQL, full-history secret-scanning, Dependabot, and CODEOWNERS configuration. The presence of these workflows does not mean that all scans are passing or that all alerts are resolved.

Proposed fail-closed API, signing-key, and CORS changes are maintained on a separate security review branch and must not be treated as deployed until merged after successful required checks and deployment verification. See [Security Operations](docs/SECURITY_OPERATIONS.md) for production configuration, key lifecycle, incident response, and repository-control guidance.

## Security Considerations

Thalos Prime Library is designed with the following security principles:

- **No secrets in source code**: All credentials must be supplied via environment variables.
- **Input validation**: All inputs are validated at API boundaries; invalid inputs are rejected
  with explicit errors.
- **Deterministic execution**: The system is designed to halt with full state capture on
  unresolvable errors rather than silently degrading.
- **Dependency auditing**: Dependency audit workflows are configured; their current results must be reviewed on each target commit.
- **Static analysis**: CodeQL and other configured security workflows must pass on the exact commit before release. Workflow presence alone is not a passing result.

## Preferred Languages

We accept vulnerability reports in **English**.
