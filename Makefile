.PHONY: bootstrap format lint type test contract security architecture build artifact-architecture sbom migration-proof smoke web-smoke verify evidence

bootstrap:
	uv sync --frozen --all-groups
	pnpm install --frozen-lockfile

format:
	uv run ruff format --check .
	pnpm run format:check

lint:
	uv run ruff check .
	pnpm run lint

type:
	uv run mypy src apps/api
	pnpm run typecheck

test:
	uv run pytest -q --cov=forgeops --cov-report=term-missing --cov-report=xml
	pnpm run test

contract:
	uv run pytest -q tests/contract

security:
	uv run python scripts/security_scan.py
	uv run pip-audit
	pnpm audit --audit-level high
	pnpm peers check

architecture:
	uv run python scripts/check_architecture.py

build:
	uv build
	pnpm run build

artifact-architecture: build
	uv run python scripts/check_artifact_architecture.py

sbom:
	mkdir -p artifacts/generated
	uv run cyclonedx-py environment --output-format JSON --output-file artifacts/generated/python-sbom.cdx.json
	pnpm list --json --depth Infinity > artifacts/generated/node-dependency-tree.json
	uv run python scripts/generate_node_sbom.py

migration-proof:
	FORGEOPS_DATABASE_URL=sqlite+pysqlite:///./.local/migration-proof.db uv run alembic upgrade head
	FORGEOPS_DATABASE_URL=sqlite+pysqlite:///./.local/migration-proof.db uv run alembic current
	FORGEOPS_DATABASE_URL=sqlite+pysqlite:///./.local/migration-proof.db uv run alembic downgrade base
	FORGEOPS_DATABASE_URL=sqlite+pysqlite:///./.local/migration-proof.db uv run alembic upgrade head
	FORGEOPS_DATABASE_URL=sqlite+pysqlite:///./.local/migration-proof.db uv run alembic current

smoke:
	uv run python scripts/standalone_api_smoke.py

web-smoke:
	sh scripts/standalone_web_smoke.sh

verify: format lint type test contract security architecture artifact-architecture

evidence:
	uv run python scripts/collect_evidence.py
