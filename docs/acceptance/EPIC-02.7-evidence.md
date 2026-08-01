# EPIC-02.7 acceptance evidence

Status: `READY_FOR_PRODUCT_OWNER_REVIEW`. This is local synthetic product-design evidence, not final product-owner acceptance and not authorization for EPIC-03.

## Scope and immutable boundaries

- Selected direction: A `静默控制台`, confirmed by the product owner on 2026-08-01.
- Main Agent is coordination-only: no DATA/CONTROL ports and no inherited child-node Skill/MCP bindings.
- Three execution Agent nodes each expose an independent model, Skill list, MCP list, Scope, budget and failure exits.
- `/design-preview/prototype` uses only isolated TypeScript fixture and React local state; it makes no `/v1` or `/health` request and performs no persistence or external write.
- Existing real Project/Registry/DomainLock/Semantic/Knowledge/Context/permission pages remain on `/` and their browser paths still pass.

## Verification ledger

| Evidence | Command | Result |
| --- | --- | --- |
| Selected prototype focused gate | `make epic-02-7` | format/lint/type/build; 6 Vitest; 3 selected-prototype Playwright passed |
| Full browser regression | `make e2e` | 8/8 passed: 2 direction, 3 selected prototype, 3 real Web/API journeys |
| Full engineering regression | `make verify` | 410 Python, 41 explicit contract, 6 Vitest; 87.18% line/branch coverage; scans/audits/build/source+wheel architecture passed |
| Semantic/knowledge regression | `make epic-02-6c` | 290 passed; 13 consecutive contract exports identical; architecture passed |
| Manual browser verification | in-app browser at 1440×900, 1280×800, 476×770 | no page overflow; no node overlap/outside-canvas; mobile visible controls ≥40px; main Agent focus/close and node resource tab verified |

## Screenshots

| View | SHA-256 |
| --- | --- |
| `prototype-a-studio-1440x900.png` | `ac79c3636f45e6f4b061978cc31880acf3c5c89a0a1c19a59e35b03866af9241` |
| `prototype-a-studio-1280x800.png` | `9e9c95840731b15ea7802eb4a0dad109884487f925c910e3a0d7061548341fae` |
| `prototype-a-studio-476x770.png` | `051fbc6b0042340346e06f45f58158e2ecfde1c9a3b07888d9771ff7330b081c` |
| `prototype-a-run-1440x900.png` | `9aac674a0b6e43417cfcf8be75975d7add8588529305917adfc738509d40c9d3` |
| `prototype-a-agents-1440x900.png` | `ce1a7374f7e51d6bd4001807caa7e6d56af5aaa34198073f4e8cc91fcda967dc` |

## Evidence binding

- Verified prototype source commit: `91431fadce28e18bfbd4941403c936e64593d332`.
- No new npm or Python runtime dependency was added.
- Machine-readable summary: `generated-epic-02.7-evidence.json`.
- Machine-readable summary SHA-256: `70537faac59d8f593464bcde4b02f884e2f3faeec027e394baa1c827c361546f`.
- This evidence document and machine summary are committed separately so they can truthfully reference the completed source commit.

## Not implemented or verified

Workflow/Version persistence; graph execution; Run, NodeExecution, PortEmission, breakpoint, step or fork; Agent/LLM/RAG; Skill/MCP installation or invocation; solver/simulation/candidate/review; real database connection or credential handling; real/de-identified data; external writes or industrial control; enterprise identity/security review; PostgreSQL service production behavior; PREPROD/PROD/UAT.

`REQ-WDBG`, EPIC-03, G2/G4/G5A/G5B, PREPROD/PROD/UAT do not advance. Final acceptance remains a human gate.
