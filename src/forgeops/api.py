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
from forgeops.domain_registry_api import register_domain_registry_routes
from forgeops.identity_api import register_identity_routes
from forgeops.observability import configure_observability
from forgeops.platform_adapters.object_storage import ContentAddressedFileStore
from forgeops.platform_adapters.postgres.database import create_engine_and_session
from forgeops.platform_adapters.postgres.domain_registry_repository import (
    SqlDomainRegistryRepository,
)
from forgeops.platform_adapters.postgres.identity_repository import SqlIdentityRepository
from forgeops.platform_adapters.postgres.repositories import (
    SqlAuditRepository,
    SqlInstallationRepository,
)
from forgeops.platform_adapters.postgres.semantic_knowledge_repository import (
    SqlSemanticKnowledgeRepository,
)
from forgeops.platform_contracts.domain import Environment
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.domain_registry.service import DomainRegistryService
from forgeops.platform_core.identity_access.auth import auth_adapter_for_environment
from forgeops.platform_core.identity_access.policy import Permission
from forgeops.platform_core.identity_access.service import ActorContext, IdentityAccessService
from forgeops.platform_core.knowledge_hub.service import KnowledgeHubService
from forgeops.platform_core.scenario_registry.service import ScenarioPackageService
from forgeops.platform_core.semantic_runtime.service import SemanticRuntimeService
from forgeops.semantic_knowledge_api import register_semantic_knowledge_routes

