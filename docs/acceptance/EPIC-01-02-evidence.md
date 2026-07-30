# EPIC-01/02 evidence and status rules

Evidence is valid only when it records the command, commit, lock digests, environment, result, and limitation. Local tests can reach `VERIFIED`; enterprise integration, production readiness, business validity, and G5 cannot.

| Scope | Candidate state | Required evidence |
| --- | --- | --- |
| Domain contracts, lifecycle, manifest/permissions/schema validation | VERIFIED | pytest + stable negative reason assertions |
| FastAPI and file-backed persistent state | VERIFIED | migration + API restart integration test |
| PostgreSQL adapter/Compose definition | CODE_COMPLETE until Docker-backed test runs | Compose config, migration and integration logs |
| Temporal generic worker skeleton | CODE_COMPLETE | import/type/build; replay is EPIC-03 |
| Enterprise IdP/Secret/signing/network/observability | BLOCKED | enterprise owners and environment evidence |
| Reference scenarios | CLARIFYING / fixture only | no business implementation or claim |
| Equipment anomaly validity and G5 | BLOCKED | domain experts and future differentiated E2E |

`ACCEPTED` and `RELEASED` are not available under this local engineering approval.

## Verified local evidence — 2026-07-30

| Evidence ID | Command | Result |
| --- | --- | --- |
| TEST-BUILD-001 | `make verify` | Ruff/Prettier, ESLint, strict mypy/TypeScript, Python/Web builds all passed |
| TEST-DOM-001 / TEST-SCHEMA-001 | `uv run pytest ...` via `make verify` | 49 Python tests passed; 94.09% branch-aware coverage |
| TEST-CONTRACT-001 / TEST-SDK-001/002 | `uv run pytest -q tests/contract` | 17 contract tests passed, including stable negative reason codes and logical uninstall |
| TEST-WEB-001 | `pnpm run test` | 2 Vitest tests passed; page reads API state and exposes local/no-enterprise boundary |
| TEST-ARCH-001 | `uv run python scripts/check_architecture.py` | 19 Platform Python files scanned; Core-to-reference-package dependencies = 0 |
| TEST-ARCH-ARTIFACT-001 | `uv run python scripts/check_artifact_architecture.py` after build | runtime wheel excludes reference packages and forbidden runtime dependencies; Platform imports = 0 |
| TEST-ACT-001/002 / TEST-SEC-002 | `make security` | local source/config scan passed; pip/pnpm known vulnerabilities = 0; peer issues = 0 |
| TEST-OPS-MIGRATION-001 | Alembic `upgrade head → current → downgrade base → upgrade head → current` | SQLite migration path passed; final revision `0004` |
| TEST-OPS-API-SMOKE-001 | `make smoke` | independent API process restarted; package installation remained readable |
| TEST-OPS-WEB-SMOKE-001 | `make web-smoke` | built Vite preview proxied health/status to an independent API and read real local boundary state |
| TEST-SBOM-001 | `make sbom` | Python and Node CycloneDX 1.6 JSON generated; Node SBOM contains 279 unique components |
| TEST-CONTRACT-EXPORT-001 | two consecutive `scripts/export_contracts.py` runs | OpenAPI and Manifest JSON Schema SHA-256 values remained identical |

## EPIC completion mapping

| Deliverable | Status | Boundary |
| --- | --- | --- |
| Independent Git repository and governance skeleton | VERIFIED | local repository only; enterprise branch protection/remote CI not evidenced |
| Locked Python 3.13/uv and Node 24/pnpm workspaces | VERIFIED | lockfiles and local frozen builds passed |
| Generic contracts, errors, repository/Port boundaries and lifecycle | VERIFIED | no reference business types or reverse dependency |
| Strict Manifest/all Pack declarations, permissions, budgets, schema/SDK compatibility and local attestation | VERIFIED | SDK remains `0.1.0`; local SHA-256 is not enterprise signing |
| Install/test/approve/grant/bind/release/enable/disable/revoke/logical-uninstall | VERIFIED | logical uninstall preserves metadata/audit and blocks new Runs |
| FastAPI/SQLite persistence, four migrations, audit/trace/metric/health and React status page | VERIFIED | direct local mode only |
| PostgreSQL/Temporal/MinIO/OTel Compose | CODE_COMPLETE | Docker is absent; no service-level evidence |
| Temporal durable workflow replay/recovery | CODE_COMPLETE | contract-probe skeleton only; EPIC-03 owns runtime acceptance |
| Steel-cord and equipment-anomaly packages | CODE_COMPLETE | contract fixtures only; no scheduling/diagnosis implementation |
| Enterprise IdP/Secret/signing/network/artifact platform, real data, PREPROD/PROD/UAT | BLOCKED | explicitly outside approved scope |
| Reference-scenario business validity and G5 generalization | BLOCKED | no domain experts or differentiated E2E |

The machine-readable evidence file is generated after the source baseline commit so it can bind lock, fixture, contract and SBOM digests to an immutable Git revision.
