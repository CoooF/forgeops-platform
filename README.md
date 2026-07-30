# ForgeOps Platform

Independent EPIC-01/02 engineering baseline for the ForgeOps Platform Core and Scenario SDK. It is runnable with local synthetic fixtures and is not approved for enterprise, preproduction, production, real-data, business-UAT, scheduling, or anomaly-diagnosis use.

## What is implemented

- strict domain-neutral platform contracts and versioned execution envelopes;
- strict Scenario Manifest/pack contracts, compatibility validation, local digest attestation, permissions, budgets, migrations, disable/revoke/uninstall semantics;
- package lifecycle with installation, permission grant, binding, environment release, and enablement kept separate;
- FastAPI health, package-registry, eligibility, audit, status, and metric endpoints, plus an offline deterministic-template fallback component;
- SQLAlchemy persistence with PostgreSQL Compose configuration and a file-backed SQLite direct-run profile;
- append-only audit API/repository skeleton, structured JSON logs, trace correlation, Prometheus metrics, content-addressed local object-store replacement;
- locked Python/TypeScript workspaces, migrations, CI, SBOM/security/architecture checks;
- two reference-package contract fixtures only—no scenario business logic.

## Explicit non-scope

No changes to `industrial-agent-demo`; no OR-Tools or scheduling logic; no anomaly diagnosis logic; no real or de-identified enterprise data; no enterprise IdP/Secret/network; no external model call; no runtime third-party Python/JavaScript loading; no external system write or industrial control capability.

## Direct local run (no Docker)

```bash
uv sync --frozen --all-groups
uv run alembic upgrade head
uv run uvicorn forgeops.api:create_app --factory --host 127.0.0.1 --port 8000
```

The direct profile persists metadata to `.local/forgeops.db` and blobs to `.local/objects`. It is a developer fallback; PostgreSQL remains the target adapter.

```bash
curl http://127.0.0.1:8000/health/live
curl http://127.0.0.1:8000/health/ready
curl -H 'X-ForgeOps-Actor: local-owner' http://127.0.0.1:8000/v1/platform/status
```

## Local service topology

When Docker is available:

```bash
docker compose -f deploy/local/compose.yaml config --quiet
docker compose -f deploy/local/compose.yaml up --build
```

This topology is local synthetic development only. It must not be reused for PREPROD or PROD.

## Repeatable verification

```bash
make bootstrap
make verify
make migration-proof
make smoke
make web-smoke
make sbom
make evidence
```

See `docs/acceptance/EPIC-01-02-evidence.md` for the exact evidence/status rules and `docs/runbooks/local-development.md` for operating steps.
