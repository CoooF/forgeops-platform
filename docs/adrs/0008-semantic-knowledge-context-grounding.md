# ADR-0008: DomainLock-bound semantic and knowledge context

- Status: `ACCEPTED_FOR_LOCAL_SYNTHETIC_SEMANTIC_ENGINEERING`
- Date: 2026-08-01
- Requirements: `REQ-FDS-001` (partial), `REQ-SEM-001` (local slice),
  `REQ-KNW-001` (local slice), `REQ-GRD-001` (local slice)
- Tests: `TEST-SEM-CONTRACT-001` through `TEST-ARCH-005` as listed in the 02.6C requirement

## Context

ADR-0007 persists an Organization installation and immutable current ProjectDomainLock,
but deliberately provides no semantic or knowledge runtime. Consumers need stable canonical
IDs and approved knowledge versions without inventing a second package-installation truth or
quietly guessing ambiguous terms. The future Workflow and Agent layers must not be introduced
to prove that prerequisite.

## Decision

Add domain-neutral `semantic_runtime` and `knowledge_hub` application modules behind
Repository and content-store Ports. Every semantic or knowledge version binds to the exact
Registry Component version, kind and digest already selected by the current DomainLock.
Semantic payloads and KnowledgeAsset versions are immutable; lifecycle state is separately
versioned and withdrawal is logical.

Semantic query is exact deterministic lookup over small canonical JSON payloads. NFKC plus
case/whitespace normalization is allowed; fuzzy matching and guessing are not. Ambiguous and
unknown inputs are results, not inferred answers. This slice intentionally uses relational
rows plus canonical JSON. It introduces no graph database, OWL/SHACL reasoner, embedding,
vector database, search cluster or automatic ontology merge.

Knowledge bodies are content-addressed local blobs with a hard 16 KiB cap and explicit
source, provenance, license, classification, purpose and effective period. Only UTF-8 plain
text and JSON are accepted. Content is returned as `untrustedData`, never used as code,
template, prompt, import, URL fetch or tool instruction. Audits store references and digests,
not bodies.

Context Compiler intersects actor Scope, current DomainLock, published/effective/purpose
eligibility and an explicit item/character budget. It orders exact references and exclusions
deterministically and stores an immutable canonical ContextManifest. Identical request identity
and inputs resolve to the same manifest and digest. It creates no Grant, runtime binding,
Agent, model, RAG or Workflow side effect.

Grounding validation is a deterministic structural membership check against one manifest.
It can reject missing citations, invalid endpoints or constraint declarations and request
clarification for unresolved terms. It cannot establish natural-language truth. Impact
analysis compares immutable versions and finds normalized Installation/ProjectDomainLock
references; Workflow impact is explicitly `NOT_EVALUATED`.

The existing general AuditRepository still has no shared unit of work with all 02.6C writes.
Success and denial evidence is correlated and append-only, but a database failure between a
domain transaction and its audit append can lose one side. That is a recorded local limitation,
not enterprise atomic-audit evidence.

## Consequences and limits

The platform now has a testable semantic/knowledge prerequisite independent of model behavior.
Small payloads are scanned in process; a future compatible indexing adapter may be added only
after measured need and without changing immutable IDs/digests. PostgreSQL service concurrency,
enterprise OIDC/SCIM, publisher namespace proof, license/legal/classification approval,
malware scanning, retention/deletion policy, remote object storage, real-data privacy,
industry ontology correctness and independent security review remain unverified.

EPIC-03 is not authorized by this ADR. The next product step is EPIC-02.7 design-system and
high-fidelity Workflow Studio prototyping; real connected execution, Run and debugger remain
EPIC-03 work requiring a separate decision and acceptance gate.
