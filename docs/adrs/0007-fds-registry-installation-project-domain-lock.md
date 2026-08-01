# ADR-0007: FDS Registry, installation, and immutable Project DomainLock

- Status: `ACCEPTED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING`
- Date: 2026-08-01
- Requirements: `REQ-FDS-001` (partial), `REQ-IAM-001`, `REQ-POL-001`
- Tests: `TEST-FDS-REGISTRY-001`, `TEST-FDS-REGISTRY-SCOPE-001`,
  `TEST-FDS-INSTALL-001`, `TEST-FDS-INSTALL-NEG-001`,
  `TEST-FDS-DOMAINLOCK-001`, `TEST-FDS-DOMAINLOCK-NEG-001`,
  `TEST-FDS-IMPACT-001`, `TEST-FDS-AUTH-001`, `TEST-FDS-API-001`,
  `TEST-FDS-PERSISTENCE-001`, `TEST-FDS-LEGACY-002`, `TEST-WEB-FDS-001`,
  `TEST-ARCH-004`

## Context

ADR-0006 established pure FDS manifests and deterministic DependencyLocks but deliberately
created no state. A Project cannot safely consume a moving package graph, and a withdrawn
transitive dependency cannot be investigated, until Registry facts, Organization install
records, and immutable Project selections exist. Existing Scenario installation and
ProjectPackageBinding history must remain a separate truth.

## Decision

Add `forgeops.platform_core.domain_registry` as a domain-neutral application module that
depends on `forgeops.fds_sdk`, identity/policy Ports, and Repository Protocols. The pure
`fds_sdk` does not depend back on Registry, SQLAlchemy, FastAPI, identity, or Project.

Persist separate records and reference tables:

```text
FdsPackageVersionRecord (immutable Manifest facts + mutable governance state)
  -> FdsInstallation (Organization + immutable DependencyLock, disabled)
    -> ProjectDomainLock (Project's immutable current/history selection)
```

Registry package/version is unique. Organization-private Overlay/Component rows carry a
real owner Organization FK. Installation nodes and Project lock nodes carry explicit FKs
to Registry versions so impact queries do not rely on unindexed JSON alone. Canonical
Manifest and DependencyLock JSON remain stored for exact historical investigation and are
revalidated on use.

A partial unique index enforces one `CURRENT` ProjectDomainLock per Project in SQLite and
PostgreSQL. Lock switching and its success audit are one database transaction: the old
row becomes `SUPERSEDED`, the new immutable row and package references are inserted, and
an idempotency record is saved. Registration and installation success audit use the same
pattern. Mutable governance uses optimistic `version` checks. Service checks provide
clear errors; database uniqueness/FKs remain the race-condition backstop.

The existing general AuditRepository has no shared Unit of Work. Successful Registry,
installation, and DomainLock writes therefore receive an `AuditEvent` inside the domain
SQL repository transaction. Authentication/authorization denials and pre-persistence
validation failures still append through the existing AuditRepository in a separate
transaction. A database outage between a denial and its audit may lose denial evidence;
this local limitation is documented and cannot be represented as enterprise atomic audit.

Registry governance does not rewrite installations or locks. Health is derived from their
referenced Registry states. Quarantine/withdrawal blocks new use and produces reference-
level impacts while preserving historical Manifest/lock content. Logical installation
uninstall is blocked by a current Project lock.

FDS Scenario Descriptor registration is investigation-only. It cannot be an installation
root and never creates existing Scenario Installation or ProjectPackageBinding rows. This
prevents two runtime truths.

## Authorization and trust

Public Registry management requires a Platform-scoped FDS management permission.
Organization-private publication/installation requires an applicable active Organization
grant. Project lock read/manage is checked against the real Project and ancestor Scope.
Private records are filtered before detail, impact, count, or error construction.

Only `REGISTERED_VALIDATED` local records can enter a new lock. `FIRST_PARTY_LOCAL` and
`local-sha256` mean deterministic local integrity only. Installation sets
`authorizationEffect=NONE`, `runtimeStateCreated=false`, and
`semanticRuntimeReady=false`; Project locks also set `runtimeBindingCreated=false`.

## Consequences and limits

The platform can now persist, install, pin, compare, and investigate FDS package graphs
without adding semantic or workflow runtime. JSON plus normalized reference tables is
sufficient for this slice; no Kafka, Redis, graph/vector database, object store, remote
Registry, or dynamic import is introduced.

PostgreSQL service concurrency, enterprise OIDC, publisher/namespace ownership,
signature roots, license/legal approval, SBOM verification, remote Artifact handling,
PREPROD/PROD, semantic differences, historical Run replay, and business validity remain
unverified or blocked. If future consumers require content-addressed external locks, a new
compatible storage Port may replace inline JSON without mutating historical lock IDs or
digests.
