# Thalos Prime Intellectual-Property and Provenance Register

**Prepared:** 31 October 2026  
**Purpose:** Working evidence register for review. This is not a legal opinion, proof of inventorship, proof of ownership, or a patentability determination.

## 1. Repository and license observations

The following are observed repository metadata or repository-documentation states from the current review. They are not a complete file-by-file license audit.

| Repository | Observed state | Required verification |
|---|---|---|
| `XxxGHOSTX/ThalosPrimeLibrary` | GitHub reports MIT license metadata. | Confirm the exact LICENSE file, release tags, contributors, and which files are covered by each release. |
| `XxxGHOSTX/THALOS-PRIME-CORE-BUILD-V2` | GitHub/repository material reports MIT. | Confirm exact licensed snapshot and provenance of contributed files. |
| `XxxGHOSTX/Thalos-Prime-Directive2` | Repository is labeled Apache-2.0. | Verify the actual LICENSE text, third-party notices, and all contributors. |
| `XxxGHOSTX/Thalos-Prime-Directive` | Public repository contains proprietary-language documentation. | Reconcile those statements with public availability, any license file, release history, and grants already made. |
| `XxxGHOSTX/ThalosPrime-v1.0` | README material has been described as MIT while earlier metadata differed. | Verify the current license file and historical versions. |
| Other Thalos/Prime repositories | Mixed or incomplete metadata. | Audit each repository, tag, release, and materialized package separately. |

A copyright notice or owner-controlled GitHub account does not by itself prove sole authorship or a complete chain of title. A later change to a repository's license does not automatically cancel permissions already granted under an earlier distributed version. Obtain a file- and version-specific legal review before changing license terms or claiming exclusive control over previously released material.

## 2. Authorship and chain of title evidence to preserve

Create a record for every human contributor and material contribution, including:

- legal name and contact details in a controlled private record;
- repository, file paths, commit hashes, dates, and description of each contribution;
- whether the contribution was authored independently, generated with tools, adapted from third-party material, or based on prior work;
- applicable license and attribution requirements;
- signed assignment, employment, or contributor agreement where applicable;
- evidence supporting conception and reduction to practice for any invention disclosure.

Do not publish personal identifiers, private agreements, or sensitive contact information in this register. Do not claim a contributor assigned rights unless a valid signed document supports it.

## 3. Public disclosure timeline

A prior repository review identified a GitHub creation timestamp of **27 December 2025, 01:08:57 UTC** for `XxxGHOSTX/ThalosPrime-v1.0`, with an initial commit bearing the same timestamp. This is a dated repository record, not proof that the repository was public at that time or that it was the first enabling public disclosure. Verify historical visibility, exact commit contents, releases, package downloads, public posts, demonstrations, and third-party copies before using it in a legal filing or opinion.

Preserve timestamped commits, releases, tags, archives, file hashes, correspondence, dated notebooks, prototype records, and actual first-disclosure evidence. Do not rewrite or delete history to conceal dates.

### Prior public removal of formal-model and claim-development documents

The current public default tree intentionally omits three detailed draft files following security/documentation commits on 29 October 2026:

- `docs/guides/Thalos_Prime_Patent_Charter.md` was removed by commit `ba6a5b5102183c0ab892bc1967b14d9003b0cd90`.
- `docs/guides/Thalos_Prime_Claims_Scaffold.md` was removed by commit `23ed19d10dcd2d93c7abc45cc231f1558758e0d1`.
- `docs/FORMAL_MODEL.md` was removed by commit `c718fa61b789b14788ffe58563b8628d2a4a5580`.

The public Phase 1/2 guides were also edited to remove detailed references to the unpublished formal model in commits `75b6d0e2dbe45efb2a08177f7561906e6ba04865` and `c4ae75edd3efc74c1316334fac90d36d0cb8dc00`.

These were deliberate removals from the current public tree. This review branch keeps them absent; it does not republish their contents. **They remain in public Git history and may remain in forks, clones, caches, and prior downloads.** Removing a path from the current branch is not a history purge and does not reverse any prior public disclosure. No history rewrite or private archive has been performed in this task. If private preservation is required, store verified copies in a restricted archive separate from the public repository. Consider history cleanup only with counsel/technical review and a coordinated fork/clone plan.

## 4. Candidate invention for technical review

**Working concept:** an evidence-gated runtime-candidate promotion protocol.

The research concept binds baseline and candidate identities, a reproducible benchmark contract, test outputs, measured metrics, policy decisions, and a rollback target into a canonical evidence receipt. Promotion is allowed only after predeclared gates pass; post-promotion invariant failures trigger a controlled rollback.

**Status:** research candidate only. This is not a novelty, non-obviousness, eligibility, priority, or freedom-to-operate conclusion.

The current implementation review identified engineering gaps that must be resolved and demonstrated before the system is described as performing the proposed functions:

- Candidate execution must be isolated from the host process and from other workloads with a documented threat model.
- Latency and efficiency must be measured from real executions with reproducible conditions, not hardcoded values.
- The audit digest must cover all security-relevant event fields, including payload, seed, configuration, schema version, and ordering; truncation and rollback need independently persisted checkpoints.
- Artifact signing must bind the complete canonical manifest and all referenced payloads, not merely a partial identifier.
- Promotion and rollback must be crash-safe, atomic, and validated against injected failure cases.

Keep the formal-model and patent-development documents as dated design materials. Clearly label proposals as proposals and implementation claims only when supported by source code, tests, and reproducible evidence. Removing documents is not a substitute for correcting unsupported claims.

## 5. Trademark and copyright work

No trademark registration, copyright registration, patent filing, or ownership assignment is confirmed by this register. Third-party trademark-directory search results are leads only; verify current records through official USPTO systems before spending on branding or making legal claims. Confirm exact work versions and claimant information before submitting copyright registrations.

## 6. Required evidence package

Maintain a versioned evidence package containing:

1. repository URLs, visibility, default branches, commit hashes, release tags, and a dated export;
2. a file-level authorship and third-party-license inventory;
3. copies of executed contributor and assignment agreements stored privately;
4. original invention notes, diagrams, experiment records, prototype logs, and source-control history;
5. a disclosure timeline distinguishing private, confidential, and public access;
6. reproducible test results tied to exact commit hashes and toolchain/dependency versions;
7. a claim-by-claim prior-art review conducted by qualified patent counsel or a search professional.

Do not represent this register as proof of ownership or patent rights. Update it only when evidence has been checked.
