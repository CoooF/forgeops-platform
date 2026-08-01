from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_epic_02_6b_migration_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migration-round-trip.db'}"
    monkeypatch.setenv("FORGEOPS_DATABASE_URL", database_url)
    configuration = Config("alembic.ini")
    command.upgrade(configuration, "head")
    engine = create_engine(database_url)
    assert engine.connect().execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one() == ("0006")
    expected = {
        "fds_package_versions",
        "fds_installations",
        "fds_installation_package_refs",
        "project_domain_locks",
        "project_domain_lock_package_refs",
        "fds_idempotency_records",
    }
    assert expected.issubset(inspect(engine).get_table_names())
    command.downgrade(configuration, "0005")
    assert expected.isdisjoint(inspect(engine).get_table_names())
    command.upgrade(configuration, "head")
    assert expected.issubset(inspect(engine).get_table_names())
    assert engine.connect().execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one() == ("0006")
    engine.dispose()
