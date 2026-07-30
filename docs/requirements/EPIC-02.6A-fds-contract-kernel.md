# EPIC-02.6A FDS contract kernel

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING` only after the commands and
source commit recorded in the acceptance evidence. `REQ-FDS-001` remains
`CLARIFYING / PARTIAL`; FDS Registry, Project DomainLock, semantic runtime, enterprise
supply chain, real data and business E2E are not implemented.

## Scope and invariants

This slice supplies reusable domain-neutral code for strict FDS v0.1 manifests,
deterministic offline dependency resolution, fixed locks, stable structured errors,
canonical JSON, and explicit Scenario SDK 0.x compatibility input.

It never:

- accesses a network, Registry, database, remote Artifact, model, graph store, or source
  system while validating or resolving;
- installs, grants, binds, releases, enables, withdraws, or persists a package;
- creates CatalogItem, Entitlement, Installation, Binding, Grant, EnvironmentRelease,
  Project DomainLock, semantic object, knowledge index, or runtime state;
- imports or executes arbitrary package code in the API process;
- implements manufacturing, steel-cord, scheduling, diagnosis, or any other business
  behavior;
- changes the existing Scenario Manifest Schema, lifecycle records, installation history,
  ProjectPackageBinding, audit history, API, database, migration, or frontend.

All fixtures are `FIRST_PARTY_LOCAL` and `SYNTHETIC`. Local digest attestation is not an
enterprise signature. PREPROD/PROD remain fixed to `DenyAllActionAdapter`.

## Contract requirements

The API version is `forgeops.ai/fds/v1alpha1`. Four strict kinds are exported:

- Domain declares its namespace, extends/imports, Component refs, competency-question
  refs, applicability, dependencies, capabilities and governance metadata.
- Organization Overlay is organization-private, names the Domain capabilities it may
  override, limits override kinds, and has no real Organization binding in this slice.
- Scenario declares required Domain capabilities, Component refs, input/output contract
  digests, permissions and budgets. A legacy descriptor may omit facts absent from the old
  source only when it carries an explicit `legacySource` and compatibility limitations.
- Component declares one of ONTOLOGY, TERMINOLOGY, KNOWLEDGE, AGENT_PROFILE, SKILL,
  MCP_SERVER, CONNECTOR, DATA_MAPPING, POLICY, EVALUATION, or UI_EXTENSION, plus runtime
  form, Artifact boundary, capabilities, namespaces, dependencies and applicability.

Every kind shares publisher/namespace owner, license and license reference, provenance
digest, visibility/trust tier/classification, content digest and Artifact/SBOM/local
attestation, Platform/FDS/Scenario SDK ranges, support status, prohibited uses, requested
permissions/resources, dependency allowances, lifecycle retention, evaluations,
conflicts, capabilities, and namespaces. Unknown fields, kinds, Component kinds, and
permissions fail closed.

Executable Artifacts must declare both `workerBoundary=isolated-worker` and Component
`runtimeForm=ISOLATED_WORKER`. Secret/credential fields are absent from the schema and are
rejected as unknown; the kernel does not claim content scanning.

## Resolver and lock requirements

Input is a root PackageRef, candidate manifest set, exact target Platform/FDS/Scenario SDK
versions, and the explicit optional-dependency flag. Package releases are strict `X.Y.Z`;
ranges follow the PEP 440 subset documented in ADR-0006. The resolver is pure and:

1. validates every candidate and duplicate ID/version digest invariant;
2. orders candidates by package ID, descending compatible version, and canonical JSON;
3. chooses the highest legal candidate with deterministic backtracking;
4. validates kind/Component kind/capability/digest expectations and target compatibility;
5. rejects missing required dependencies, incompatible ranges, ambiguity, cycles, direct
   conflicts, layer/public-private violations, provider conflicts and missing Domain
   capabilities;
6. aggregates direct/transitive requested permissions and resources and rejects values not
   declared or accepted by the root;
7. emits dependency-first topological nodes, stable edges/skips, source/version/kind/digest,
   totals/deltas, `authorizationEffect=NONE`, and `runtimeStateCreated=false`;
8. canonicalizes all contract-set arrays and object keys and hashes the lock with SHA-256;
9. returns no partial lock on any issue and orders all issues by code, path, and message.

## Synthetic consumer fixtures

The contract graph is deliberately content-free:

```text
core-semantics Component
  -> manufacturing-shape Domain
    -> steel-cord-shape Domain
      -> synthetic organization Overlay
        -> contract-shape Scenario

core-semantics Component
  -> reference-domain-a Domain
```

The first branch proves layering and private Overlay structure only. The second proves the
same production contract code accepts a non-manufacturing shape with no manufacturing
import or condition. Neither is business-valid or a cross-industry E2E.

Negative cases cover missing, range mismatch, ambiguity, digest conflict, cycle, direct
conflict, package/Component kind mismatch, capability/namespace conflict, public/private
violation, permission/resource expansion, target incompatibility, executable boundary,
unknown permission and lock tampering.

## Legacy compatibility

Both existing Scenario fixtures must first pass their unchanged `ManifestValidator`. The
adapter preserves old identifiers, versions, Artifact digest, permissions, ResourceBudget,
SDK range, retention behavior and all declaration summary references. It is deterministic,
side-effect free, does not import scenario_registry, and reports absent FDS facts rather
than manufacturing them. Existing installation and Project binding regressions remain in
the full test suite.

## Stable test IDs

| ID | Verified local contract behavior |
| --- | --- |
| TEST-FDS-CONTRACT-001 | Four strict kinds, Component kinds, metadata, JSON Schema, unknown-field/kind rejection |
| TEST-FDS-DEPENDENCY-001 | required/optional, version choice/backtracking, missing, ambiguity, cycle, conflict, topology |
| TEST-FDS-LAYER-001 | legal/illegal Domain/Overlay/Scenario/Component direction and public/private isolation |
| TEST-FDS-PERMISSION-001 | permission/budget totals and delta; unknown/expanded requests fail; no authorization effect |
| TEST-FDS-LOCK-001 | exact version/source/digest, canonical JSON, shuffled input and consecutive export SHA-256 |
| TEST-FDS-LEGACY-001 | two unchanged Scenario fixtures, preserved summaries and deterministic limited compatibility |
| TEST-FDS-XDOM-CONTRACT-001 | second-domain shape uses the same contract with no production reference-domain branch |
| TEST-FDS-SEC-001 | credential/Secret field, digest, private content, executable boundary and lock tamper rejection |
| TEST-ARCH-003 | FDS SDK excludes reference domains and FastAPI/SQLAlchemy/Temporal/model/solver dependencies |

`TEST-FDS-001` may cite the completed schema/lock sub-evidence as local partial evidence.
`TEST-FDS-002` runtime migration, `TEST-FDS-004` enterprise supply chain,
`TEST-XDOM-001`, `REQ-SEM-001`, `REQ-KNW-001`, and `REQ-GRD-001` remain unverified.

## Acceptance boundary

The slice can be marked `VERIFIED_FOR_LOCAL_SYNTHETIC_CONTRACT_ENGINEERING` only when
`make epic-02-6a`, `make verify`, `make smoke`, `make web-smoke`, `make e2e`, and
`make sbom` pass; two consecutive FDS exports match; source/artifact architecture scans
pass; the source commit is clean before machine evidence generation; and the acceptance
evidence accurately keeps 02.6B/02.6C, enterprise gates, G2/G4/G5A/G5B and business
validity unchanged.
