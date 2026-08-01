# EPIC-02.6C semantic, knowledge, context, and grounding runtime

Status: `VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING`. This slice is
domain-neutral and local-synthetic. It does not grant enterprise acceptance for
`REQ-SEM-001`, `REQ-KNW-001`, `REQ-GRD-001`, or EPIC-02.6.

## Product boundary

The current ProjectDomainLock from EPIC-02.6B remains the only project domain-version
truth. This slice binds immutable Ontology, Terminology, Semantic Mapping and Knowledge
payloads to exact, usable Registry Component versions in that lock. Authorized users can
query canonical semantic IDs, compile a deterministic budgeted ContextManifest, validate
structured candidate references, and inspect semantic or knowledge version impact.

It does not call a model, execute an Agent, retrieve from a vector index, reason over a
graph database, define or run a Workflow, import scripts, connect to an external system,
or implement reference-domain behavior. Knowledge content is untrusted inert data.

## Invariants

- Semantic namespaces are URNs or HTTPS URIs. IDs, relation endpoints, constraints, term
  targets and mappings are validated strictly; unknown fields fail.
- Each payload binds to one exact Registry Component version of the matching kind and
  content digest. Published definitions are immutable; withdrawal preserves history.
- KnowledgeAsset metadata and each version preserve Organization, source, provenance,
  license, classification, allowed purposes, effective period, content type/ref/digest and
  lifecycle. Content is UTF-8 text or JSON, at most 16 KiB, stored content-addressed, never
  evaluated, imported, fetched as a URL, or executed.
- Query candidates come only from published payloads referenced by the current healthy
  DomainLock. NFKC/case/space normalization is deterministic. Unknown and ambiguous terms
  or mappings return explicit states with no silent guess.
- Context compilation requires purpose, evaluation time, explicit semantic/knowledge
  requests and a bounded item/character budget. Authorization, Project DomainLock,
  lifecycle, effective period and purpose are intersected. Ordering, exclusions, usage,
  truncation and SHA-256 digest are deterministic; immutable manifests remain readable.
- A ContextManifest records `authorizationEffect=NONE`, and model, Agent, RAG, runtime and
  Workflow execution flags remain false. Audit records contain IDs/digests and decisions,
  never knowledge body content.
- Grounding validation checks only structured membership and declared relations,
  constraints, mappings and citations against one ContextManifest. Results are
  `VALID`, `INVALID` or `NEEDS_CLARIFICATION`; they do not claim prose factuality.
- Impact reports compare immutable v1/v2 records, identify affected Installation and
  ProjectDomainLock references, preserve history, and always say Workflow impact is
  `NOT_EVALUATED`.
- Writes use `Idempotency-Key`; lifecycle transitions use `If-Match`; cross-Organization
  detail and error paths return concealed 404 responses. No physical delete API exists.

## Stable API and persistence

The API provides semantic payload create/list/detail/publish/withdraw; Organization
KnowledgeAsset create/list and immutable version/content/publish/withdraw; Project semantic
component inventory/query; ContextManifest compile/read; structured Grounding validation;
and semantic/knowledge impact create/list. Migration `0008` adds separate semantic payload,
knowledge asset/version, context manifest, grounding result, impact and idempotency tables.
Normalized FKs and unique/check constraints protect exact package and immutable-history
relationships; JSON contains canonical contract content, not a second installation truth.

## Authorization intent

Semantic registry view/manage, query, Knowledge view/manage, Context compile, Grounding
validate and impact view are separate deny-by-default permissions. Organization/Workspace/
Project Owners inherit applicable access. Editor and Viewer can read/query/compile/validate
within their scope but cannot publish. Package Operator governs semantic and knowledge
versions. Outsiders and wrong-Organization principals discover nothing.

## Stable test IDs

| ID | Local synthetic evidence |
| --- | --- |
| TEST-SEM-CONTRACT-001 | Strict schema, unknown field/URI rejection and canonical digest |
| TEST-SEM-REGISTRY-001 | Exact kind/digest binding, immutable version and publish/withdraw |
| TEST-SEM-QUERY-001 | SemanticId, term, relation and constraint lookup through current DomainLock |
| TEST-SEM-MAPPING-001 | Source mapping, unit/time metadata and conflict response |
| TEST-SEM-AMBIGUITY-001 | Unique/ambiguous/unknown/unauthorized/withdrawn with zero guesses |
| TEST-KNW-LIFECYCLE-001 | Metadata, immutable versions, effective period, publish and withdrawal |
| TEST-KNW-SEC-001 | Injection inertness, strict content/size, cross-scope concealment and no audit leak |
| TEST-CONTEXT-COMPILER-001 | Scope intersection, stable digest, budget/truncation and exclusions |
| TEST-GROUNDING-001 | VALID/INVALID/NEEDS_CLARIFICATION and structured reference checks |
| TEST-SEM-IMPACT-001 | Semantic/knowledge v1-v2 diff, affected locks, Workflow NOT_EVALUATED |
| TEST-SEM-AUTH-001 | Owner/Viewer/Outsider, deny by default and 404 concealment |
| TEST-SEM-PERSISTENCE-001 | `0008`, constraints, restart history and optimistic concurrency |
| TEST-SEM-API-001 | Strict DTO, pagination, idempotency, If-Match and stable errors |
| TEST-WEB-SEM-001 | Real Web/API/DB success plus ambiguity/permission rejection |
| TEST-ARCH-005 | Domain-neutral core; no reverse FDS dependency or LLM/vector/graph runtime |

These are local sub-evidence for `TEST-SEM-001/002`, `TEST-KNW-001/002` and
`TEST-GRD-001`. They do not validate an industry ontology, enterprise license/classification,
RAG quality, model grounding, model replacement, Agent hallucination, Workflow execution,
real data, cross-industry behavior, PostgreSQL service behavior or release gates.

## Acceptance boundary

The slice may be marked `VERIFIED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING` only after
focused and full regression, 02.6A/02.6B regression, migration round trip, independent
restart, owner demo, real Playwright E2E, build, coverage, dependency/security, source/wheel
architecture, deterministic contract export, SBOM, human evidence and commit-bound machine
evidence all pass. Otherwise it remains `PARTIAL`. G2, G4, G5A, G5B, PREPROD, PROD and UAT
cannot advance from this evidence.
