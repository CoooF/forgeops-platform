# EPIC-02.5 identity, project scope and authorization

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_ENGINEERING` after the commands recorded in the acceptance evidence. Enterprise identity, PostgreSQL runtime, PREPROD/PROD and business acceptance remain blocked.

## Boundary and model

This slice establishes generic Principal, Organization, Workspace, Project, Membership, AuthorizationDecision and ProjectPackageBinding models. It does not implement passwords, enterprise OIDC, FDS, ontology/semantic compilation, workflow execution, reference-scenario business logic, real data or external writes.

`LocalSyntheticAuthAdapter` maps only a controlled DEV/TEST header to a subject reference. INT/PREPROD/PROD select an unavailable fail-closed adapter until enterprise identity is approved. The API then resolves a persisted Principal and performs a fresh authorization decision. An unknown/disabled Principal, missing/suspended/revoked Membership, wrong scope, archived parent, unsafe package state or unsupported role/scope combination fails closed.

Scope rules are explicit:

- a PLATFORM grant is local bootstrap only and applies to platform resources;
- an ORGANIZATION grant applies to that organization and its descendant workspaces/projects;
- a WORKSPACE grant applies to that workspace and its descendant projects;
- a PROJECT grant applies only to that project;
- no grant crosses an Organization boundary, and resource discovery denial returns `RESOURCE_NOT_FOUND`;
- slug uniqueness is global for Organization and parent-relative for Workspace/Project;
- writes use `Idempotency-Key` for creation and `expectedVersion` for optimistic updates/transitions.

Lifecycle state is preserved rather than deleted: Principal `ACTIVE/DISABLED`; Organization `ACTIVE/SUSPENDED/ARCHIVED`; Workspace `ACTIVE/ARCHIVED`; Project `DRAFT/ACTIVE/ARCHIVED`; Membership `ACTIVE/SUSPENDED/REVOKED`; binding `ACTIVE/DISABLED/REVOKED`. Archived ancestors block descendant writes. The final active `ORG_OWNER` is protected. History and scoped audit remain readable.

## Permission matrix

Roles are permission sets interpreted with resource state, scope and environment by `AuthorizationService`; they are not route-level shortcuts. `✓` means the permission exists in the role set, subject to a valid role/scope combination and active hierarchy.

| Role | Workspace create | Project create | Project view | Project update/activate | Project archive | Member manage | Package bind | Audit read |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ORG_OWNER | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| ORG_ADMIN | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| WORKSPACE_ADMIN | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PROJECT_OWNER | — | — | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| PROJECT_EDITOR | — | — | ✓ | ✓ | — | — | — | — |
| PROJECT_VIEWER | — | — | ✓ | — | — | — | — | — |
| PACKAGE_OPERATOR | — | — | ✓ | — | — | — | ✓ | — |
| AUDITOR | — | — | ✓ | — | — | — | — | ✓ |

Additional permissions cover organization/workspace update/archive and package registry view/manage. The source-of-truth exhaustive matrix is `ROLE_PERMISSIONS`; `TEST-IAM-POLICY-001` evaluates every role against every permission on correct and incorrect scopes.

Allowed role scopes are: `ORG_OWNER` PLATFORM/ORGANIZATION; `ORG_ADMIN` ORGANIZATION; `WORKSPACE_ADMIN` WORKSPACE; project roles PROJECT; `PACKAGE_OPERATOR` PLATFORM/ORGANIZATION/PROJECT; `AUDITOR` all scope types. A client-supplied role outside these combinations is rejected.

## Package binding compatibility

New bindings use `project_package_bindings.project_id` plus a fixed installation ID and generic `PackageKind=SCENARIO`. Binding requires `package.bind`, a writable Project, an approved/tested installation, granted manifest permissions, an active/non-revoked installation and a safe current environment boundary. Binding does not release/enable a package or grant data access.

Existing Scenario installation history and legacy string bindings are not rewritten. Legacy history remains readable. New legacy calls containing `project://` are rejected so an arbitrary string cannot impersonate Project scope. Revoked or logically uninstalled packages cannot receive new bindings or new use; historical rows remain investigable.

## API and persistence

Migration `0005` adds constrained/indexed principals, organizations, workspaces, projects, memberships, project-package bindings and idempotency records, plus `scope_ref` and `policy_version` on append-only audit. Routes cover `/v1/me`, hierarchy CRUD/lifecycle, memberships, scoped bindings/permissions/audit and bindable installations. Requests reject extra fields; lists are scope-filtered, deterministically ordered and bounded by limit/offset envelopes.

The Project Center consumes only these APIs. It exposes a clearly labeled development-only Principal selector, Organization/Workspace switching, Project search/filter/lifecycle, Overview/Members/Packages/Audit views and real loading/empty/error/forbidden/conflict/archive states. Refresh and browser tests read the persisted API; there is no fake success state.

## Test IDs

| ID | Coverage |
| --- | --- |
| TEST-IAM-DOMAIN-001 | strict entities, slugs, lifecycle and role/scope validation |
| TEST-IAM-POLICY-001 | every role × every Permission × correct/wrong scope; disabled/suspended denial |
| TEST-IAM-AUTH-001 | missing/forged header, unknown/disabled Principal and auth ≠ authorization |
| TEST-IAM-ISOLATION-001 | cross-Organization/Workspace/Project filtering and uniform concealment |
| TEST-IAM-API-001 | 200/201, 401, 404, 409, 422, idempotency and optimistic concurrency |
| TEST-IAM-MEMBERSHIP-001 | grant, immediate suspension/revocation and final Owner protection |
| TEST-PKG-PROJECT-BINDING-001 | real Project target, package eligibility, archived denial and legacy guard |
| TEST-IAM-AUDIT-001 | actor/scope/result/reason/trace/policy correlation and append-only history |
| TEST-OPS-MIGRATION-002 | `0004 → 0005`, full downgrade/upgrade and clean install |
| TEST-OPS-PROJECT-RESTART-001 | Organization/Workspace/Project survives independent API restart |
| TEST-WEB-PROJECT-001 | React API loading/error/component behavior |
| TEST-WEB-PROJECT-E2E-001 | Owner hierarchy/bind, Viewer read-only, outsider isolation, archive/reload |
| TEST-ARCH-002 | Core and Web source remain reference-domain neutral |

## Known limits

Docker/PostgreSQL services, enterprise OIDC/SCIM, enterprise policy publication, remote CI, signing roots, network controls, PREPROD/PROD, real data and business UAT were not run. Those items cannot advance past `CODE_COMPLETE` or `BLOCKED` from this local SQLite/browser evidence. EPIC-02.6 may consume only the verified generic Project scope/binding target; it must separately prove FDS manifests, semantic isolation and consumer contracts.
