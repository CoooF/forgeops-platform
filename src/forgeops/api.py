from __future__ import annotations

import base64
import binascii
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Any, cast
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse
from opentelemetry import trace
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from forgeops.config import ActionAdapterKind, Settings
from forgeops.observability import configure_observability
from forgeops.platform_adapters.postgres.database import create_engine_and_session
from forgeops.platform_adapters.postgres.repositories import (
    SqlAuditRepository,
    SqlInstallationRepository,
)
from forgeops.platform_contracts.domain import Environment
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.scenario_registry.service import ScenarioPackageService

LOGGER = logging.getLogger("forgeops.api")
REQUESTS = Counter("forgeops_http_requests_total", "HTTP requests", ("method", "path", "status"))
PACKAGE_OPERATIONS = Counter(
    "forgeops_package_operations_total", "Package operations", ("operation", "result")
)


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ManifestSubmission(ApiModel):
    manifest: dict[str, Any]
    artifact_payload_base64: str = Field(alias="artifactPayloadBase64")

    def artifact_payload(self) -> bytes:
        try:
            return base64.b64decode(self.artifact_payload_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ForgeOpsError(
                ErrorCode.INPUT_INVALID,
                "artifactPayloadBase64 is not valid base64",
                http_status=422,
            ) from exc


class PermissionGrantRequest(ApiModel):
    permissions: tuple[str, ...]


class BindingRequest(ApiModel):
    binding_ref: str = Field(alias="bindingRef", min_length=1)


class ReleaseRequest(ApiModel):
    environment: Environment
    action_adapter: ActionAdapterKind = Field(alias="actionAdapter")


def require_local_actor(
    x_forgeops_actor: Annotated[str | None, Header()] = None,
) -> str:
    if not x_forgeops_actor:
        raise ForgeOpsError(
            ErrorCode.UNAUTHORIZED,
            "X-ForgeOps-Actor is required for local engineering API access",
            http_status=401,
        )
    return x_forgeops_actor


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    configure_observability(resolved.service_name, resolved.log_level)
    engine, session_factory = create_engine_and_session(resolved.database_url)
    installations = SqlInstallationRepository(session_factory)
    audit = SqlAuditRepository(session_factory)
    packages = ScenarioPackageService(installations, audit)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        LOGGER.info(
            "application_started",
            extra={
                "trace_id": "startup",
                "environment": resolved.environment.value,
                "action_adapter": resolved.action_adapter.value,
            },
        )
        yield
        engine.dispose()

    app = FastAPI(
        title="ForgeOps Platform API",
        version="0.1.0",
        description="Local synthetic EPIC-01/02 baseline; advisory-only",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.engine = engine
    app.state.installations = installations
    app.state.audit = audit
    app.state.packages = packages

    @app.exception_handler(ForgeOpsError)
    async def forgeops_error_handler(_: Request, exc: ForgeOpsError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content={"error": exc.as_dict()})

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next: Any) -> Response:
        request.state.trace_id = request.headers.get("X-Trace-ID", uuid4().hex)
        tracer = trace.get_tracer("forgeops.api")
        with tracer.start_as_current_span(f"{request.method} {request.url.path}"):
            response: Response = await call_next(request)
        response.headers["X-Trace-ID"] = request.state.trace_id
        REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
        LOGGER.info(
            "http_request",
            extra={
                "trace_id": request.state.trace_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
            },
        )
        return response

    @app.get("/health/live", tags=["operations"])
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready", tags=["operations"])
    def health_ready() -> JSONResponse:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT version_num FROM alembic_version"))
            return JSONResponse({"status": "ready", "database": "migrated"})
        except SQLAlchemyError:
            return JSONResponse(
                status_code=503,
                content={"status": "not-ready", "database": "unavailable-or-unmigrated"},
            )

    @app.get("/metrics", tags=["operations"])
    def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/v1/platform/status", tags=["platform"])
    def platform_status(_: Annotated[str, Depends(require_local_actor)]) -> dict[str, Any]:
        return {
            "environment": resolved.environment.value,
            "scope": "LOCAL_SYNTHETIC_ENGINEERING",
            "advisoryMode": True,
            "dataMode": "SYNTHETIC_ONLY",
            "externalModelEnabled": False,
            "runtimePluginsEnabled": False,
            "actionAdapter": resolved.action_adapter.value,
            "sdkVersion": resolved.sdk_version,
            "enterpriseApproval": "NOT_GRANTED",
        }

    @app.post("/v1/scenario-packages:validate", tags=["scenario-packages"])
    def validate_package(
        submission: ManifestSubmission,
        _: Annotated[str, Depends(require_local_actor)],
    ) -> dict[str, Any]:
        report = packages.validate(submission.manifest, submission.artifact_payload())
        PACKAGE_OPERATIONS.labels("validate", "valid" if report.valid else "invalid").inc()
        return report.model_dump(mode="json", by_alias=True)

    @app.post("/v1/scenario-package-installations", status_code=201, tags=["scenario-packages"])
    def install_package(
        submission: ManifestSubmission,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        record = packages.install(
            submission.manifest,
            submission.artifact_payload(),
            actor_ref=actor,
            trace_id=_trace_id(request),
        )
        PACKAGE_OPERATIONS.labels("install", "success").inc()
        return record.model_dump(mode="json", by_alias=True)

    @app.get("/v1/scenario-package-installations", tags=["scenario-packages"])
    def list_installations(
        _: Annotated[str, Depends(require_local_actor)],
    ) -> list[dict[str, Any]]:
        return [
            item.model_dump(mode="json", by_alias=True)
            for item in installations.list_installations()
        ]

    def transition(
        operation: str, installation_id: UUID, actor: str, request: Request
    ) -> dict[str, Any]:
        handler = packages.mark_tested if operation == "mark-tested" else packages.approve
        result = handler(installation_id, actor_ref=actor, trace_id=_trace_id(request))
        return result.model_dump(mode="json", by_alias=True)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}:mark-tested",
        tags=["scenario-packages"],
    )
    def mark_tested(
        installation_id: UUID,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        return transition("mark-tested", installation_id, actor, request)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}:approve",
        tags=["scenario-packages"],
    )
    def approve(
        installation_id: UUID,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        return transition("approve", installation_id, actor, request)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}/permission-grants",
        tags=["scenario-packages"],
    )
    def grant_permissions(
        installation_id: UUID,
        body: PermissionGrantRequest,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        result = packages.grant_permissions(
            installation_id,
            body.permissions,
            actor_ref=actor,
            trace_id=_trace_id(request),
        )
        return result.model_dump(mode="json", by_alias=True)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}/bindings",
        tags=["scenario-packages"],
    )
    def bind_package(
        installation_id: UUID,
        body: BindingRequest,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        result = packages.bind(
            installation_id,
            body.binding_ref,
            actor_ref=actor,
            trace_id=_trace_id(request),
        )
        return result.model_dump(mode="json", by_alias=True)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}/releases",
        status_code=201,
        tags=["scenario-packages"],
    )
    def release_package(
        installation_id: UUID,
        body: ReleaseRequest,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        result = packages.release(
            installation_id,
            body.environment,
            body.action_adapter,
            actor_ref=actor,
            trace_id=_trace_id(request),
        )
        return result.model_dump(mode="json", by_alias=True)

    def release_transition(
        operation: str,
        installation_id: UUID,
        environment: Environment,
        actor: str,
        request: Request,
    ) -> dict[str, Any]:
        handlers = {
            "enable": packages.enable,
            "disable": packages.disable,
            "revoke": packages.revoke,
        }
        result = handlers[operation](
            installation_id, environment, actor_ref=actor, trace_id=_trace_id(request)
        )
        return result.model_dump(mode="json", by_alias=True)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}/releases/{environment}:enable",
        tags=["scenario-packages"],
    )
    def enable_release(
        installation_id: UUID,
        environment: Environment,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        return release_transition("enable", installation_id, environment, actor, request)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}/releases/{environment}:disable",
        tags=["scenario-packages"],
    )
    def disable_release(
        installation_id: UUID,
        environment: Environment,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        return release_transition("disable", installation_id, environment, actor, request)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}/releases/{environment}:revoke",
        tags=["scenario-packages"],
    )
    def revoke_release(
        installation_id: UUID,
        environment: Environment,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        return release_transition("revoke", installation_id, environment, actor, request)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}:uninstall",
        tags=["scenario-packages"],
    )
    def uninstall_package(
        installation_id: UUID,
        actor: Annotated[str, Depends(require_local_actor)],
        request: Request,
    ) -> dict[str, Any]:
        result = packages.uninstall(
            installation_id,
            actor_ref=actor,
            trace_id=_trace_id(request),
        )
        return result.model_dump(mode="json", by_alias=True)

    @app.get(
        "/v1/scenario-package-installations/{installation_id}/run-eligibility/{environment}",
        tags=["scenario-packages"],
    )
    def run_eligibility(
        installation_id: UUID,
        environment: Environment,
        _: Annotated[str, Depends(require_local_actor)],
    ) -> dict[str, bool]:
        packages.assert_new_run_allowed(installation_id, environment)
        return {"newRunAllowed": True}

    @app.get("/v1/audit-events", tags=["audit"])
    def list_audit_events(
        _: Annotated[str, Depends(require_local_actor)], limit: int = 100
    ) -> list[dict[str, Any]]:
        return [
            event.model_dump(mode="json", by_alias=True)
            for event in audit.list_events(limit=min(max(limit, 1), 500))
        ]

    return app


def database_engine(app: FastAPI) -> Engine:
    return cast(Engine, app.state.engine)
