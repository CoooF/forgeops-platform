# ADR-0005: local identity and project authorization boundary

- Status: `ACCEPTED_FOR_LOCAL_SYNTHETIC_ENGINEERING`
- Enterprise identity and policy status: `PROPOSED / BLOCKED`
- Maps to: production ADR-0006/0014/0016

ForgeOps separates authentication from authorization. `LocalSyntheticAuthAdapter` may resolve a controlled `X-ForgeOps-Actor` subject reference only in DEV/TEST, but the header grants no permission. INT/PREPROD/PROD use a fail-closed unavailable adapter until an approved enterprise identity adapter exists. A persisted active Principal and an applicable active Membership are required for every protected request. Enterprise OIDC, credentials, invitations and production login remain absent.

The stable hierarchy is Organization → Workspace → Project. Organization grants explicitly apply to descendant workspaces/projects; Workspace grants apply only to that workspace and its projects; Project grants are direct; grants never cross organizations. Authorization is centralized, default-deny, scope-aware and versioned as `identity-access-v1`. Cross-scope resource discovery uses a uniform not-found response.

Organizations, workspaces, projects, memberships and project-package bindings use archive/suspend/revoke/disable state instead of physical deletion. The final active Organization Owner cannot be revoked. New package bindings reference a real Project ID and do not imply environment release, enablement or data access. Historical legacy `binding_ref` rows remain readable, but callers may not create a new `project://` binding through the legacy string API.

SQLite remains a direct local verification adapter; PostgreSQL remains the target. PREPROD/PROD still use `DenyAllActionAdapter`, and this decision adds no external-write path.
