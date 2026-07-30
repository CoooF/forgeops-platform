# ADR-0003: fail-closed package trust and lifecycle

- Status: `ACCEPTED_FOR_LOCAL_SYNTHETIC_ENGINEERING`
- Enterprise signing/root of trust: `PROPOSED / BLOCKED`

Local packages must be first-party fixtures with fixed versions, SHA-256 content digest, local digest attestation, strict manifest/schema, approved permissions, zero network/Secret access, and declarative UI. Installation, testing, approval, permission grant, binding, environment release, and enablement are separate records/steps. Revocation is terminal; disable/revoke block new Runs while preserving metadata and audit. Logical uninstall is allowed only after disable/revoke, clears grants and bindings, preserves manifest/history/audit, remains idempotent, and permanently blocks new Runs for that installation.
