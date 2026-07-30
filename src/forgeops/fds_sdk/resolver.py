from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

from forgeops.fds_sdk.canonical import canonical_json, sha256_digest
from forgeops.fds_sdk.models import (
    ComponentManifest,
    DependencyLock,
    DependencyRequirement,
    FdsManifest,
    FdsValidationIssue,
    LockedEdge,
    LockedNode,
    OrganizationOverlayManifest,
    PackageKind,
    PackageRef,
    RequestedResourceBudget,
    ResolutionReport,
    ScenarioDescriptor,
    TargetVersions,
    Visibility,
)
from forgeops.fds_sdk.validation import (
    FdsManifestValidator,
    issue_sort_key,
    manifest_requirements,
    sorted_issues,
)
from forgeops.platform_contracts.errors import ErrorCode


@dataclass(frozen=True)
class _Pending:
    parent_id: str
    requirement: DependencyRequirement

    @property
    def key(self) -> tuple[str, str, str, bool]:
        package = self.requirement.package
        return (
            self.parent_id,
            package.package_id,
            package.version_constraint,
            self.requirement.required,
        )


@dataclass(frozen=True)
class _SearchResult:
    selected: dict[str, FdsManifest] | None
    edges: tuple[LockedEdge, ...] = ()
    skipped: tuple[str, ...] = ()
    issues: tuple[FdsValidationIssue, ...] = ()


