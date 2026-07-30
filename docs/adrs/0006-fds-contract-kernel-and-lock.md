# ADR-0006: FDS v0.1 contract kernel and deterministic dependency lock

- Status: `ACCEPTED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING`
- Date: 2026-07-30
- Requirements: `REQ-FDS-001` (partial only), `REQ-SDK-001`
- Tests: `TEST-FDS-CONTRACT-001`, `TEST-FDS-DEPENDENCY-001`,
  `TEST-FDS-LAYER-001`, `TEST-FDS-PERMISSION-001`, `TEST-FDS-LOCK-001`,
  `TEST-FDS-LEGACY-001`, `TEST-FDS-XDOM-CONTRACT-001`, `TEST-FDS-SEC-001`,
  `TEST-ARCH-003`

## Context

The existing Scenario SDK 0.1 proves strict manifests, local digest attestation,
permissions, budgets, package lifecycle and isolated execution metadata. It does not
separate reusable Domain, organization-private Overlay, Scenario, and independently
published Component contracts. The production FDS direction requires that separation,
but Registry persistence, Project DomainLock, semantic runtime, enterprise supply chain,
and business execution are later slices.

## Decision

`forgeops.fds_sdk` is a pure, offline contract library. It defines strict, versioned,
unknown-field-forbidden models for `DOMAIN`, `ORGANIZATION_OVERLAY`, `SCENARIO`, and
`COMPONENT`, plus the eleven required Component kinds. All manifests carry publisher,
namespace owner, local trust tier, license/provenance boundaries, visibility,
classification, compatibility, applicability/prohibited use, lifecycle, Artifact/SBOM
metadata, permissions, budgets, dependency/conflict declarations, capabilities, and
namespaces.

Package releases use canonical `X.Y.Z` versions only. Dependency and compatibility
ranges use PEP 440 `SpecifierSet` syntax. This is explicit because PEP 440 is not silently
treated as full SemVer: prereleases, local versions, epochs, post releases, and arbitrary
package-version spellings are outside FDS v0.1 package releases. The resolver selects the
highest compatible canonical version, processes equal inputs in sorted canonical order,
and deterministically backtracks when a higher candidate makes the graph illegal.
Distinct manifests at the same ID/version are ambiguous; distinct content digests at the
same ID/version are a digest conflict.

Required dependencies must resolve. Optional dependencies use one explicit rule:

- `include_optional=true` (default): include the highest legal matching candidate when
  one exists; a missing or range-incompatible optional candidate is recorded as skipped;
  once included, an illegal subtree is not silently ignored.
- `include_optional=false`: skip every optional dependency and record its package ID.

The dependency direction is fixed:

```text
Scenario -> Organization Overlay / Domain / Component
Organization Overlay -> Domain / Component
Domain -> Domain / Component
Component -> Domain / Component
```

Domain and Component cannot depend on Scenario; Domain cannot depend on Overlay. Public
Domain cannot depend on private content. Overlay must be organization-private and name a
Domain capability it overrides. Namespace/capability conflicts, cycles, direct conflicts,
missing capabilities, incompatible targets, digest conflicts, unknown permissions, and
transitive permission/resource expansion all fail closed with stable sorted issues and no
partial lock.

The root explicitly declares accepted dependency permissions and a dependency budget
allowance. Resolution reports requested totals and delta only. It has
`authorizationEffect=NONE` and `runtimeStateCreated=false`; it cannot create a Grant,
Installation, Binding, Release, Entitlement, CatalogItem, Project DomainLock, or runtime
state.

Canonical JSON sorts object keys and all contract-set arrays before SHA-256. Lock nodes
are dependency-first topological order, edges and errors are stable sorted sequences, and
the lock digest excludes only its own `lockDigest` field. Exported JSON Schema, native
example lock, and two legacy compatibility reports are generated twice in the dedicated
gate and must have identical SHA-256 values.

## Legacy Scenario decision

`LegacyScenarioAdapter` first runs the existing `ScenarioManifest` and
`ManifestValidator`. It then preserves package ID/version, Artifact digest/attestation,
permissions, ResourceBudget, SDK range, lifecycle retention, and every declaration
summary reference. It never mutates the original manifest or package history.

Facts absent from Scenario SDK 0.x are not invented: the descriptor has no declared FDS
Domain capability, no input/output content digest, and an unverified `UNSPECIFIED`
license. The deterministic compatibility report marks these limitations and
`resolverReady=false`. This is contract compatibility evidence, not runtime migration or
Project DomainLock evidence.

## Consequences and boundaries

The contract kernel and synthetic graph can be reused without a database, API, frontend,
network, model, graph engine, or domain implementation. The second-domain fixture proves
only that the same schema accepts another neutral contract shape; it does not advance G5B
or `TEST-XDOM-001`.

Enterprise signature roots, private Registry enforcement, content scanning, withdrawals,
license/legal review, PostgreSQL, PREPROD/PROD, Domain installation and rollback, semantic
mapping/query/grounding, Knowledge/RAG, and real multi-domain E2E remain unimplemented or
blocked. FDS remains a ForgeOps product protocol, not an industry or public standard.
