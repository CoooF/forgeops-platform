from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from forgeops.platform_adapters.postgres.models import (
    IdempotencyRecordRow,
    MembershipRow,
    OrganizationRow,
    PrincipalRow,
    ProjectPackageBindingRow,
    ProjectRow,
    WorkspaceRow,
)
from forgeops.platform_contracts.errors import ErrorCode, ForgeOpsError
from forgeops.platform_core.identity_access.entities import (
    BindingState,
    Membership,
    MembershipState,
    Organization,
    OrganizationState,
    PackageKind,
    Principal,
    PrincipalKind,
    PrincipalState,
    Project,
    ProjectPackageBinding,
    ProjectState,
    Role,
    ScopeType,
    Workspace,
    WorkspaceState,
)


class SqlIdentityRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def get_principal_by_subject(self, subject_ref: str) -> Principal | None:
        with self._session_factory() as session:
            return self._principal(
                session.scalar(select(PrincipalRow).where(PrincipalRow.subject_ref == subject_ref))
            )

    def get_principal(self, principal_id: UUID) -> Principal | None:
        with self._session_factory() as session:
            return self._principal(session.get(PrincipalRow, principal_id))

    def list_memberships_for_principal(self, principal_id: UUID) -> tuple[Membership, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(MembershipRow)
                .where(MembershipRow.principal_id == principal_id)
                .order_by(MembershipRow.granted_at, MembershipRow.membership_id)
            )
            return tuple(self._membership(row) for row in rows)

    def list_memberships_for_organization(self, organization_id: UUID) -> tuple[Membership, ...]:
        with self._session_factory() as session:
            workspace_ids = select(WorkspaceRow.workspace_id).where(
                WorkspaceRow.organization_id == organization_id
            )
            project_ids = select(ProjectRow.project_id).where(
                ProjectRow.workspace_id.in_(workspace_ids)
            )
            rows = session.scalars(
                select(MembershipRow)
                .where(
                    or_(
                        MembershipRow.organization_id == organization_id,
                        MembershipRow.workspace_id.in_(workspace_ids),
                        MembershipRow.project_id.in_(project_ids),
                    )
                )
                .order_by(MembershipRow.granted_at, MembershipRow.membership_id)
            )
            return tuple(self._membership(row) for row in rows)

    def get_membership(self, membership_id: UUID) -> Membership | None:
        with self._session_factory() as session:
            return self._membership_optional(session.get(MembershipRow, membership_id))

    def add_membership(self, membership: Membership, idempotency_key: str) -> Membership:
        with self._session_factory() as session, session.begin():
            replay = self._find_idempotent(
                session, membership.granted_by, "membership.create", idempotency_key
            )
            if replay:
                existing = session.get(MembershipRow, replay.resource_id)
                if existing is None:
                    raise self._idempotency_corrupt()
                return self._membership(existing)
            session.add(self._membership_row(membership))
            self._add_idempotency(
                session,
                membership.granted_by,
                "membership.create",
                idempotency_key,
                "MEMBERSHIP",
                membership.membership_id,
            )
            self._flush_or_conflict(session)
        return membership

    def save_membership(self, membership: Membership, expected_version: int) -> Membership:
        with self._session_factory() as session, session.begin():
            row = session.scalar(
                select(MembershipRow)
                .where(MembershipRow.membership_id == membership.membership_id)
                .with_for_update()
            )
            if row is None or row.version != expected_version:
                raise self._concurrency_conflict(expected_version)
            if (
                row.scope_type == ScopeType.ORGANIZATION.value
                and row.role == Role.ORG_OWNER.value
                and row.state == MembershipState.ACTIVE.value
                and membership.state != MembershipState.ACTIVE
            ):
                active_owner_ids = tuple(
                    session.scalars(
                        select(MembershipRow.membership_id)
                        .where(
                            MembershipRow.organization_id == row.organization_id,
                            MembershipRow.role == Role.ORG_OWNER.value,
                            MembershipRow.state == MembershipState.ACTIVE.value,
                        )
                        .with_for_update()
                    )
                )
                if len(active_owner_ids) <= 1:
                    raise ForgeOpsError(
                        ErrorCode.LAST_OWNER_REQUIRED,
                        "the final active organization owner cannot be suspended or revoked",
                        http_status=409,
                    )
            row.state = membership.state.value
            row.version = expected_version + 1
            row.updated_at = membership.updated_at
            self._flush_or_conflict(session)
        return membership.model_copy(update={"version": expected_version + 1})

    def count_active_org_owners(self, organization_id: UUID) -> int:
        with self._session_factory() as session:
            return int(
                session.scalar(
                    select(func.count())
                    .select_from(MembershipRow)
                    .where(
                        MembershipRow.organization_id == organization_id,
                        MembershipRow.role == Role.ORG_OWNER.value,
                        MembershipRow.state == MembershipState.ACTIVE.value,
                    )
                )
                or 0
            )

    def list_organizations(self) -> tuple[Organization, ...]:
        with self._session_factory() as session:
            rows = session.scalars(select(OrganizationRow).order_by(OrganizationRow.slug))
            return tuple(self._organization(row) for row in rows)

    def get_organization(self, organization_id: UUID) -> Organization | None:
        with self._session_factory() as session:
            return self._organization_optional(session.get(OrganizationRow, organization_id))

    def add_organization_with_owner(
        self,
        organization: Organization,
        owner: Membership,
        idempotency_key: str,
    ) -> Organization:
        with self._session_factory() as session, session.begin():
            replay = self._find_idempotent(
                session, organization.created_by, "organization.create", idempotency_key
            )
            if replay:
                existing = session.get(OrganizationRow, replay.resource_id)
                if existing is None:
                    raise self._idempotency_corrupt()
                return self._organization(existing)
            session.add(self._organization_row(organization))
            self._flush_or_conflict(session)
            session.add(self._membership_row(owner))
            self._add_idempotency(
                session,
                organization.created_by,
                "organization.create",
                idempotency_key,
                "ORGANIZATION",
                organization.organization_id,
            )
            self._flush_or_conflict(session)
        return organization

    def save_organization(self, organization: Organization, expected_version: int) -> Organization:
        values = self._versioned_values(organization, expected_version)
        values.update(
            {
                "name": organization.name,
                "slug": organization.slug,
                "state": organization.state.value,
            }
        )
        self._optimistic_update(
            OrganizationRow,
            "organization_id",
            organization.organization_id,
            expected_version,
            values,
        )
        return organization.model_copy(update={"version": expected_version + 1})

    def list_workspaces(self, organization_id: UUID) -> tuple[Workspace, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(WorkspaceRow)
                .where(WorkspaceRow.organization_id == organization_id)
                .order_by(WorkspaceRow.slug)
            )
            return tuple(self._workspace(row) for row in rows)

    def get_workspace(self, workspace_id: UUID) -> Workspace | None:
        with self._session_factory() as session:
            return self._workspace_optional(session.get(WorkspaceRow, workspace_id))

    def add_workspace(self, workspace: Workspace, idempotency_key: str) -> Workspace:
        return cast(
            Workspace,
            self._add_versioned(
                workspace,
                self._workspace_row(workspace),
                workspace.created_by,
                "workspace.create",
                idempotency_key,
                "WORKSPACE",
                workspace.workspace_id,
                WorkspaceRow,
                self._workspace,
            ),
        )

    def save_workspace(self, workspace: Workspace, expected_version: int) -> Workspace:
        values = self._versioned_values(workspace, expected_version)
        values.update(
            {"name": workspace.name, "slug": workspace.slug, "state": workspace.state.value}
        )
        self._optimistic_update(
            WorkspaceRow, "workspace_id", workspace.workspace_id, expected_version, values
        )
        return workspace.model_copy(update={"version": expected_version + 1})

    def list_projects(self, workspace_id: UUID) -> tuple[Project, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ProjectRow)
                .where(ProjectRow.workspace_id == workspace_id)
                .order_by(ProjectRow.slug)
            )
            return tuple(self._project(row) for row in rows)

    def get_project(self, project_id: UUID) -> Project | None:
        with self._session_factory() as session:
            return self._project_optional(session.get(ProjectRow, project_id))

    def add_project(self, project: Project, idempotency_key: str) -> Project:
        return cast(
            Project,
            self._add_versioned(
                project,
                self._project_row(project),
                project.created_by,
                "project.create",
                idempotency_key,
                "PROJECT",
                project.project_id,
                ProjectRow,
                self._project,
            ),
        )

    def save_project(self, project: Project, expected_version: int) -> Project:
        values = self._versioned_values(project, expected_version)
        values.update(
            {
                "name": project.name,
                "slug": project.slug,
                "description": project.description,
                "state": project.state.value,
            }
        )
        self._optimistic_update(
            ProjectRow, "project_id", project.project_id, expected_version, values
        )
        return project.model_copy(update={"version": expected_version + 1})

    def get_binding(self, binding_id: UUID) -> ProjectPackageBinding | None:
        with self._session_factory() as session:
            return self._binding_optional(session.get(ProjectPackageBindingRow, binding_id))

    def get_project_installation_binding(
        self, project_id: UUID, installation_id: UUID
    ) -> ProjectPackageBinding | None:
        with self._session_factory() as session:
            return self._binding_optional(
                session.scalar(
                    select(ProjectPackageBindingRow).where(
                        ProjectPackageBindingRow.project_id == project_id,
                        ProjectPackageBindingRow.installation_id == installation_id,
                    )
                )
            )

    def list_project_bindings(self, project_id: UUID) -> tuple[ProjectPackageBinding, ...]:
        with self._session_factory() as session:
            rows = session.scalars(
                select(ProjectPackageBindingRow)
                .where(ProjectPackageBindingRow.project_id == project_id)
                .order_by(ProjectPackageBindingRow.created_at, ProjectPackageBindingRow.binding_id)
            )
            return tuple(self._binding(row) for row in rows)

    def add_project_binding(
        self, binding: ProjectPackageBinding, idempotency_key: str
    ) -> ProjectPackageBinding:
        return cast(
            ProjectPackageBinding,
            self._add_versioned(
                binding,
                self._binding_row(binding),
                binding.created_by,
                "project-package-binding.create",
                idempotency_key,
                "PROJECT_PACKAGE_BINDING",
                binding.binding_id,
                ProjectPackageBindingRow,
                self._binding,
            ),
        )

    def save_project_binding(
        self, binding: ProjectPackageBinding, expected_version: int
    ) -> ProjectPackageBinding:
        values = self._versioned_values(binding, expected_version)
        values.update({"state": binding.state.value})
        self._optimistic_update(
            ProjectPackageBindingRow, "binding_id", binding.binding_id, expected_version, values
        )
        return binding.model_copy(update={"version": expected_version + 1})

    def find_idempotent_resource(
        self, actor_ref: str, operation: str, idempotency_key: str
    ) -> tuple[str, UUID] | None:
        with self._session_factory() as session:
            record = self._find_idempotent(session, actor_ref, operation, idempotency_key)
            return (record.resource_type, record.resource_id) if record else None

    def organization_id_for_scope(self, scope_type: ScopeType, scope_id: UUID) -> UUID | None:
        with self._session_factory() as session:
            if scope_type == ScopeType.ORGANIZATION:
                return scope_id if session.get(OrganizationRow, scope_id) else None
            if scope_type == ScopeType.WORKSPACE:
                workspace_row = session.get(WorkspaceRow, scope_id)
                return workspace_row.organization_id if workspace_row else None
            if scope_type == ScopeType.PROJECT:
                project_row = session.get(ProjectRow, scope_id)
                if project_row is None:
                    return None
                workspace = session.get(WorkspaceRow, project_row.workspace_id)
                return workspace.organization_id if workspace else None
            return None

    def binding_state_for_installation(
        self, project_id: UUID, installation_id: UUID
    ) -> BindingState | None:
        binding = self.get_project_installation_binding(project_id, installation_id)
        return binding.state if binding else None

    def _add_versioned(
        self,
        entity: Any,
        row: Any,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        resource_type: str,
        resource_id: UUID,
        row_type: Any,
        converter: Callable[[Any], Any],
    ) -> Any:
        with self._session_factory() as session, session.begin():
            replay = self._find_idempotent(session, actor_ref, operation, idempotency_key)
            if replay:
                existing = session.get(row_type, replay.resource_id)
                if existing is None:
                    raise self._idempotency_corrupt()
                return converter(existing)
            session.add(row)
            self._add_idempotency(
                session,
                actor_ref,
                operation,
                idempotency_key,
                resource_type,
                resource_id,
            )
            self._flush_or_conflict(session)
        return entity

    def _optimistic_update(
        self,
        row_type: Any,
        identifier_name: str,
        identifier: UUID,
        expected_version: int,
        values: dict[str, object],
    ) -> None:
        with self._session_factory() as session, session.begin():
            identifier_column = getattr(row_type, identifier_name)
            result = session.execute(
                update(row_type)
                .where(
                    identifier_column == identifier,
                    row_type.version == expected_version,
                )
                .values(**values)
            )
            if cast(Any, result).rowcount != 1:
                raise self._concurrency_conflict(expected_version)
            self._flush_or_conflict(session)

    @staticmethod
    def _concurrency_conflict(expected_version: int) -> ForgeOpsError:
        return ForgeOpsError(
            ErrorCode.CONCURRENCY_CONFLICT,
            "resource version does not match expectedVersion",
            details={"expectedVersion": expected_version},
            http_status=409,
        )

    @staticmethod
    def _versioned_values(entity: Any, expected_version: int) -> dict[str, object]:
        return {
            "version": expected_version + 1,
            "updated_at": entity.updated_at,
            "updated_by": entity.updated_by,
        }

    @staticmethod
    def _find_idempotent(
        session: Session, actor_ref: str, operation: str, idempotency_key: str
    ) -> IdempotencyRecordRow | None:
        return session.scalar(
            select(IdempotencyRecordRow).where(
                IdempotencyRecordRow.actor_ref == actor_ref,
                IdempotencyRecordRow.operation == operation,
                IdempotencyRecordRow.idempotency_key == idempotency_key,
            )
        )

    @staticmethod
    def _add_idempotency(
        session: Session,
        actor_ref: str,
        operation: str,
        idempotency_key: str,
        resource_type: str,
        resource_id: UUID,
    ) -> None:
        session.add(
            IdempotencyRecordRow(
                record_id=uuid4(),
                actor_ref=actor_ref,
                operation=operation,
                idempotency_key=idempotency_key,
                resource_type=resource_type,
                resource_id=resource_id,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _flush_or_conflict(session: Session) -> None:
        try:
            session.flush()
        except IntegrityError as exc:
            message = str(exc.orig).lower()
            code = ErrorCode.SLUG_CONFLICT if "slug" in message else ErrorCode.IDEMPOTENCY_CONFLICT
            raise ForgeOpsError(
                code, "resource conflicts with an existing record", http_status=409
            ) from exc

    @staticmethod
    def _idempotency_corrupt() -> ForgeOpsError:
        return ForgeOpsError(
            ErrorCode.INTERNAL_FAILURE,
            "idempotency record refers to a missing resource",
            http_status=500,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _principal(row: PrincipalRow | None) -> Principal | None:
        if row is None:
            return None
        return Principal(
            principal_id=row.principal_id,
            subject_ref=row.subject_ref,
            display_name=row.display_name,
            kind=PrincipalKind(row.kind),
            state=PrincipalState(row.state),
            version=row.version,
            created_at=SqlIdentityRepository._utc(row.created_at),
            updated_at=SqlIdentityRepository._utc(row.updated_at),
            created_by=row.created_by,
            updated_by=row.updated_by,
        )

    @staticmethod
    def _organization(row: OrganizationRow) -> Organization:
        return Organization(
            organization_id=row.organization_id,
            name=row.name,
            slug=row.slug,
            state=OrganizationState(row.state),
            version=row.version,
            created_at=SqlIdentityRepository._utc(row.created_at),
            updated_at=SqlIdentityRepository._utc(row.updated_at),
            created_by=row.created_by,
            updated_by=row.updated_by,
        )

    @classmethod
    def _organization_optional(cls, row: OrganizationRow | None) -> Organization | None:
        return cls._organization(row) if row else None

    @staticmethod
    def _workspace(row: WorkspaceRow) -> Workspace:
        return Workspace(
            workspace_id=row.workspace_id,
            organization_id=row.organization_id,
            name=row.name,
            slug=row.slug,
            state=WorkspaceState(row.state),
            version=row.version,
            created_at=SqlIdentityRepository._utc(row.created_at),
            updated_at=SqlIdentityRepository._utc(row.updated_at),
            created_by=row.created_by,
            updated_by=row.updated_by,
        )

    @classmethod
    def _workspace_optional(cls, row: WorkspaceRow | None) -> Workspace | None:
        return cls._workspace(row) if row else None

    @staticmethod
    def _project(row: ProjectRow) -> Project:
        return Project(
            project_id=row.project_id,
            workspace_id=row.workspace_id,
            name=row.name,
            slug=row.slug,
            description=row.description,
            state=ProjectState(row.state),
            version=row.version,
            created_at=SqlIdentityRepository._utc(row.created_at),
            updated_at=SqlIdentityRepository._utc(row.updated_at),
            created_by=row.created_by,
            updated_by=row.updated_by,
        )

    @classmethod
    def _project_optional(cls, row: ProjectRow | None) -> Project | None:
        return cls._project(row) if row else None

    @staticmethod
    def _membership(row: MembershipRow) -> Membership:
        scope_id = {
            ScopeType.PLATFORM: None,
            ScopeType.ORGANIZATION: row.organization_id,
            ScopeType.WORKSPACE: row.workspace_id,
            ScopeType.PROJECT: row.project_id,
        }[ScopeType(row.scope_type)]
        return Membership(
            membership_id=row.membership_id,
            principal_id=row.principal_id,
            scope_type=ScopeType(row.scope_type),
            scope_id=scope_id,
            role=Role(row.role),
            state=MembershipState(row.state),
            version=row.version,
            granted_by=row.granted_by,
            granted_at=SqlIdentityRepository._utc(row.granted_at),
            updated_at=SqlIdentityRepository._utc(row.updated_at),
        )

    @classmethod
    def _membership_optional(cls, row: MembershipRow | None) -> Membership | None:
        return cls._membership(row) if row else None

    @staticmethod
    def _binding(row: ProjectPackageBindingRow) -> ProjectPackageBinding:
        return ProjectPackageBinding(
            binding_id=row.binding_id,
            project_id=row.project_id,
            installation_id=row.installation_id,
            package_kind=PackageKind(row.package_kind),
            state=BindingState(row.state),
            version=row.version,
            created_at=SqlIdentityRepository._utc(row.created_at),
            updated_at=SqlIdentityRepository._utc(row.updated_at),
            created_by=row.created_by,
            updated_by=row.updated_by,
        )

    @classmethod
    def _binding_optional(
        cls, row: ProjectPackageBindingRow | None
    ) -> ProjectPackageBinding | None:
        return cls._binding(row) if row else None

    @staticmethod
    def _principal_row(principal: Principal) -> PrincipalRow:
        return PrincipalRow(
            principal_id=principal.principal_id,
            subject_ref=principal.subject_ref,
            display_name=principal.display_name,
            kind=principal.kind.value,
            state=principal.state.value,
            version=principal.version,
            created_at=principal.created_at,
            updated_at=principal.updated_at,
            created_by=principal.created_by,
            updated_by=principal.updated_by,
        )

    @staticmethod
    def _organization_row(organization: Organization) -> OrganizationRow:
        return OrganizationRow(
            organization_id=organization.organization_id,
            name=organization.name,
            slug=organization.slug,
            state=organization.state.value,
            version=organization.version,
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            created_by=organization.created_by,
            updated_by=organization.updated_by,
        )

    @staticmethod
    def _workspace_row(workspace: Workspace) -> WorkspaceRow:
        return WorkspaceRow(
            workspace_id=workspace.workspace_id,
            organization_id=workspace.organization_id,
            name=workspace.name,
            slug=workspace.slug,
            state=workspace.state.value,
            version=workspace.version,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            created_by=workspace.created_by,
            updated_by=workspace.updated_by,
        )

    @staticmethod
    def _project_row(project: Project) -> ProjectRow:
        return ProjectRow(
            project_id=project.project_id,
            workspace_id=project.workspace_id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            state=project.state.value,
            version=project.version,
            created_at=project.created_at,
            updated_at=project.updated_at,
            created_by=project.created_by,
            updated_by=project.updated_by,
        )

    @staticmethod
    def _membership_row(membership: Membership) -> MembershipRow:
        return MembershipRow(
            membership_id=membership.membership_id,
            principal_id=membership.principal_id,
            scope_type=membership.scope_type.value,
            organization_id=(
                membership.scope_id if membership.scope_type == ScopeType.ORGANIZATION else None
            ),
            workspace_id=(
                membership.scope_id if membership.scope_type == ScopeType.WORKSPACE else None
            ),
            project_id=(
                membership.scope_id if membership.scope_type == ScopeType.PROJECT else None
            ),
            role=membership.role.value,
            state=membership.state.value,
            version=membership.version,
            granted_by=membership.granted_by,
            granted_at=membership.granted_at,
            updated_at=membership.updated_at,
        )

    @staticmethod
    def _binding_row(binding: ProjectPackageBinding) -> ProjectPackageBindingRow:
        return ProjectPackageBindingRow(
            binding_id=binding.binding_id,
            project_id=binding.project_id,
            installation_id=binding.installation_id,
            package_kind=binding.package_kind.value,
            state=binding.state.value,
            version=binding.version,
            created_at=binding.created_at,
            updated_at=binding.updated_at,
            created_by=binding.created_by,
            updated_by=binding.updated_by,
        )
