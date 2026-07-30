from __future__ import annotations

import asyncio
from dataclasses import dataclass

from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

from forgeops.config import Settings
from forgeops.observability import configure_observability


@dataclass(frozen=True)
class ContractProbeInput:
    input_ref: str
    schema_ref: str


@workflow.defn(name="forgeops.platform.contract-probe.v1")
class ContractProbeWorkflow:
    """Opaque reference echo used only to prove a domain-neutral worker boundary."""

    @workflow.run
    async def run(self, input_value: ContractProbeInput) -> dict[str, str]:
        return {
            "status": "CONTRACT_ONLY",
            "inputRef": input_value.input_ref,
            "schemaRef": input_value.schema_ref,
        }


async def run_worker(settings: Settings | None = None) -> None:
    resolved = settings or Settings(service_name="forgeops-worker")
    configure_observability(resolved.service_name, resolved.log_level)
    client = await Client.connect(resolved.temporal_address, namespace=resolved.temporal_namespace)
    worker = Worker(
        client,
        task_queue=resolved.temporal_task_queue,
        workflows=[ContractProbeWorkflow],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
