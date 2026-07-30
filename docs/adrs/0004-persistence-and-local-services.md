# ADR-0004: PostgreSQL target and direct-run persistence

- Status: `ACCEPTED_FOR_LOCAL_SYNTHETIC_ENGINEERING`
- Enterprise topology: `PROPOSED / BLOCKED`

PostgreSQL 17 is the target transaction store in local Compose. A file-backed SQLite adapter is permitted only for direct local development and deterministic CI where Docker is unavailable. Both use the same repository and Alembic migrations. Audit exposes append/list only and database triggers reject update/delete. Temporal is present only as a generic worker skeleton; workflow runtime acceptance belongs to EPIC-03.
