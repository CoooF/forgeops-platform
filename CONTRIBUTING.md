# Contributing

1. Link changes to a `REQ-*`, `ADR-*`, and `TEST-*` identifier.
2. Add contracts and negative tests before API or persistence behavior.
3. Run `make verify` and preserve the generated evidence summary.
4. Do not weaken advisory-only, isolation, compatibility, or audit controls to make a test pass.
5. A local maintainer review is not enterprise approval. Security, OT, data, operations, domain, and independent review owners remain TBD.
