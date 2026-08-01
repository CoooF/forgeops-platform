# EPIC-02.6B acceptance evidence

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING` on 2026-08-01 after all
listed local gates passed.
`REQ-FDS-001` and EPIC-02.6 remain `CLARIFYING / PARTIAL`. This is not enterprise
supply-chain acceptance, FDS Runtime, semantic/knowledge runtime, business UAT, or production
readiness evidence.

## Immutable boundaries

- Scope is domain-neutral Registry governance, Organization Installation, immutable Project
  DomainLock, package-reference impact, and a minimal real management UI.
- Installation and DomainLock create no authorization, runtime state, semantic readiness,
  workflow/Agent binding, Scenario binding, Grant, Secret, external write, or artifact execution.
- The existing Scenario Registry/Installation/ProjectPackageBinding remains the only Scenario
  runtime governance truth. An FDS Scenario Descriptor is investigation metadata only.
- All fixtures are `FIRST_PARTY_LOCAL` and `SYNTHETIC`. `local-sha256` is not enterprise
  signature, publisher, license, provenance, or malicious-content verification.
- No EPIC-02.6C semantic/knowledge feature, EPIC-03 workflow feature, or reference-scenario
  business behavior is present.

## Verified commands and results

| Evidence | Command | Verified result |
| --- | --- | --- |
| Baseline | `git status --short --branch`; `git log --oneline --decorate -8`; `make verify`; `make epic-02-6a`; `make fds-owner-demo` | planned HEAD `459e7f7`, clean; all prior gates pass before changes |
| 02.6A regression | `make epic-02-6a` | 40 focused cases and 17 FDS JSON consecutive-export digests passed |
| 02.6B focused | `make epic-02-6b` | 63 Registry/installation/lock/migration/FDS/architecture cases passed; 18 OpenAPI/FDS JSON consecutive-export digests matched |
| Owner walkthrough | `make epic-02-6b-owner-demo` | version switch/history/restart passed; Viewer 200/404, Outsider 404; transitive withdrawal reported 2 installations/2 locks and blocked new lock with stable 409 |
| Migration | `make migration-proof` | `0006` upgrade → base → `0006` passed |
| API restart | `make smoke` | existing Scenario/Project plus new Registry/Installation/current DomainLock persisted across independent API starts |
| Web restart | `make web-smoke` | built Web preview used independent real API state |
| Browser | `make e2e` | 2 existing/new real Web + API cases passed |
| Full regression | `make verify` | 341 Python tests at 88.34% combined line/branch coverage, 41 explicit contract tests and 6 Vitest cases passed; format/lint/type/security/build/source/wheel gates passed |
| Architecture | source and wheel scans | 36 Python and 9 Web source files scanned; source/wheel reference-domain violations = 0 |
| Security | local scan, `pip-audit`, `pnpm audit`, peer check | 0 local findings, known Python/Node vulnerabilities, or peer issues |
| Supply-chain inventory | `make sbom` | Python and Node CycloneDX JSON generated; Node SBOM contained 283 components |

## Acceptance mapping

| Criterion | Evidence | Result |
| --- | --- | --- |
| Four strict immutable versions, idempotency and digest conflict | API/SQL integration plus existing FDS validation | VERIFIED locally |
| Private Overlay/Component Organization isolation | list/detail/impact concealment and cross-Scope negative cases | VERIFIED locally; successful cross-Organization private reads = 0 |
| Registry-only atomic Installation | exact Registry refs/DependencyLock, digest revalidation, idempotency and no-partial-state assertions | VERIFIED locally |
| Installation creates no authorization/runtime | response invariants, stored values and owner/browser walkthrough | VERIFIED locally |
| Unique immutable current ProjectDomainLock and switch history | service transaction, partial unique index, tamper/double-current negatives, SUPERSEDED history | VERIFIED locally |
| Archive/cross-Scope/no-right/withdrawn/tampered fail closed | API negative matrix and stable errors | VERIFIED locally |
| Direct/transitive withdrawal impact | normalized ref tables, 2-installation/2-lock walkthrough, new-use block, unchanged history | VERIFIED locally |
| Persistence and migration | migration isolated round trip, standalone double-start, owner demo restart | VERIFIED with local SQLite |
| Real UI and role behavior | Playwright drives Web + real API for Owner, Viewer and withdrawal failure | VERIFIED locally |
| Legacy Scenario remains separate | full regression and explicit descriptor/no-second-truth assertion | VERIFIED as non-regression |
| SDK/core/wheel boundary | source and built-wheel architecture scans | VERIFIED locally |
| Audit correlation | success transaction and denial audit assertions with actor/scope/decision/reason/trace/policy/digest | VERIFIED subject to recorded denial-UoW limit |

## Evidence binding

After final gates, the implementation and human documentation are committed as a clean verified
source commit. `make epic-02-6b-evidence` then binds that commit to dependency locks,
OpenAPI/FDS contracts, synthetic governance fixtures, migration, requirements/ADR, built wheel,
SBOMs and coverage. The generated JSON is committed separately. Exact hashes and the generated
file SHA-256 are written back without amending prior commits.

- Verified source commit: pending clean source commit after the completed verification.
- Initial machine-evidence artifact commit: pending generation.
- Machine evidence SHA-256: pending generation.

## Not verified / blocked

- PostgreSQL service/runtime concurrency, backup/restore, enterprise OIDC/SCIM, external policy,
  Secret/network controls, PREPROD/PROD and independent security review;
- enterprise signature root, publisher identity, license/legal approval, remote Artifact/SBOM
  retrieval and verification, malicious-content scanning (`TEST-FDS-004` is blocked);
- Workflow Run/replay and fixed DomainLock consumption (`TEST-FDS-002` remains partial);
- Ontology/Terminology/Mapping, semantic query/constraints/grounding, KnowledgeAsset/RAG and
  Context Compiler (EPIC-02.6C not started);
- Workflow/Agent/model/MCP/Skill/Temporal runtime (EPIC-03 or later not started);
- real/de-identified data, business UAT, cross-industry real E2E, G2/G4/G5A/G5B and production
  release approval.

These limitations cannot be advanced by SQLite, synthetic identities, local hashes, a working
page, or passing local tests.

The full Python run emitted one SQLAlchemy `ResourceWarning` from an existing identity-access
test while all 341 tests passed. It is not treated as PostgreSQL service-runtime evidence.
