from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from pydantic import Field

from forgeops.platform_contracts.domain import StrictModel


class AuditEvent(StrictModel):
    event_id: UUID = Field(default_factory=uuid4, alias="eventId")
    event_type: str = Field(alias="eventType", min_length=3)
    actor_ref: str = Field(alias="actorRef", min_length=1)
    resource_ref: str = Field(alias="resourceRef", min_length=1)
    result: str
    reason_code: str = Field(alias="reasonCode")
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC), alias="occurredAt")
    trace_id: str = Field(alias="traceId", min_length=8)
    requirement_ids: tuple[str, ...] = Field(alias="requirementIds")
    test_ids: tuple[str, ...] = Field(default=(), alias="testIds")
    details: dict[str, Any] = Field(default_factory=dict)


class AuditRepository(Protocol):
    def append(self, event: AuditEvent) -> None: ...

    def list_events(self, *, limit: int = 100) -> tuple[AuditEvent, ...]: ...


class InMemoryAuditRepository:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def list_events(self, *, limit: int = 100) -> tuple[AuditEvent, ...]:
        return tuple(self._events[-limit:])
