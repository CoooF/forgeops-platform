from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InstallationRow(Base):
    __tablename__ = "scenario_package_installations"
    __table_args__ = (UniqueConstraint("package_id", "package_version"),)

    installation_id: Mapped[UUID] = mapped_column(primary_key=True)
    package_id: Mapped[str] = mapped_column(String(64), index=True)
    package_version: Mapped[str] = mapped_column(String(32))
    content_digest: Mapped[str] = mapped_column(String(80))
    manifest: Mapped[dict[str, object]] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(32), index=True)
    granted_permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    binding_refs: Mapped[list[str]] = mapped_column(JSON, default=list)
    uninstalled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EnvironmentReleaseRow(Base):
    __tablename__ = "scenario_package_environment_releases"
    __table_args__ = (UniqueConstraint("installation_id", "environment"),)

    release_id: Mapped[UUID] = mapped_column(primary_key=True)
    installation_id: Mapped[UUID] = mapped_column(
        ForeignKey("scenario_package_installations.installation_id"), index=True
    )
    environment: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(32))
    action_adapter: Mapped[str] = mapped_column(String(32))
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    actor_ref: Mapped[str] = mapped_column(String(256))
    resource_ref: Mapped[str] = mapped_column(String(256), index=True)
    result: Mapped[str] = mapped_column(String(32))
    reason_code: Mapped[str] = mapped_column(String(128))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    requirement_ids: Mapped[list[str]] = mapped_column(JSON)
    test_ids: Mapped[list[str]] = mapped_column(JSON)
    details: Mapped[dict[str, object]] = mapped_column(JSON)