LOGGER = logging.getLogger("forgeops.api")
REQUESTS = Counter("forgeops_http_requests_total", "HTTP requests", ("method", "path", "status"))
PACKAGE_OPERATIONS = Counter(
    "forgeops_package_operations_total", "Package operations", ("operation", "result")
)
AUTHORIZATION_DECISIONS = Counter(
    "forgeops_authorization_decisions_total",
    "Authentication and authorization decisions",
    ("action", "result"),
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


def require_current_actor(
    request: Request,
    x_forgeops_actor: Annotated[str | None, Header()] = None,
) -> ActorContext:
    identity = cast(IdentityAccessService, request.app.state.identity)
    return identity.authenticate(x_forgeops_actor, _trace_id(request))


def _trace_id(request: Request) -> str:
    return str(request.state.trace_id)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    configure_observability(resolved.service_name, resolved.log_level)
    engine, session_factory = create_engine_and_session(resolved.database_url)
    installations = SqlInstallationRepository(session_factory)
    audit = SqlAuditRepository(session_factory)
    packages = ScenarioPackageService(installations, audit)
    identity_repository = SqlIdentityRepository(session_factory)
    identity = IdentityAccessService(
        identity_repository,
        installations,
        packages,
        audit,
        auth_adapter_for_environment(resolved.environment),
        resolved.environment,
        lambda action, result: AUTHORIZATION_DECISIONS.labels(action, result).inc(),
    )
    domain_repository = SqlDomainRegistryRepository(session_factory)
    domain_registry = DomainRegistryService(domain_repository, identity_repository, audit)
    semantic_knowledge_repository = SqlSemanticKnowledgeRepository(session_factory)
    object_store = ContentAddressedFileStore(resolved.object_store_path)
    knowledge_hub = KnowledgeHubService(
        semantic_knowledge_repository,
        domain_repository,
        identity_repository,
        audit,
        object_store,
    )
    semantic_runtime = SemanticRuntimeService(
        semantic_knowledge_repository,
        semantic_knowledge_repository,
        domain_repository,
        domain_registry,
        identity_repository,
        audit,
        knowledge_hub,
    )

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
        version="0.2.6c",
        description="Local synthetic EPIC-01/02.6C semantic engineering; advisory-only",
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.engine = engine
    app.state.installations = installations
    app.state.audit = audit
    app.state.packages = packages
    app.state.identity = identity
    app.state.domain_registry = domain_registry
    app.state.knowledge_hub = knowledge_hub
    app.state.semantic_runtime = semantic_runtime
    register_identity_routes(app, identity)
    register_domain_registry_routes(app, domain_registry)
    register_semantic_knowledge_routes(app, semantic_runtime, knowledge_hub)

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
        route = request.scope.get("route")
        route_template = str(getattr(route, "path", "unmatched"))
        REQUESTS.labels(request.method, route_template, str(response.status_code)).inc()
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
    def platform_status(
        _: Annotated[ActorContext, Depends(require_current_actor)],
    ) -> dict[str, Any]:
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
            "identityMode": "LOCAL_SYNTHETIC",
            "enterpriseIdentityConnected": False,
            "projectScopeEnabled": True,
            "fdsRegistryEnabled": True,
            "organizationDomainInstallationEnabled": True,
            "projectDomainLockEnabled": True,
            "semanticRuntimeEnabled": True,
            "knowledgeHubEnabled": True,
            "contextCompilerEnabled": True,
            "groundingValidationEnabled": True,
            "agentRuntimeEnabled": False,
            "llmEnabled": False,
            "ragEnabled": False,
            "workflowRuntimeEnabled": False,
        }

    @app.post("/v1/scenario-packages:validate", tags=["scenario-packages"])
    def validate_package(
        submission: ManifestSubmission,
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        report = packages.validate(submission.manifest, submission.artifact_payload())
        PACKAGE_OPERATIONS.labels("validate", "valid" if report.valid else "invalid").inc()
        return report.model_dump(mode="json", by_alias=True)

    @app.post("/v1/scenario-package-installations", status_code=201, tags=["scenario-packages"])
    def install_package(
        submission: ManifestSubmission,
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        record = packages.install(
            submission.manifest,
            submission.artifact_payload(),
            actor_ref=actor.principal.subject_ref,
            trace_id=_trace_id(request),
        )
        PACKAGE_OPERATIONS.labels("install", "success").inc()
        return record.model_dump(mode="json", by_alias=True)

    @app.get("/v1/scenario-package-installations", tags=["scenario-packages"])
    def list_installations(
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> list[dict[str, Any]]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_VIEW, _trace_id(request))
        return [
            item.model_dump(mode="json", by_alias=True)
            for item in installations.list_installations()
        ]

    def transition(
        operation: str, installation_id: UUID, actor: ActorContext, request: Request
    ) -> dict[str, Any]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        handler = packages.mark_tested if operation == "mark-tested" else packages.approve
        result = handler(
            installation_id,
            actor_ref=actor.principal.subject_ref,
            trace_id=_trace_id(request),
        )
        return result.model_dump(mode="json", by_alias=True)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}:mark-tested",
        tags=["scenario-packages"],
    )
    def mark_tested(
        installation_id: UUID,
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        return transition("mark-tested", installation_id, actor, request)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}:approve",
        tags=["scenario-packages"],
    )
    def approve(
        installation_id: UUID,
        actor: Annotated[ActorContext, Depends(require_current_actor)],
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
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        result = packages.grant_permissions(
            installation_id,
            body.permissions,
            actor_ref=actor.principal.subject_ref,
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
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        result = packages.bind(
            installation_id,
            body.binding_ref,
            actor_ref=actor.principal.subject_ref,
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
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        result = packages.release(
            installation_id,
            body.environment,
            body.action_adapter,
            actor_ref=actor.principal.subject_ref,
            trace_id=_trace_id(request),
        )
        return result.model_dump(mode="json", by_alias=True)

    def release_transition(
        operation: str,
        installation_id: UUID,
        environment: Environment,
        actor: ActorContext,
        request: Request,
    ) -> dict[str, Any]:
        handlers = {
            "enable": packages.enable,
            "disable": packages.disable,
            "revoke": packages.revoke,
        }
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        result = handlers[operation](
            installation_id,
            environment,
            actor_ref=actor.principal.subject_ref,
            trace_id=_trace_id(request),
        )
        return result.model_dump(mode="json", by_alias=True)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}/releases/{environment}:enable",
        tags=["scenario-packages"],
    )
    def enable_release(
        installation_id: UUID,
        environment: Environment,
        actor: Annotated[ActorContext, Depends(require_current_actor)],
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
        actor: Annotated[ActorContext, Depends(require_current_actor)],
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
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        return release_transition("revoke", installation_id, environment, actor, request)

    @app.post(
        "/v1/scenario-package-installations/{installation_id}:uninstall",
        tags=["scenario-packages"],
    )
    def uninstall_package(
        installation_id: UUID,
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, Any]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_MANAGE, _trace_id(request))
        result = packages.uninstall(
            installation_id,
            actor_ref=actor.principal.subject_ref,
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
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
    ) -> dict[str, bool]:
        identity.authorize_platform(actor, Permission.PACKAGE_REGISTRY_VIEW, _trace_id(request))
        packages.assert_new_run_allowed(installation_id, environment)
        return {"newRunAllowed": True}

    @app.get("/v1/audit-events", tags=["audit"])
    def list_audit_events(
        actor: Annotated[ActorContext, Depends(require_current_actor)],
        request: Request,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        identity.authorize_platform(actor, Permission.AUDIT_READ, _trace_id(request))
        return [
            event.model_dump(mode="json", by_alias=True)
            for event in audit.list_events(limit=min(max(limit, 1), 500))
        ]

    return app


def database_engine(app: FastAPI) -> Engine:
    return cast(Engine, app.state.engine)
