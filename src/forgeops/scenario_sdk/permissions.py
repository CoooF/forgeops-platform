from __future__ import annotations

ALLOWED_SCENARIO_PERMISSIONS: frozenset[str] = frozenset(
    {
        "synthetic-data.read",
        "evidence.read",
        "candidate.create",
        "simulation.create",
        "evaluation.create",
        "agent-template.execute",
        "node.execute",
        "ui-extension.declare",
    }
)

FORBIDDEN_WORKER_CAPABILITIES: frozenset[str] = frozenset(
    {
        "network.unrestricted",
        "secret.read",
        "data-source.direct-read",
        "proposal.write",
        "external-system.write",
        "industrial-control.write",
    }
)
