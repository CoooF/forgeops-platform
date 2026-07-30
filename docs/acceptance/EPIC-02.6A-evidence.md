# EPIC-02.6A acceptance evidence

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING` on 2026-07-30.
`REQ-FDS-001` remains `CLARIFYING / PARTIAL`. This is not FDS Runtime, semantic runtime,
enterprise supply-chain acceptance, production readiness, business UAT, or cross-industry
E2E evidence.

## Immutable boundaries

- Scope is a pure FDS v0.1 contract kernel: strict manifests, deterministic offline
  resolution/lock, stable issues, canonical export, and non-mutating Scenario SDK 0.x
  compatibility input.
- No API, database table, migration, frontend, Registry, Domain/Overlay installation,
  Project DomainLock, CatalogItem, Entitlement, Binding, Grant, Release, semantic runtime,
  knowledge/RAG, external model/network, real data, or business behavior was added.
- All new package fixtures are `FIRST_PARTY_LOCAL` and `SYNTHETIC`; local SHA-256
  attestation is not enterprise signature verification.
- PREPROD/PROD still use `DenyAllActionAdapter`. Resolution has
  `authorizationEffect=NONE` and `runtimeStateCreated=false`.
- The non-manufacturing `reference-domain-a` shape proves contract expressiveness and
  dependency neutrality only. `TEST-XDOM-001` and G5B remain blocked.
- EPIC-02.6B Registry/Project DomainLock and EPIC-02.6C Semantic Runtime were not started.

## Verified commands and results

| Evidence | Command | Result |
| --- | --- | --- |
| Baseline | `git status --short --branch`; `git log --oneline --decorate -5`; `make verify` | HEAD `806978e`, clean tree; 214 Python/17 contract/4 Web tests and all prior gates passed before changes |
| FDS focused gate | `make epic-02-6a` plus final focused rerun | 40 FDS contract, dependency, layer, permission, lock, legacy, security, XDOM-contract and architecture cases passed |
| TEST-FDS-CONTRACT-001 / LOCK-001 | `scripts/check_fds_determinism.py` | 17 FDS Schema/example/report/lock JSON files had identical SHA-256 across two consecutive exports |
| Full regression | `make verify` | 254 Python tests passed with 89.78% combined line/branch coverage; 41 explicit contract tests and 4 Vitest cases passed; format/lint/type/security/build gates passed |
| TEST-ARCH-003 | source and wheel architecture gates in `make verify` | 32 Platform/SDK Python and 6 Web source files scanned; FDS/reference-domain/framework violations = 0; wheel violations = 0 |
| TEST-OPS-API-SMOKE-001 | `make smoke` | independent API double-start preserved the existing Scenario installation and Project |
| TEST-OPS-WEB-SMOKE-001 | `make web-smoke` | built Web preview proxied independent real API and persisted local identity state |
| Existing Project E2E | `make e2e` | 1 Owner/Viewer/Outsider/archive/reload Playwright case passed |
| TEST-SBOM-001 | `make sbom` | Python and Node CycloneDX JSON generated; Node SBOM contains 283 components |
| Security | `pip-audit`; `pnpm audit --audit-level high`; `pnpm peers check`; local scan | 0 known Python/Node vulnerabilities, 0 peer issues, 0 local scan findings |

## Acceptance mapping

| Criterion | Evidence | Result |
| --- | --- | --- |
| Four strict manifest kinds and eleven Component kinds | Pydantic positive/negative tests and seven exported JSON Schemas | VERIFIED locally |
| Unique deterministic lock and stable topological order | multi-layer graph, candidate permutations, repeated runs, exported lock | VERIFIED locally |
| Missing/range/ambiguity/cycle/conflict/kind/capability/digest failures | focused negative matrix with stable code/path and `lock is None` | VERIFIED locally |
| Public/private and layer boundaries | direct/transitive private dependency, Domain→Overlay, cycle and Overlay-target tests | VERIFIED locally |
| Permission/budget calculation does not authorize | transitive total/delta/allowance tests and lock invariants | VERIFIED locally |
| Two old Scenario fixtures adapt without mutation | unchanged legacy validator first, preserved identifiers/digests/permissions/budgets/references, deterministic limited reports | VERIFIED as compatibility input only |
| Existing Scenario installation/binding/history unaffected | no registry import or persistence code; full prior regression, API restart and browser E2E pass | VERIFIED as non-mutation/regression evidence |
| Second-domain contract has no production special case | same Domain schema; FDS source and wheel term/import scan = 0 | VERIFIED as contract-only evidence |
| Schema/report/lock repeatability | consecutive export SHA-256 map | VERIFIED locally |
| No 02.6B/02.6C or runtime state | source scope review, architecture test, no migrations/API/frontend diff | VERIFIED as a non-scope invariant |

## Implemented evidence

- `forgeops.fds_sdk` contains strict models, canonical JSON/SHA-256, structured validation,
  a deterministic backtracking resolver, lock verification, and the explicit Legacy
  Scenario adapter.
- Package versions are canonical `X.Y.Z`; ranges are the documented PEP 440 subset. The
  optional rule and highest-compatible/backtracking behavior are explicit and tested.
- `contracts/fds/` contains the union/four-kind/lock/report Schemas, content-free
  multi-layer/second-domain fixtures, negative-case catalog, fixed lock, and two legacy
  compatibility reports.
- Stable issue order is code → path → message. Failures expose no partial lock or stack.
- Existing Scenario import paths, Schema, lifecycle, persistence, Project binding, API,
  OpenAPI, database and frontend remain unchanged except that contract export now also
  emits FDS artifacts.

## Evidence binding

The verified source commit is created before machine evidence. Then
`make epic-02-6a-evidence` requires a clean versioned source tree and writes
`docs/acceptance/generated-epic-02.6a-evidence.json`, binding that commit to lockfiles,
FDS schemas/examples, legacy fixtures, wheel, SBOM and coverage digests. The generated
file and this section are committed separately; the exact source/evidence commit hashes
are recorded there after generation.

## Not verified / blocked

- FDS Registry, Artifact download/trust service, Domain/Overlay installation, Project
  DomainLock, release, rollback, withdrawal propagation and private catalog enforcement
  (EPIC-02.6B or later);
- Ontology/Terminology Registry, semantic mapping/query/constraint/grounding, Context
  Compiler, Impact Analysis, KnowledgeAsset storage/index/RAG, Agent or workflow runtime
  (EPIC-02.6C or later);
- enterprise signature roots, publisher verification, license/legal review, SBOM/signature
  verification service, malicious-content scanning and external supply-chain incident
  response (`TEST-FDS-004` remains not started/blocked);
- PostgreSQL/Temporal/MinIO/OTel service runtime, enterprise OIDC/Secret/network,
  PREPROD/PROD, real/de-identified data, business UAT, G2/G4/G5A/G5B and G6—G8.

These limitations cannot be advanced by local contract tests. `TEST-FDS-002` has only the
adapter/non-mutation sub-evidence; runtime migration, fixed Project DomainLock and replay
remain unverified.
