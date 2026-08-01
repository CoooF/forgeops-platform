# ForgeOps Platform

Independent EPIC-01/02, EPIC-02.5, and EPIC-02.6A/B/C engineering baseline for the ForgeOps Platform Core, Scenario SDK, generic project boundary, FDS v0.1, Registry/Project DomainLock, and a domain-neutral semantic/knowledge thin slice. It runs only with local synthetic fixtures and is not approved for enterprise, preproduction, production, real data, business UAT, reference business, Agent/LLM/RAG, or Workflow use.

## 产品负责人进度与五分钟验证

从 [产品负责人进度总览](docs/acceptance/PRODUCT-OWNER-PROGRESS.md) 进入各 Epic 的大白话说明、
成功/拒绝案例、五分钟验证路径、明确未实现项和证据提交。当前结果均不代表企业验收或生产发布。

## What is implemented

- strict domain-neutral platform contracts and versioned execution envelopes;
- strict Scenario Manifest/pack contracts, compatibility validation, local digest attestation, permissions, budgets, migrations, disable/revoke/uninstall semantics;
- package lifecycle with installation, permission grant, binding, environment release, and enablement kept separate;
- persisted Principal, Organization, Workspace, Project, Membership and real Project-to-package binding models with fail-closed scoped authorization;
- replaceable `AuthPort`, centralized `AuthorizationPort`, local synthetic identity adapter, explicit role/permission inheritance and append-only decision evidence;
- FastAPI health, package-registry, eligibility, audit, status, and metric endpoints, plus an offline deterministic-template fallback component;
- SQLAlchemy persistence with PostgreSQL Compose configuration and a file-backed SQLite direct-run profile;
- append-only audit API/repository skeleton, structured JSON logs, trace correlation, Prometheus metrics, content-addressed local object-store replacement;
- a real-API React Project Center for hierarchy switching, project lifecycle, members, packages and scoped audit, with Playwright isolation/restart coverage;
- locked Python/TypeScript workspaces, migrations, CI, SBOM/security/architecture checks;
- two reference-package contract fixtures only—no scenario business logic.
- strict domain-neutral FDS Domain/Organization Overlay/Scenario/Component contracts,
  deterministic offline dependency locks, permission/budget deltas, and an explicit
  non-mutating Scenario SDK 0.x compatibility adapter;
- persisted FDS Registry, Organization Installation, immutable current/history ProjectDomainLock,
  withdrawal impact, and real Domain Registry/Project management pages;
- strict Ontology/Terminology/Mapping and KnowledgeAsset versions bound to exact locked Registry
  components, deterministic semantic query/ContextManifest, structural Grounding and impact;
- real Semantic & Knowledge and Project Context pages backed by the API/database. There is no
  Agent/model/RAG, graph/vector index, Workflow/Run, or reference-business claim.

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
curl -H 'X-ForgeOps-Actor: local-owner' http://127.0.0.1:8000/v1/me
curl -H 'X-ForgeOps-Actor: local-owner' http://127.0.0.1:8000/v1/organizations
```

`X-ForgeOps-Actor` is a DEV/TEST subject lookup only and grants nothing. Controlled seeded subjects include `local-owner`, `local-editor`, `local-viewer`, `local-outsider` and `local-disabled`; their persisted memberships, not the header value, determine access. Enterprise identity is not connected.

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
make e2e
make epic-02-5
make epic-02-6a
make epic-02-6b
make epic-02-6c
make epic-02-6c-owner-demo
make sbom
make evidence
```

See [EPIC-02.6C Evidence](docs/acceptance/EPIC-02.6C-evidence.md) and the
[02.6C requirement](docs/requirements/EPIC-02.6C-semantic-knowledge-runtime.md) for the exact
local-only boundary. [Local development](docs/runbooks/local-development.md) contains the
five-minute owner and browser walkthroughs.