class DependencyResolver:
    """Offline, deterministic FDS v0.1 dependency resolver."""

    def resolve(
        self,
        root: PackageRef,
        candidates: Iterable[FdsManifest],
        target_versions: TargetVersions,
        *,
        include_optional: bool = True,
    ) -> ResolutionReport:
        candidate_list, candidate_issues = self._prepare_candidates(candidates)
        if candidate_issues:
            return ResolutionReport(valid=False, issues=candidate_issues)
        root_options, root_issues = self._options(root, candidate_list, target_versions)
        if not root_options:
            return ResolutionReport(valid=False, issues=root_issues)

        failures: list[tuple[FdsValidationIssue, ...]] = []
        for root_manifest in root_options:
            pending = tuple(
                _Pending(root_manifest.package_id, requirement)
                for requirement in manifest_requirements(root_manifest)
            )
            result = self._search(
                {root_manifest.package_id: root_manifest},
                (),
                (),
                pending,
                candidate_list,
                target_versions,
                include_optional,
                root_manifest.package_id,
            )
            if result.selected is not None:
                lock = self._build_lock(
                    root_manifest,
                    result.selected,
                    result.edges,
                    result.skipped,
                    target_versions,
                )
                return ResolutionReport(valid=True, lock=lock)
            failures.append(result.issues)
        issues = min(failures, key=self._issue_tuple_key) if failures else root_issues
        return ResolutionReport(valid=False, issues=issues)

    def _search(
        self,
        selected: dict[str, FdsManifest],
        edges: tuple[LockedEdge, ...],
        skipped: tuple[str, ...],
        pending: tuple[_Pending, ...],
        candidates: tuple[FdsManifest, ...],
        targets: TargetVersions,
        include_optional: bool,
        root_id: str,
    ) -> _SearchResult:
        if not pending:
            issues = self._validate_graph(selected, edges, root_id)
            if issues:
                return _SearchResult(selected=None, issues=issues)
            return _SearchResult(
                selected=selected, edges=edges, skipped=tuple(sorted(set(skipped)))
            )

        current = min(pending, key=lambda item: item.key)
        remainder_list = list(pending)
        remainder_list.remove(current)
        remainder = tuple(remainder_list)
        requirement = current.requirement
        dependency_id = requirement.package.package_id
        if not requirement.required and not include_optional:
            return self._search(
                selected,
                edges,
                (*skipped, dependency_id),
                remainder,
                candidates,
                targets,
                include_optional,
                root_id,
            )

        existing = selected.get(dependency_id)
        if existing is not None:
            match_issues = self._candidate_match_issues(existing, requirement, targets)
            if match_issues:
                return _SearchResult(selected=None, issues=match_issues)
            edge = self._edge(current)
            return self._search(
                selected,
                (*edges, edge),
                skipped,
                remainder,
                candidates,
                targets,
                include_optional,
                root_id,
            )

        options, option_issues = self._options(
            requirement.package, candidates, targets, requirement
        )
        if not options:
            if not requirement.required:
                return self._search(
                    selected,
                    edges,
                    (*skipped, dependency_id),
                    remainder,
                    candidates,
                    targets,
                    include_optional,
                    root_id,
                )
            return _SearchResult(selected=None, issues=option_issues)

        failures: list[tuple[FdsValidationIssue, ...]] = []
        for option in options:
            next_selected = {**selected, dependency_id: option}
            next_pending = (
                *remainder,
                *(_Pending(option.package_id, child) for child in manifest_requirements(option)),
            )
            result = self._search(
                next_selected,
                (*edges, self._edge(current)),
                skipped,
                next_pending,
                candidates,
                targets,
                include_optional,
                root_id,
            )
            if result.selected is not None:
                return result
            failures.append(result.issues)
        return _SearchResult(selected=None, issues=min(failures, key=self._issue_tuple_key))

    @staticmethod
    def _edge(pending: _Pending) -> LockedEdge:
        return LockedEdge(
            from_package_id=pending.parent_id,
            to_package_id=pending.requirement.package.package_id,
            version_constraint=pending.requirement.package.version_constraint,
            required=pending.requirement.required,
        )

    def _prepare_candidates(
        self, candidates: Iterable[FdsManifest]
    ) -> tuple[tuple[FdsManifest, ...], tuple[FdsValidationIssue, ...]]:
        unique: dict[str, FdsManifest] = {}
        groups: dict[tuple[str, str], list[FdsManifest]] = {}
        issues: list[FdsValidationIssue] = []
        validator = FdsManifestValidator()
        for candidate in candidates:
            model_issues = validator.validate_model(candidate)
            issues.extend(model_issues)
            serialized = canonical_json(candidate)
            unique[serialized] = candidate
        for candidate in unique.values():
            groups.setdefault((candidate.package_id, candidate.package_version), []).append(
                candidate
            )
        for (package_id, package_version), group in sorted(groups.items()):
            if len(group) <= 1:
                continue
            digests = {item.content_digest for item in group}
            if len(digests) > 1:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.PACKAGE_VERSION_DIGEST_CONFLICT,
                        message=f"{package_id}@{package_version} has multiple content digests",
                        path=f"$.candidates[{package_id}@{package_version}]",
                    )
                )
            else:
                issues.append(
                    FdsValidationIssue(
                        code=ErrorCode.DEPENDENCY_AMBIGUOUS,
                        message=f"{package_id}@{package_version} has multiple distinct manifests",
                        path=f"$.candidates[{package_id}@{package_version}]",
                    )
                )
        ordered = tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    item.package_id,
                    Version(item.package_version),
                    canonical_json(item),
                ),
            )
        )
        return ordered, sorted_issues(issues)

    def _options(
        self,
        reference: PackageRef,
        candidates: tuple[FdsManifest, ...],
        targets: TargetVersions,
        requirement: DependencyRequirement | None = None,
    ) -> tuple[tuple[FdsManifest, ...], tuple[FdsValidationIssue, ...]]:
        matching_id = [item for item in candidates if item.package_id == reference.package_id]
        path = f"$.dependencies[{reference.package_id}]"
        if not matching_id:
            return (), (
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_MISSING,
                    message=f"required package is absent: {reference.package_id}",
                    path=path,
                ),
            )
        try:
            specifier = SpecifierSet(reference.version_constraint)
        except InvalidSpecifier:
            return (), (
                FdsValidationIssue(
                    code=ErrorCode.MANIFEST_INVALID,
                    message=f"invalid version constraint: {reference.version_constraint!r}",
                    path=f"{path}.versionConstraint",
                ),
            )
        matching_version = [
            item for item in matching_id if Version(item.package_version) in specifier
        ]
        if not matching_version:
            return (), (
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_VERSION_UNSATISFIED,
                    message=(
                        f"no {reference.package_id} version satisfies "
                        f"{reference.version_constraint}"
                    ),
                    path=f"{path}.versionConstraint",
                ),
            )
        matching_kind = [
            item
            for item in matching_version
            if reference.expected_kind is None or item.kind == reference.expected_kind
        ]
        if not matching_kind:
            return (), (
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_KIND_MISMATCH,
                    message=f"{reference.package_id} does not match expected package kind",
                    path=f"{path}.expectedKind",
                ),
            )
        matching_component = [
            item
            for item in matching_kind
            if requirement is None
            or requirement.expected_component_kind is None
            or (
                isinstance(item, ComponentManifest)
                and item.component_kind == requirement.expected_component_kind
            )
        ]
        if not matching_component:
            return (), (
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_KIND_MISMATCH,
                    message=f"{reference.package_id} does not match expected component kind",
                    path=f"{path}.expectedComponentKind",
                ),
            )
        matching_capability = [
            item
            for item in matching_component
            if reference.expected_capability is None
            or reference.expected_capability in item.provided_capabilities
        ]
        if not matching_capability:
            return (), (
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_CAPABILITY_MISSING,
                    message=f"{reference.package_id} does not provide expected capability",
                    path=f"{path}.expectedCapability",
                ),
            )
        matching_digest = [
            item
            for item in matching_capability
            if reference.content_digest is None or item.content_digest == reference.content_digest
        ]
        if not matching_digest:
            return (), (
                FdsValidationIssue(
                    code=ErrorCode.ARTIFACT_DIGEST_MISMATCH,
                    message=f"{reference.package_id} does not match the requested digest",
                    path=f"{path}.contentDigest",
                ),
            )
        compatible: list[FdsManifest] = []
        compatibility_issues: list[FdsValidationIssue] = []
        for item in matching_digest:
            item_issues = self._compatibility_issues(item, targets)
            if item_issues:
                compatibility_issues.extend(item_issues)
            else:
                compatible.append(item)
        if not compatible:
            return (), sorted_issues(compatibility_issues)
        compatible.sort(
            key=lambda item: (Version(item.package_version), canonical_json(item)), reverse=True
        )
        return tuple(compatible), ()

    @staticmethod
    def _candidate_match_issues(
        candidate: FdsManifest,
        requirement: DependencyRequirement,
        targets: TargetVersions,
    ) -> tuple[FdsValidationIssue, ...]:
        reference = requirement.package
        path = f"$.dependencies[{reference.package_id}]"
        try:
            version_matches = Version(candidate.package_version) in SpecifierSet(
                reference.version_constraint
            )
        except InvalidSpecifier:
            version_matches = False
        issues: list[FdsValidationIssue] = []
        if not version_matches:
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_VERSION_UNSATISFIED,
                    message=f"selected {candidate.package_version} violates a later constraint",
                    path=f"{path}.versionConstraint",
                )
            )
        if reference.expected_kind is not None and candidate.kind != reference.expected_kind:
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_KIND_MISMATCH,
                    message="selected package kind violates dependency expectation",
                    path=f"{path}.expectedKind",
                )
            )
        if requirement.expected_component_kind is not None and (
            not isinstance(candidate, ComponentManifest)
            or candidate.component_kind != requirement.expected_component_kind
        ):
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_KIND_MISMATCH,
                    message="selected component kind violates dependency expectation",
                    path=f"{path}.expectedComponentKind",
                )
            )
        if (
            reference.expected_capability is not None
            and reference.expected_capability not in candidate.provided_capabilities
        ):
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_CAPABILITY_MISSING,
                    message="selected package lacks the expected capability",
                    path=f"{path}.expectedCapability",
                )
            )
        if (
            reference.content_digest is not None
            and candidate.content_digest != reference.content_digest
        ):
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.ARTIFACT_DIGEST_MISMATCH,
                    message="selected package violates the requested digest",
                    path=f"{path}.contentDigest",
                )
            )
        issues.extend(DependencyResolver._compatibility_issues(candidate, targets))
        return sorted_issues(issues)

    @staticmethod
    def _compatibility_issues(
        manifest: FdsManifest, targets: TargetVersions
    ) -> list[FdsValidationIssue]:
        checks = (
            (
                manifest.compatibility.platform,
                targets.platform,
                ErrorCode.PLATFORM_INCOMPATIBLE,
                "platform",
            ),
            (manifest.compatibility.fds, targets.fds, ErrorCode.FDS_INCOMPATIBLE, "fds"),
            (
                manifest.compatibility.scenario_sdk,
                targets.scenario_sdk,
                ErrorCode.SDK_INCOMPATIBLE,
                "scenarioSdk",
            ),
        )
        issues: list[FdsValidationIssue] = []
        for constraint, target, code, field in checks:
            try:
                compatible = Version(target) in SpecifierSet(constraint)
            except InvalidSpecifier:
                compatible = False
            if not compatible:
                issues.append(
                    FdsValidationIssue(
                        code=code,
                        message=(
                            f"{manifest.package_id}@{manifest.package_version} constraint "
                            f"{constraint!r} excludes {target}"
                        ),
                        path=f"$.candidates[{manifest.package_id}].compatibility.{field}",
                    )
                )
        return issues

    def _validate_graph(
        self,
        selected: dict[str, FdsManifest],
        edges: tuple[LockedEdge, ...],
        root_id: str,
    ) -> tuple[FdsValidationIssue, ...]:
        issues: list[FdsValidationIssue] = []
        adjacency: dict[str, set[str]] = {package_id: set() for package_id in selected}
        for edge in edges:
            adjacency[edge.from_package_id].add(edge.to_package_id)
            parent = selected[edge.from_package_id]
            child = selected[edge.to_package_id]
            issues.extend(self._layer_issues(parent, child, edge))
        cycle = self._find_cycle(adjacency)
        if cycle:
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_CYCLE,
                    message=f"dependency cycle: {' -> '.join(cycle)}",
                    path="$.dependencies",
                )
            )
        issues.extend(self._transitive_visibility_issues(selected, adjacency))
        issues.extend(self._conflict_issues(selected))
        issues.extend(self._provider_issues(selected))
        issues.extend(self._capability_requirement_issues(selected))
        issues.extend(self._permission_budget_issues(selected, root_id))
        return sorted_issues(issues)

    @staticmethod
    def _layer_issues(
        parent: FdsManifest, child: FdsManifest, edge: LockedEdge
    ) -> list[FdsValidationIssue]:
        allowed: dict[PackageKind, frozenset[PackageKind]] = {
            PackageKind.DOMAIN: frozenset({PackageKind.DOMAIN, PackageKind.COMPONENT}),
            PackageKind.ORGANIZATION_OVERLAY: frozenset(
                {PackageKind.DOMAIN, PackageKind.COMPONENT}
            ),
            PackageKind.SCENARIO: frozenset(
                {PackageKind.DOMAIN, PackageKind.ORGANIZATION_OVERLAY, PackageKind.COMPONENT}
            ),
            PackageKind.COMPONENT: frozenset({PackageKind.DOMAIN, PackageKind.COMPONENT}),
        }
        issues: list[FdsValidationIssue] = []
        if child.kind not in allowed[parent.kind]:
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.DEPENDENCY_LAYER_VIOLATION,
                    message=f"{parent.kind.value} cannot depend on {child.kind.value}",
                    path=f"$.edges[{edge.from_package_id}->{edge.to_package_id}]",
                )
            )
        if (
            parent.kind == PackageKind.DOMAIN
            and parent.visibility == Visibility.PUBLIC
            and child.visibility in {Visibility.ORGANIZATION_PRIVATE, Visibility.PRIVATE}
        ):
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.VISIBILITY_VIOLATION,
                    message="public Domain cannot depend on private content",
                    path=f"$.edges[{edge.from_package_id}->{edge.to_package_id}]",
                )
            )
        return issues

    @staticmethod
    def _transitive_visibility_issues(
        selected: dict[str, FdsManifest], adjacency: dict[str, set[str]]
    ) -> list[FdsValidationIssue]:
        issues: list[FdsValidationIssue] = []
        for domain in sorted(selected.values(), key=lambda item: item.package_id):
            if domain.kind != PackageKind.DOMAIN or domain.visibility != Visibility.PUBLIC:
                continue
            pending = list(sorted(adjacency[domain.package_id]))
            visited: set[str] = set()
            while pending:
                dependency_id = pending.pop(0)
                if dependency_id in visited:
                    continue
                visited.add(dependency_id)
                dependency = selected[dependency_id]
                if dependency.visibility in {
                    Visibility.ORGANIZATION_PRIVATE,
                    Visibility.PRIVATE,
                }:
                    issues.append(
                        FdsValidationIssue(
                            code=ErrorCode.VISIBILITY_VIOLATION,
                            message=(
                                f"public Domain {domain.package_id} transitively depends on "
                                f"private package {dependency_id}"
                            ),
                            path=f"$.candidates[{domain.package_id}].dependencies",
                        )
                    )
                pending.extend(sorted(adjacency[dependency_id] - visited))
        return issues

    @staticmethod
    def _find_cycle(adjacency: dict[str, set[str]]) -> tuple[str, ...]:
        visited: set[str] = set()
        active: list[str] = []

        def visit(node: str) -> tuple[str, ...]:
            if node in active:
                index = active.index(node)
                return (*active[index:], node)
            if node in visited:
                return ()
            active.append(node)
            for child in sorted(adjacency[node]):
                cycle = visit(child)
                if cycle:
                    return cycle
            active.pop()
            visited.add(node)
            return ()

        for node in sorted(adjacency):
            cycle = visit(node)
            if cycle:
                return cycle
        return ()

    @staticmethod
    def _conflict_issues(selected: dict[str, FdsManifest]) -> list[FdsValidationIssue]:
        issues: list[FdsValidationIssue] = []
        capabilities = {
            capability: manifest.package_id
            for manifest in selected.values()
            for capability in manifest.provided_capabilities
        }
        for manifest in sorted(selected.values(), key=lambda item: item.package_id):
            for conflict in manifest.conflicts:
                hit = False
                target = conflict.package_id or conflict.capability or "unknown"
                if conflict.package_id in selected:
                    hit = conflict.version_constraint is None or Version(
                        selected[conflict.package_id].package_version
                    ) in SpecifierSet(conflict.version_constraint)
                if conflict.capability in capabilities:
                    hit = True
                if hit:
                    issues.append(
                        FdsValidationIssue(
                            code=ErrorCode.DEPENDENCY_CONFLICT,
                            message=f"{manifest.package_id} conflict matched {target}",
                            path=f"$.candidates[{manifest.package_id}].conflicts",
                        )
                    )
        return issues

    @staticmethod
    def _provider_issues(selected: dict[str, FdsManifest]) -> list[FdsValidationIssue]:
        issues: list[FdsValidationIssue] = []
        for attribute, code in (
            ("provided_capabilities", ErrorCode.CAPABILITY_CONFLICT),
            ("provided_namespaces", ErrorCode.NAMESPACE_CONFLICT),
        ):
            owners: dict[str, list[str]] = {}
            for manifest in selected.values():
                for value in getattr(manifest, attribute):
                    owners.setdefault(value, []).append(manifest.package_id)
            for value, package_ids in sorted(owners.items()):
                if len(package_ids) > 1:
                    issues.append(
                        FdsValidationIssue(
                            code=code,
                            message=f"{value} is provided by {sorted(package_ids)}",
                            path=f"$.providers[{value}]",
                        )
                    )
        return issues

    @staticmethod
    def _capability_requirement_issues(
        selected: dict[str, FdsManifest],
    ) -> list[FdsValidationIssue]:
        domain_capabilities = {
            capability
            for manifest in selected.values()
            if manifest.kind == PackageKind.DOMAIN
            for capability in manifest.provided_capabilities
        }
        issues: list[FdsValidationIssue] = []
        for manifest in selected.values():
            if isinstance(manifest, ScenarioDescriptor):
                for capability in sorted(
                    set(manifest.required_domain_capabilities) - domain_capabilities
                ):
                    issues.append(
                        FdsValidationIssue(
                            code=ErrorCode.SCENARIO_DOMAIN_CAPABILITY_MISSING,
                            message=(
                                f"scenario requires unavailable domain capability: {capability}"
                            ),
                            path=f"$.candidates[{manifest.package_id}].requiredDomainCapabilities",
                        )
                    )
            if isinstance(manifest, OrganizationOverlayManifest):
                for capability in sorted(
                    set(manifest.overrides_domain_capabilities) - domain_capabilities
                ):
                    issues.append(
                        FdsValidationIssue(
                            code=ErrorCode.OVERLAY_TARGET_MISSING,
                            message=f"overlay target capability is unavailable: {capability}",
                            path=f"$.candidates[{manifest.package_id}].overridesDomainCapabilities",
                        )
                    )
        return issues

    @staticmethod
    def _permission_budget_issues(
        selected: dict[str, FdsManifest], root_id: str
    ) -> list[FdsValidationIssue]:
        root = selected[root_id]
        dependencies = [item for key, item in selected.items() if key != root_id]
        dependency_permissions = {
            permission for manifest in dependencies for permission in manifest.permissions
        }
        accepted = set(root.permissions) | set(root.accepted_dependency_permissions)
        unaccepted = sorted(dependency_permissions - accepted)
        issues = [
            FdsValidationIssue(
                code=ErrorCode.PERMISSION_EXPANSION,
                message=f"transitive permission was not declared or accepted by root: {permission}",
                path="$.permissionDelta",
            )
            for permission in unaccepted
        ]
        delta = DependencyResolver._aggregate_budget(dependencies)
        allowance = root.dependency_resource_budget_allowance
        expanded_fields = []
        for field in ("cpu_millis", "memory_mib", "timeout_seconds", "max_output_bytes"):
            if getattr(delta, field) > getattr(allowance, field):
                expanded_fields.append(field)
        if delta.network_access and not allowance.network_access:
            expanded_fields.append("network_access")
        if not set(delta.secret_refs).issubset(allowance.secret_refs):
            expanded_fields.append("secret_refs")
        issues.extend(
            FdsValidationIssue(
                code=ErrorCode.RESOURCE_BUDGET_EXPANSION,
                message=f"transitive resource budget exceeds root allowance: {field}",
                path=f"$.resourceBudgetDelta.{field}",
            )
            for field in sorted(expanded_fields)
        )
        return issues

    def _build_lock(
        self,
        root: FdsManifest,
        selected: dict[str, FdsManifest],
        edges: tuple[LockedEdge, ...],
        skipped: tuple[str, ...],
        targets: TargetVersions,
    ) -> DependencyLock:
        topological_ids = self._topological_order(selected, edges, root.package_id)
        node_items: list[LockedNode] = []
        for package_id in topological_ids:
            manifest = selected[package_id]
            component_kind = (
                manifest.component_kind if isinstance(manifest, ComponentManifest) else None
            )
            node_items.append(
                LockedNode(
                    package_id=manifest.package_id,
                    package_version=manifest.package_version,
                    kind=manifest.kind,
                    component_kind=component_kind,
                    source_ref=manifest.provenance.source_ref,
                    publisher=manifest.publisher,
                    content_digest=manifest.content_digest,
                )
            )
        nodes = tuple(node_items)
        unique_edges = {canonical_json(edge): edge for edge in edges}
        ordered_edges = tuple(unique_edges[key] for key in sorted(unique_edges))
        all_manifests = list(selected.values())
        dependencies = [item for item in all_manifests if item.package_id != root.package_id]
        requested_permissions = tuple(
            sorted({permission for item in all_manifests for permission in item.permissions})
        )
        dependency_permissions = {
            permission for item in dependencies for permission in item.permissions
        }
        permission_delta = tuple(sorted(dependency_permissions - set(root.permissions)))
        payload = {
            "lockVersion": "forgeops.ai/fds-lock/v1alpha1",
            "rootPackageId": root.package_id,
            "rootPackageVersion": root.package_version,
            "targetVersions": targets,
            "nodes": nodes,
            "edges": ordered_edges,
            "skippedOptionalDependencies": tuple(sorted(set(skipped))),
            "requestedPermissions": requested_permissions,
            "permissionDelta": permission_delta,
            "acceptedDependencyPermissions": tuple(sorted(root.accepted_dependency_permissions)),
            "resourceBudget": self._aggregate_budget(all_manifests),
            "resourceBudgetDelta": self._aggregate_budget(dependencies),
            "authorizationEffect": "NONE",
            "runtimeStateCreated": False,
        }
        return DependencyLock(**payload, lock_digest=sha256_digest(payload))

    @staticmethod
    def _aggregate_budget(manifests: Iterable[FdsManifest]) -> RequestedResourceBudget:
        items = list(manifests)
        return RequestedResourceBudget(
            cpu_millis=sum(item.resource_budget.cpu_millis for item in items),
            memory_mib=sum(item.resource_budget.memory_mib for item in items),
            timeout_seconds=max(
                (item.resource_budget.timeout_seconds for item in items), default=0
            ),
            max_output_bytes=sum(item.resource_budget.max_output_bytes for item in items),
            network_access=any(item.resource_budget.network_access for item in items),
            secret_refs=tuple(
                sorted({secret for item in items for secret in item.resource_budget.secret_refs})
            ),
        )

    @staticmethod
    def _topological_order(
        selected: dict[str, FdsManifest], edges: tuple[LockedEdge, ...], root_id: str
    ) -> tuple[str, ...]:
        adjacency: dict[str, set[str]] = {package_id: set() for package_id in selected}
        for edge in edges:
            adjacency[edge.from_package_id].add(edge.to_package_id)
        ordered: list[str] = []
        visited: set[str] = set()

        def visit(package_id: str) -> None:
            if package_id in visited:
                return
            visited.add(package_id)
            for dependency_id in sorted(adjacency[package_id]):
                visit(dependency_id)
            ordered.append(package_id)

        visit(root_id)
        for package_id in sorted(selected):
            visit(package_id)
        return tuple(ordered)

    @staticmethod
    def _issue_tuple_key(
        issues: tuple[FdsValidationIssue, ...],
    ) -> tuple[tuple[str, str, str], ...]:
        return tuple(issue_sort_key(issue) for issue in issues)


def verify_dependency_lock(
    lock: DependencyLock, candidates: Iterable[FdsManifest] = ()
) -> tuple[FdsValidationIssue, ...]:
    payload = lock.model_dump(by_alias=True, mode="json")
    declared_digest = payload.pop("lockDigest")
    issues: list[FdsValidationIssue] = []
    if sha256_digest(payload) != declared_digest:
        issues.append(
            FdsValidationIssue(
                code=ErrorCode.LOCK_DIGEST_MISMATCH,
                message="DependencyLock digest does not match canonical lock content",
                path="$.lockDigest",
            )
        )
    candidate_index = {(item.package_id, item.package_version): item for item in candidates}
    for index, node in enumerate(lock.nodes):
        candidate = candidate_index.get((node.package_id, node.package_version))
        if candidate is None:
            continue
        if (
            candidate.content_digest != node.content_digest
            or candidate.kind != node.kind
            or candidate.provenance.source_ref != node.source_ref
        ):
            issues.append(
                FdsValidationIssue(
                    code=ErrorCode.LOCK_CONTENT_MISMATCH,
                    message=f"locked node does not match candidate: {node.package_id}",
                    path=f"$.nodes[{index}]",
                )
            )
    return sorted_issues(issues)
