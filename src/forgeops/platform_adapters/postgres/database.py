from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def create_engine_and_session(database_url: str) -> tuple[Engine, Callable[[], Session]]:
    if database_url.startswith("sqlite"):
        database_path = database_url.rsplit("///", maxsplit=1)[-1]
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, pool_pre_ping=True)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection: object, _: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, factory
