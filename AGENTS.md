# ForgeOps repository rules

- Scope is EPIC-01/02 local synthetic engineering only.
- Never import a reference scenario from `src/forgeops/platform_core`, `platform_contracts`, or `scenario_sdk`.
- Dependency direction is `scenario package -> scenario_sdk -> platform_contracts`.
- Platform concepts must remain domain-neutral. Reference-scenario terms belong only under `scenario-packages/` and test fixtures.
- Do not implement scheduling, anomaly diagnosis, OR-Tools adapters, external model calls, real-data connectors, RPA, industrial control, or external-system writes.
- PREPROD and PROD must always use `DenyAllActionAdapter`. This invariant is not configurable.
- Executable scenario code is never dynamically imported into the API process. UI extensions are declarative JSON only.
- Every behavior change needs requirement, ADR, and test IDs in tests or evidence.
- Use locked dependencies. Do not use `latest`, arbitrary third-party plugins, or unverified runtime downloads.
- Preserve audit history. Deletion of tracked audit or package-history data is outside this task.
