from __future__ import annotations

# Package-requested permissions are declarations, never authorization grants. This
# local dictionary is shared by the legacy Scenario SDK and FDS contract kernel.
ALLOWED_PACKAGE_PERMISSIONS: frozenset[str] = frozenset(
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

FORBIDDEN_PACKAGE_CAPABILITIES: frozenset[str] = frozenset(
    {
        "network.unrestricted",
        "secret.read",
        "data-source.direct-read",
        "proposal.write",
        "external-system.write",
        "industrial-control.write",
    }
)
