# EPIC-02.6C acceptance evidence

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING` after every listed local gate passed.
This document must not be read as enterprise
acceptance for REQ-SEM/KNW/GRD or EPIC-02.6.

## Immutable scope and boundaries

- Domain-neutral semantic/knowledge version governance, current-DomainLock query, deterministic
  ContextManifest, structured Grounding and version impact only.
- All fixtures are local synthetic. Knowledge content is inert untrusted data and never executed.
- Agent, LLM, RAG, embedding, vector/graph/search runtime, Workflow/Run/Temporal, reference business,
  real data, external systems and external writes are absent.
- `DenyAllActionAdapter` and advisory-only product status remain unchanged.

## Verification ledger

| Evidence | Command | Final result |
| --- | --- | --- |
| Baseline and 02.6B evidence | clean `701bfec`; prior evidence digest checks; `make verify`; `make epic-02-6a`; `make epic-02-6b`; prior owner demos | passed before 02.6C edits; 342 Python, 41 contract, 6 Web unit tests; 88.34% baseline coverage |
| 02.6C focused | `make epic-02-6c` | 290 passed; 13 OpenAPI/semantic JSON exports identical; architecture 44 Python/11 Web, 0 violations; 6 Web tests passed |
| Owner walkthrough | `make epic-02-6c-owner-demo` | unique/ambiguous/unknown, deterministic/truncated context, valid/invalid Grounding, impact, authorization and restart passed; all runtime/model flags false |
| Migration | `make migration-proof` and clean-db `alembic upgrade head` | `0008` upgrade → base → `0008` passed; missing-parent entry test passed |
| Browser | focused semantic spec during implementation; `make e2e` in final run | 3 real Web + API paths passed, including semantic success and ambiguity/Viewer/Outsider refusal |
| Full regression/security/build | `make verify` | 410 Python at 87.18% combined line/branch coverage; 41 contract and 6 Vitest passed; format/lint/type, local scan, audits, build and source/wheel architecture passed |
| 02.6A/02.6B regression | `make epic-02-6a`; `make epic-02-6b` | 40 and 64 passed; consecutive FDS/OpenAPI export digests matched |
| Restart/smoke | `make smoke`; `make web-smoke` | independent API state and built Web preview against real persisted API passed |
| SBOM | `make sbom` | Python/Node CycloneDX generated; Node inventory contained 283 components |

## Acceptance mapping

The integration matrix maps all IDs in the 02.6C requirement to strict contracts, exact
Registry/DomainLock binding, unique/ambiguous/unknown and mapping conflict behavior, knowledge
lifecycle/security, deterministic/budgeted context, all three Grounding outcomes, semantic and
knowledge impact, authorization concealment, migration/restart/concurrency, strict API behavior,
real browser state and architecture bans. Final counts and hashes are recorded only after gates.

## Evidence binding

- Verified source commit: `50853d34f245ee3152c111121c765dd6ac8459d4`.
- Initial machine-evidence artifact commit: `5591dc59fd159df0a4f8e47214f0ff3d0dc504a5`.
- Machine evidence SHA-256:
  `908c4a07faef8caa3098b7df47b6ba378617fb3c133c8de4d1649f6a8f4e0308`.

The collector requires a clean committed source tree and binds dependency locks, OpenAPI and
semantic/FDS contracts, neutral fixtures, migration, requirement/ADR, owner demo/test/browser
sources, built wheel, SBOMs and coverage to that source commit. The artifact is committed
separately; hashes are never prefilled with a future commit.

## Not verified / blocked

- industry ontology or mapping correctness, enterprise knowledge owner/license/classification and
  hostile-file approval, data retention/deletion approval, independent security assessment;
- model grounding, model replacement, RAG quality, Agent hallucination or natural-language truth;
- PostgreSQL service concurrency/backup/restore, enterprise OIDC/SCIM/policy, PREPROD/PROD/UAT;
- Workflow Studio/Run/replay/debugger, any reference scenario, real/de-identified data or external
  system integration;
- G2, G4, G5A, G5B, enterprise supply chain and production release.

REQ-SEM-001, REQ-KNW-001 and REQ-GRD-001 may gain only this local synthetic sub-evidence.
REQ-FDS-001 and EPIC-02.6 remain `CLARIFYING / PARTIAL` pending separate product/enterprise review.
