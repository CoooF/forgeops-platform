from __future__ import annotations

import hashlib

from forgeops.platform_contracts.envelopes import AgentTaskRequest, AgentTaskResult


class DeterministicTemplateAgent:
    """Approved fallback: deterministic output reference, with no model or network call."""

    async def execute(self, request: AgentTaskRequest) -> AgentTaskResult:
        material = "|".join(
            (
                request.profile.contract_id,
                request.profile.version,
                request.input_ref,
                *sorted(request.evidence_refs),
                request.output_schema_ref,
            )
        ).encode()
        digest = hashlib.sha256(material).hexdigest()
        return AgentTaskResult(
            result_ref=f"template-result://sha256/{digest}",
            evidence_refs=request.evidence_refs,
            trace_ref=f"local-template://{request.context.trace_id}",
            degraded_to_template=True,
        )
