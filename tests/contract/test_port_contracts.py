from __future__ import annotations

from typing import get_type_hints

from forgeops.platform_contracts import ports


def test_required_ports_are_versioned_domain_neutral_protocols() -> None:
    names = {
        "DataProviderPort",
        "AgentTaskPort",
        "SolverPort",
        "SimulationPort",
        "EvaluationPort",
        "NodeExecutionPort",
    }
    assert names <= set(vars(ports))
    for name in names:
        protocol = getattr(ports, name)
        operation = (
            "provide"
            if name == "DataProviderPort"
            else (
                "solve"
                if name == "SolverPort"
                else (
                    "simulate"
                    if name == "SimulationPort"
                    else ("evaluate" if name == "EvaluationPort" else "execute")
                )
            )
        )
        hints = get_type_hints(getattr(protocol, operation))
        assert "request" in hints
        assert "return" in hints
