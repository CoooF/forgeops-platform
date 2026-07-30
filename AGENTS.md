# ForgeOps repository rules

- Scope is EPIC-01/02 plus EPIC-02.5 local synthetic engineering only.
- EPIC-02.5 may implement domain-neutral Principal, Organization, Workspace, Project,
  Membership/RoleAssignment, AuthorizationDecision, and ProjectPackageBinding concepts.
- Never import a reference scenario from `src/forgeops/platform_core`, `platform_contracts`, or `scenario_sdk`.
- Dependency direction is `scenario package -> scenario_sdk -> platform_contracts`.
- Platform concepts must remain domain-neutral. Reference-scenario terms belong only under `scenario-packages/` and test fixtures.
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
