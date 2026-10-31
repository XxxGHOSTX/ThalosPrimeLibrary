# Thalos / Prime Repository Security Inventory

**Snapshot date:** 31 October 2026  
**Scope:** 16 public repositories under the Thalos/Prime project family. A recursive tree scan was performed against each reported default branch. The returned non-empty trees were not marked truncated.

This is a current-branch configuration inventory, not a complete audit of all branches, commit history, deployments, collaborators, or GitHub account security. Presence of a workflow does not establish that it is passing or that its alerts have been resolved.

## Repository controls observed

All 16 repositories had the following files/configuration on their default branch at the time of the scan:

- `.github/CODEOWNERS`
- `.github/dependabot.yml`
- `.github/workflows/secret-scan.yml`
- `SECURITY.md`

Ten repositories also had a CodeQL workflow. The six without CodeQL are mostly documentation-only or very small scaffolds; add language-specific CodeQL analysis if substantive supported source code is introduced.

| Repository | Default branch | Default tree entries | CodeQL workflow | Notes |
|---|---:|---:|---|---|
| [ThalosPrime-v1.0](https://github.com/XxxGHOSTX/ThalosPrime-v1.0) | `main` | 51 | Yes | Core project repository; also has CI and release workflows. |
| [ThalosPrimeMedv1](https://github.com/XxxGHOSTX/ThalosPrimeMedv1) | `main` | 12 | No | Small HTML/TypeScript configuration scaffold; review CodeQL if application source is added. |
| [Thalos-Prime-Directive2](https://github.com/XxxGHOSTX/Thalos-Prime-Directive2) | `main` | 72 | Yes | Security and CI replacement is proposed in draft PR #31; not merged or deployed. |
| [Thalos-Prime-Web](https://github.com/XxxGHOSTX/Thalos-Prime-Web) | `main` | 7 | No | Documentation/security-policy shell; no substantial application source in the current tree. |
| [Thalos_Prime_New_system_build](https://github.com/XxxGHOSTX/Thalos_Prime_New_system_build) | `master` | 155 | Yes | Database-related matches are source modules, not credential files or database dumps in the current tree. |
| [ThalosPrimeCodev1](https://github.com/XxxGHOSTX/ThalosPrimeCodev1) | `main` | 8 | No | Small documentation/license shell; no substantive source tree identified. |
| [ThalosPrimeCoreBuildv1](https://github.com/XxxGHOSTX/ThalosPrimeCoreBuildv1) | `master` | 30 | Yes | Existing source repository. |
| [THALOS-PRIME-CORE-BUILD-V2](https://github.com/XxxGHOSTX/THALOS-PRIME-CORE-BUILD-V2) | `main` | 43 | Yes | Current tree has no database/bytecode files; a previous commit deleted a tracked `data.db` and Python bytecode. Historical objects may remain. |
| [THALOS_PRIME_CORE_INTELLIGENCE](https://github.com/XxxGHOSTX/THALOS_PRIME_CORE_INTELLIGENCE) | `main` | 18 | Yes | Small active source/design repository. |
| [ThalosPrimeConcept](https://github.com/XxxGHOSTX/ThalosPrimeConcept) | `main` | 41 | Yes | Concept and source materials. |
| [ThalosPrimeLibrary](https://github.com/XxxGHOSTX/ThalosPrimeLibrary) | `main` | 586 | Yes | Main library; fail-closed security hardening is proposed in draft PR #122. |
| [ThalosPrimeLibraryOfBabel](https://github.com/XxxGHOSTX/ThalosPrimeLibraryOfBabel) | `main` | 6 | No | Empty Git repository apart from repository-control files. |
| [ThalosPrime-Platform](https://github.com/XxxGHOSTX/ThalosPrime-Platform) | `main` | 141 | Yes | Has separate CI, dependency, lint, and security workflows. |
| [ThalosPrimeLibrary.v2](https://github.com/XxxGHOSTX/ThalosPrimeLibrary.v2) | `main` | 8 | No | Small documentation/license shell; no substantive source tree identified. |
| [Thalos-Prime-Revision](https://github.com/XxxGHOSTX/Thalos-Prime-Revision) | `main` | 8 | No | Small documentation/license shell; no substantive source tree identified. |
| [Thalos-Prime-Directive](https://github.com/XxxGHOSTX/Thalos-Prime-Directive) | `main` | 169 | Yes | IP/publication-status correction is in existing draft/working PR #8; code was not changed. |

## Findings requiring follow-through

### ThalosPrimeLibrary

The main branch's known signing-key, JWT/CORS, admin-key, PRP-key, and missing API authentication weaknesses are addressed in proposed source changes on [PR #122](https://github.com/XxxGHOSTX/ThalosPrimeLibrary/pull/122). That PR is a draft, not merged, and its latest required checks are failing or undiagnosed. Do not treat the branch as deployed security.

Historical source included publicly known fallback strings such as `admin-key-change-in-production` and `change-this-secret-key-in-production`. Current proposed code removes those defaults. Full-history scanning may still alert on parent commits. Do not broadly suppress those alerts. Determine whether any deployed service relied on those values; rotate them if confirmed.

### Thalos-Prime-Directive2

The proposed replacement [PR #31](https://github.com/XxxGHOSTX/Thalos-Prime-Directive2/pull/31) adds API token validation, stricter CORS, safer container/Kubernetes defaults, and Node 24 LTS. It is a draft, not merged or deployed. Its latest checks are failing or undiagnosed. The Kubernetes Secret is intentionally a non-deployable template and the deployment image must be replaced with a verified immutable digest before deployment.

### Thalos-Prime-Directive

[PR #8](https://github.com/XxxGHOSTX/Thalos-Prime-Directive/pull/8) updates one IP/publication-status document. It corrects unqualified "proprietary/unpublished" assertions but does not establish sole ownership, a patent filing, or a copyright registration.

### THALOS-PRIME-CORE-BUILD-V2 historical database

The current default tree does not contain the previous `data.db` path. A recorded deletion commit does not prove what the old database contained or remove its old Git object. Confirm whether it ever contained personal, sensitive, or confidential information before deciding whether history cleanup or further incident response is required. Do not rewrite history without preserving evidence and planning for forks/clones.

### Other database source modules

The scanned `Thalos_Prime_New_system_build` database files are source code rather than a checked-in database dump. The advanced PostgreSQL manager uses localhost configuration defaults and simulated connection behaviour; the wetware database stores data in memory. The `Thalos-Prime-Directive` connection manager likewise uses memory/file placeholder behaviour and contains no embedded database credential in the inspected source. These observations do not certify future deployments.

## GitHub settings that still need an owner action

The connected repository interface could read repository metadata and source files but could not verify or change branch-protection/ruleset settings. CODEOWNERS does not enforce review by itself. On each active default branch, configure and verify a GitHub ruleset that:

1. Requires a pull request and at least one review before merging.
2. Requires CODEOWNERS review for protected paths where practical.
3. Requires all relevant CI, CodeQL, and security checks to pass.
4. Requires review conversations resolved.
5. Blocks force-pushes and branch deletion.
6. Restricts bypass permissions to a minimal trusted set.

Also review GitHub Security settings for secret-scanning push protection and Dependabot security alerts/updates. The checked-in workflows and Dependabot update configuration are useful controls but do not prove those repository settings are enabled.

## Validation boundaries

The repository-tree scan is not a complete secret-value scan, malware analysis, dependency inventory, all-branch/history audit, access review, cloud/deployment audit, or proof that no data was previously exposed. Current workflow failures in the two replacement security PRs have no retrievable job steps/logs through the connected integration; inspect their Actions pages before merging. Never infer a passing check from a workflow file existing.
