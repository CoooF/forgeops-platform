# ForgeOps repository rules

- Scope is EPIC-01/02, EPIC-02.5, and EPIC-02.6A local synthetic engineering only.
- EPIC-02.5 may implement domain-neutral Principal, Organization, Workspace, Project,
  Membership/RoleAssignment, AuthorizationDecision, and ProjectPackageBinding concepts.
- EPIC-02.6A may implement only domain-neutral FDS manifests, compatibility reports,
  deterministic dependency locks, legacy Scenario compatibility input, and synthetic
  contract fixtures. EPIC-02.6B Registry/Project DomainLock and EPIC-02.6C semantic
  runtime are prohibited until separately approved.
- Never import a reference scenario from `src/forgeops/platform_core`, `platform_contracts`, or `scenario_sdk`.
- Dependency direction is `scenario package -> scenario_sdk -> platform_contracts`.
- Platform concepts must remain domain-neutral. Reference-scenario terms belong only under `scenario-packages/` and test fixtures.
- `forgeops.fds_sdk` must not contain reference-domain conditions or depend on FastAPI,
  SQLAlchemy, Temporal, LLM/model SDKs, graph databases, or solver frameworks.
- FDS validation and resolution never create CatalogItem, Entitlement, Installation,
  Binding, Grant, DomainLock, EnvironmentRelease, or runtime/semantic state.
- Do not implement scheduling, anomaly diagnosis, OR-Tools adapters, external model calls, real-data connectors, RPA, industrial control, or external-system writes.
- PREPROD and PROD must always use `DenyAllActionAdapter`. This invariant is not configurable.
- Executable scenario code is never dynamically imported into the API process. UI extensions are declarative JSON only.
- `X-ForgeOps-Actor` is a LOCAL/TEST authentication adapter input only. It never grants a
  role; every business request must resolve a persisted active principal and pass a
  deny-by-default, server-side scope authorization decision.
- Organizations, workspaces, projects, memberships, project-package bindings, package
  history, and audit history are never physically deleted. Use explicit archive,
  suspend, disable, or revoke transitions.
- Every behavior change needs requirement, ADR, and test IDs in tests or evidence.
- Use locked dependencies. Do not use `latest`, arbitrary third-party plugins, or unverified runtime downloads.
- Preserve audit history. Deletion of tracked audit or package-history data is outside this task.
