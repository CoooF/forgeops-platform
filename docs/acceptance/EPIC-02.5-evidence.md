# EPIC-02.5 acceptance evidence

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_ENGINEERING` on 2026-07-30. This is not enterprise acceptance, production readiness, business UAT or permission to use real data.

## Immutable boundaries

- Scope is `LOCAL_SYNTHETIC_ENGINEERING`; `identityMode=LOCAL_SYNTHETIC` and `enterpriseIdentityConnected=false`.
- `X-ForgeOps-Actor` identifies a controlled seeded subject only in DEV/TEST. It creates no Principal, Membership, role or grant; INT/PREPROD/PROD reject it until an approved enterprise adapter exists.
- PREPROD/PROD remain fixed to `DenyAllActionAdapter`; no execution API, external model call, production credential, RPA, industrial-control path or external-system write was added.
- All test data are synthetic. No password, enterprise IdP, real directory, real/de-identified enterprise record or external service was used.
- FDS/semantic runtime, workflow runtime and reference-scenario business logic remain outside this Epic.

## Verified commands and results

| Evidence | Command | Result |
| --- | --- | --- |
| TEST-BUILD-001 and full regression | `make verify` | 214 pytest cases passed with 87.60% branch-aware coverage; 17 contract cases also passed in the explicit contract gate; 4 Vitest cases; Ruff/Prettier/ESLint, mypy/TypeScript, security, source/artifact architecture, Python and Web builds all passed |
| Python scope count | `uv run pytest -q --ignore=tests/contract` | 197 non-contract tests passed |
| TEST-IAM-POLICY-001 | `uv run pytest -q tests/unit/test_identity_policy.py tests/integration/test_identity_access_api.py` | 160 role/permission/scope and API integration cases passed |
| TEST-OPS-MIGRATION-001/002 | `make migration-proof` | Existing `0004 → 0005`, full `0005 → base → 0005` round trip and final head `0005` passed on an independent SQLite database |
| TEST-OPS-API-SMOKE-001 / TEST-OPS-PROJECT-RESTART-001 | `make smoke` | Independent API process created package installation plus Organization/Workspace/Project, stopped, restarted and read both persisted installation and Project |
| TEST-OPS-WEB-SMOKE-001 | `make web-smoke` | Built Vite preview proxied independent API health, platform boundary and persisted local identity; processes stopped |
| TEST-WEB-PROJECT-E2E-001 | `make e2e` | System Chrome: Owner created hierarchy and bound an approved fixture; Viewer was read-only; Outsider saw no scope; archived Project rejected binding; reload preserved archive |
| TEST-ARCH-001/002 | `scripts/check_architecture.py` plus artifact gate | 25 Platform Python and 6 Web source files scanned; reference-domain imports/conditions = 0; runtime wheel leakage = 0 |
| TEST-ACT-001/002 / TEST-SEC-002 | `make verify` security stage | local source/config findings = 0; Python and Node known vulnerabilities = 0; peer issues = 0; DenyAll/Mock regression passed |
| TEST-SBOM-001 | `make sbom` | Python and Node CycloneDX JSON generated; Node SBOM contains 283 unique components |
| TEST-CONTRACT-EXPORT-001 | two consecutive `scripts/export_contracts.py` runs | OpenAPI SHA-256 remained `591076d8e5032e06db0f7ae97b6b0efb629ca31327c93ed3d1469bc71fcaf030` |

## Acceptance mapping

| Acceptance criterion | Evidence | Result |
| --- | --- | --- |
| Header is not authorization | missing/unknown/forged/disabled subjects and local-outsider create attempt | VERIFIED |
| Owner creates Organization → Workspace → Project and restart preserves it | API integration plus standalone double-start smoke | VERIFIED |
| Viewer cannot edit/archive/manage members/bind | backend stable-error assertions and browser E2E | VERIFIED |
| Cross-scope discovery does not expose another resource | list filtering and uniform `RESOURCE_NOT_FOUND` assertions | VERIFIED |
| Disabled Principal or suspended/revoked Membership loses next-request access | policy/API integration | VERIFIED |
| Archived scope blocks writes/bindings but preserves history/audit | lifecycle/API/browser checks | VERIFIED |
| Existing Scenario lifecycle remains compatible | full regression and 17 consumer-contract cases | VERIFIED |
| New binding uses a real Project and arbitrary legacy string cannot impersonate it | Project binding integration and `project://` legacy rejection | VERIFIED |
| Project Center uses real APIs and persists refresh | component, preview smoke and Playwright | VERIFIED |
| OpenAPI, migration, builds, architecture, security and SBOM gates pass | commands above | VERIFIED |
| Enterprise login/FDS/workflow/reference business capability was not added | source/architecture/security review | VERIFIED as a non-scope invariant |

## Implementation evidence

- `identity_access` contains strict entities, replaceable `AuthPort`, stable `AuthorizationPort`, Permission dictionary, role/scope matrix, default-deny decisions and orchestration services.
- Alembic `0005` and SQLAlchemy repositories persist constrained/indexed Principals, hierarchy, Memberships, real Project bindings and idempotency records. Existing package/audit history is not rewritten.
- Every protected package and identity route resolves a persisted active Principal and authorizes on the backend. Sensitive denials and lifecycle events record actor/resource/scope/result/reason/trace/policy version in append-only audit.
- Project Center supports real hierarchy switching, search/filter, lifecycle, members, bindings and scoped audit, including loading/empty/error/forbidden/conflict/archive states. Its industrial operations-ledger visual system uses no remote fonts, decorative gradient or reference-scenario condition.

## Evidence binding

After the verified source commit, `make evidence` creates `docs/acceptance/generated-epic-02.5-evidence.json` and binds the source commit, locks, fixture/contract/SBOM digests, environment and limitations. The generated file is committed separately so it cannot claim a dirty or mutable source tree.

- Verified source baseline: `18bee65b20689068d6dd29f485133b9129c60385`.
- Machine evidence SHA-256: `05c43b3d176a79c318cb9cb142e36a4e4a495c29d3518400145ce6b73d4d313c`.
- Coverage is the combined covered line/branch total (`2268 / 2589 = 87.60%`), matching the full `make verify` gate rather than the line-only Cobertura rate.

## Not verified / blocked

- Docker-backed PostgreSQL/Temporal/MinIO/OTel runtime, PostgreSQL constraints/roles/RLS, backup/restore and service failure injection;
- enterprise OIDC/SCIM/Token rotation, policy publication/rollback, IdP outage, enterprise Secret/network/artifact/signing and independent security review;
- remote CI, enterprise browser/device matrix, load/performance/accessibility certification, PREPROD/PROD and UAT;
- real or de-identified data, any external model/system, FDS/semantic runtime (EPIC-02.6), durable workflow runtime (EPIC-03), business validity and G4—G7.

These remain `CODE_COMPLETE`, `CLARIFYING` or `BLOCKED` as applicable. Local SQLite and Chrome evidence must not be used to advance them to enterprise `VERIFIED`, `ACCEPTED` or `RELEASED`.
