FROM ghcr.io/astral-sh/uv:0.12.0-python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY apps/api ./apps/api
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev --no-install-project
RUN uv sync --frozen --no-dev

USER 65532:65532
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "forgeops.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
