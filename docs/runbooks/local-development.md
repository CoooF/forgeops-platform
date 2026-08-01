# Local synthetic development runbook

## Preconditions

- `uv 0.12.0`, managed Python `3.13.14`, Node `24.14.0`, pnpm `11.1.2`;
- no enterprise credential or real/de-identified data in the working tree;
- Docker is optional for direct mode and required for Compose verification.

## Direct mode

```bash
uv sync --frozen --all-groups
pnpm install --frozen-lockfile
uv run alembic upgrade head
uv run uvicorn forgeops.api:create_app --factory --host 127.0.0.1 --port 8000
```

Use `X-ForgeOps-Actor: local-owner` on all non-health requests. A missing header must return `UNAUTHORIZED`.

## EPIC-02.6B Registry governance walkthrough

Start the API as above, then start the Web shell in a second terminal:

```bash
pnpm --filter @forgeops/web run dev
```

Open the printed local Web URL. The top-level **Domain Registry** surface uses the real
`/v1/fds/package-versions` and Organization Installation APIs. Select an active Project and
open **DomainLock** to create or switch the Project's current immutable lock and inspect
SUPERSEDED history. The page deliberately labels the state as `LOCAL_SYNTHETIC`,
`NOT_ENTERPRISE_VERIFIED`, `authorizationEffect=NONE`, `semanticRuntimeReady=false`, and
`runtimeBindingCreated=false`.

For a stable five-minute API/database walkthrough that creates an isolated SQLite database,
runs a successful version switch, proves Viewer/Outsider boundaries, withdraws a transitive
dependency, verifies impact, and restarts the application, run:

```bash
make epic-02-6b-owner-demo
```

For the real browser/API path, run:

```bash
make e2e
```

The browser test starts a real local API and Web server. It does not use browser-local arrays
as Registry state and does not contact an external Registry, model, artifact service, or
control system.

## EPIC-02.6C semantic and knowledge walkthrough

Start the same API and Web shell, open top-level **Semantic & Knowledge**, then select an
ACTIVE Project and open its **Context** tab. The first page manages strict payload and
KnowledgeAsset versions through the real database. Context resolves a term/source mapping,
compiles an immutable manifest with explicit purpose/evaluation time/item-character budget,
and validates structured JSON references. Ambiguity is shown as candidates; it is never guessed.

The five-minute isolated success/refusal walkthrough is:

```bash
make epic-02-6c-owner-demo
```

It proves exact Registry/DomainLock binding, deterministic digest, exclusions/truncation,
VALID/INVALID Grounding, v1-v2 impact, Viewer/Outsider refusal, restart persistence, and
`agentRuntimeEnabled=false`, `llmEnabled=false`, `ragEnabled=false`,
`workflowRuntimeEnabled=false`. All generated content is neutral and local synthetic.

Run the focused contract/service/Web checks and the real browser path with:

```bash
make epic-02-6c
pnpm --filter @forgeops/web run e2e -- semantic-knowledge.spec.ts
```

## Verification and evidence

```bash
make verify
make migration-proof
make smoke
make web-smoke
make sbom
make evidence
make epic-02-6b
make epic-02-6b-owner-demo
make epic-02-6b-evidence
make epic-02-6c
make epic-02-6c-owner-demo
make epic-02-6c-evidence
```

`make evidence` requires an existing Git commit and the SBOM outputs from the immediately preceding verified run; it binds their digests to that commit.

`make epic-02-6b-evidence` likewise requires a clean, committed, already verified source tree.
It records local test/gate results and digests; it does not rerun enterprise or production
checks and cannot grant enterprise approval.

`make epic-02-6c-evidence` has the same clean-source rule. Run it only after all 02.6C gates,
wheel and SBOM generation; it binds evidence but does not run a model or advance release gates.

Run `uv run alembic downgrade base && uv run alembic upgrade head` only against a disposable local database. Do not use migration downgrade against any shared or enterprise environment.

## Stop/rollback

- Stop API/Worker processes; local package state remains in the database.
- Disable or revoke a package through the lifecycle API; do not remove history.
- If Compose was used, stop services without deleting volumes. Data removal is not part of this runbook.

## Incident boundary

If any real data, enterprise credential, external model request, external write client, or control-system path appears, stop immediately, preserve audit evidence, and notify the project owner. Do not continue under the local approval.
