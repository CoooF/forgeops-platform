from __future__ import annotations

import asyncio

from forgeops.platform_contracts.envelopes import (
    AgentTaskRequest,
    ContractRef,
    RequestContext,
    ResourceBudget,
)
from forgeops.platform_core.template_agent import DeterministicTemplateAgent


def test_template_fallback_is_deterministic_and_offline() -> None:
    request = AgentTaskRequest(
        context=RequestContext(
            traceId="trace-0001",
            actorRef="local-test",
            environment="TEST",
            purpose="contract-test",
        ),
        profile=ContractRef(
            contractId="generic.template", version="1.0.0", schemaRef="schema://profile"
        ),
        inputRef="blob://input",
        evidenceRefs=("evidence://1",),
        outputSchemaRef="schema://output",
        budget=ResourceBudget(
            cpuMillis=100,
            memoryMiB=64,
            timeoutSeconds=5,
            maxOutputBytes=1000,
        ),
    )
    agent = DeterministicTemplateAgent()
    first = asyncio.run(agent.execute(request))
    second = asyncio.run(agent.execute(request))
    assert first == second
    assert first.degraded_to_template is True
    assert first.result_ref.startswith("template-result://sha256/")
