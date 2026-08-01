from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_migration_creates_missing_sqlite_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "missing" / "nested" / "forgeops.db"
    monkeypatch.setenv("FORGEOPS_DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    command.upgrade(Config("alembic.ini"), "head")
    assert database_path.exists()
    engine = create_engine(f"sqlite+pysqlite:///{database_path}")
    try:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0007"
    finally:
        engine.dispose()
