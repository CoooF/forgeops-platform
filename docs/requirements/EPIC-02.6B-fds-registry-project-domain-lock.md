# EPIC-02.6B FDS Registry, organization installation, and Project DomainLock

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING`. `REQ-FDS-001`
remains `CLARIFYING / PARTIAL`; this slice cannot advance enterprise supply-chain,
semantic/knowledge runtime, workflow runtime, real-data, business-UAT, or release gates.

## Product boundary

This slice persists immutable, validated FDS package versions; lets an authorized
Organization resolve and install a fixed Domain or Organization Overlay composition in
`INSTALLED_DISABLED`; lets an ACTIVE Project select one immutable current DomainLock;
and derives direct/transitive impact when a referenced Registry version is quarantined or
withdrawn. The Web Shell exposes these real API/database states.

It does not create CatalogItem, Offer, Entitlement, Grant, Scenario installation,
ProjectPackageBinding, EnvironmentRelease, Worker, Run, semantic object, knowledge index,
Context Compiler, model call, remote download, or external-system action. FDS Scenario
Descriptors remain investigation-only Registry records; the existing Scenario Registry is
the sole Scenario installation/runtime truth.

## Invariants

- A Registry `packageId + packageVersion` is unique and immutable. Re-registering the
  same canonical Manifest/digest returns the same record; a different digest returns
  `PACKAGE_VERSION_DIGEST_CONFLICT`.
- Registration first uses `FDS_MANIFEST_ADAPTER`/`FdsManifestValidator`; invalid input
  creates no Registry row. `FIRST_PARTY_LOCAL` and `local-sha256` never mean enterprise
  signature or license verification.
- Organization Overlay records are `ORGANIZATION_PRIVATE`, reference an existing owner
  Organization, and are not discoverable outside that Organization. Private Component
  records follow the same owner boundary.
- Registry governance changes state and reason only; Manifest, content/manifest digest,
  publisher, license, visibility, classification, and owner Scope never change in place.
  Rows and history are never physically deleted.
- Organization installation candidates come only from visible, usable Registry records.
  The verified `DependencyResolver` produces the exact lock; every node is tied to a
  Registry version ID and rechecked for version, digest, state, and Organization Scope.
- Installation persistence is atomic and idempotent. It has
  `authorizationEffect=NONE`, `runtimeStateCreated=false`, and
  `semanticRuntimeReady=false`; it never creates a Grant, Binding, Release, or runtime.
- ProjectDomainLock is immutable package/edge/digest content. An ACTIVE Project has at
  most one `CURRENT` lock. Switching creates a new lock and atomically marks the old lock
  `SUPERSEDED`; history remains readable.
- Project and installation Organizations must match. Archived Projects, disabled/revoked/
  logically-uninstalled installations, digest drift, quarantined/withdrawn dependencies,
  wrong Scope, and concurrent current-lock creation fail closed.
- Registry withdrawal/quarantine blocks new installation and new Project locks, derives
  `AT_RISK/BLOCKED_FOR_NEW_USE` for existing records, and lists impacted installations and
  locks without rewriting their immutable lock content or selecting a replacement.
- Logical uninstall is blocked while a current ProjectDomainLock references the
  installation. No state transition physically deletes Registry, installation, lock, or
  audit history.
- `Idempotency-Key` protects creates; mutable governance operations require `If-Match`.
  Reusing a key with another canonical payload is `IDEMPOTENCY_CONFLICT`.
- Authorization is server-side and deny-by-default. Cross-Scope list/detail/impact/error
  responses do not disclose private package, Organization, Project, or count information.

## Stable states and API

Registry states are `REGISTERED_VALIDATED`, `QUARANTINED`, `WITHDRAWN`, and
`LOGICALLY_UNINSTALLED`. Installation states are `INSTALLED_DISABLED`, `DISABLED`,
`REVOKED`, and `LOGICALLY_UNINSTALLED`. Project lock states are `CURRENT`,
`SUPERSEDED`, and `REVOKED`; withdrawal risk is derived health, not lock mutation.

Protected `/v1/fds/package-versions`, Organization `/domain-installations`, and Project
`/domain-locks` routes provide validation, registration, filtering/detail, governance,
impact, preview/install, lock content/diff, current/history, and lifecycle transitions.
Responses expose immutable facts, governance state, install/lock state, and derived health
as separate fields. They never return ORM objects, stack traces, private Manifest data to
unauthorized users, or enterprise trust claims.

## Authorization intent

Permissions separately cover FDS Registry view/manage, Organization installation
view/manage, Project DomainLock view/manage, and impact view. Platform/Package Operator
manages public Registry versions. Organization Owner/Admin manages its private Overlay or
Component and Organization installations. Project Owner (and inherited Organization or
Workspace administrators) creates/switches locks. Project Editor/Viewer may read lock
summaries but cannot register, install, or switch. Auditor reads only within an applicable
Scope. Outsider discovers nothing.

## Stable test IDs

| ID | Required evidence |
| --- | --- |
| TEST-FDS-REGISTRY-001 | Four kinds, strict validation, immutable/idempotent version, digest conflict, governance transitions |
| TEST-FDS-REGISTRY-SCOPE-001 | Public/private visibility, Overlay owner, cross-Organization list/detail/impact concealment |
| TEST-FDS-INSTALL-001 | Registry-only resolution, exact lock/ref persistence, idempotency, disabled/no-side-effect state |
| TEST-FDS-INSTALL-NEG-001 | Missing/unavailable/private/drift/permission-budget/concurrency failures leave no partial install |
| TEST-FDS-DOMAINLOCK-001 | Organization match, unique current, immutable switch, SUPERSEDED history and diff |
| TEST-FDS-DOMAINLOCK-NEG-001 | Archived/cross-Scope/no-permission/withdrawn/tampered/double-current rejection |
| TEST-FDS-IMPACT-001 | Direct/transitive impact, new-use block, unchanged history |
| TEST-FDS-AUTH-001 | Role/action/correct-wrong Scope, immediate revocation, backend enforcement |
| TEST-FDS-API-001 | 201/200/401/404/409/422, idempotency, If-Match, stable OpenAPI/error |
| TEST-FDS-PERSISTENCE-001 | Migration round trip, restart persistence, current/history survival |
| TEST-FDS-LEGACY-002 | Existing Scenario Registry/Binding/fixtures unchanged; descriptor is no second runtime truth |
| TEST-WEB-FDS-001 | Operator/Owner success, Viewer read-only, Outsider hidden, refresh and withdrawal failure in real browser/API |
| TEST-ARCH-004 | FDS SDK one-way dependency, domain-neutral Core/Web, runtime artifact excludes reference business code |

`TEST-FDS-002` gains only Registry/DomainLock partial evidence; runtime replay remains
unverified. `TEST-FDS-004` remains `NOT_STARTED/BLOCKED` because enterprise publisher,
signature, SBOM verification, license/legal review, Artifact service, and hostile-content
controls are absent.

## Acceptance boundary

The slice may become `VERIFIED_FOR_LOCAL_SYNTHETIC_REGISTRY_ENGINEERING` only after the
focused tests, migration upgrade/downgrade/upgrade and clean install, independent API
restart, real browser E2E, prior 02.6A regression, full verify/build/SBOM/security/
architecture gates, deterministic OpenAPI/FDS exports, Owner Summary, and commit-bound
machine evidence all pass. PostgreSQL service behavior, enterprise identity/supply chain,
PREPROD/PROD, G2/G4/G5A/G5B, and product acceptance remain blocked.
