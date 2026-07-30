from __future__ import annotations

from typing import Protocol

from forgeops.platform_contracts.envelopes import (
    AgentTaskRequest,
    AgentTaskResult,
    DataProviderRequest,
    DataProviderResult,
    EvaluationRequest,
    EvaluationResult,
    NodeExecutionRequest,
    NodeExecutionResult,
    SimulationRequest,
    SimulationResult,
    SolverRequest,
    SolverResult,
)


class DataProviderPort(Protocol):
    async def provide(self, request: DataProviderRequest) -> DataProviderResult: ...


class AgentTaskPort(Protocol):
    async def execute(self, request: AgentTaskRequest) -> AgentTaskResult: ...


class SolverPort(Protocol):
    async def solve(self, request: SolverRequest) -> SolverResult: ...


class SimulationPort(Protocol):
    async def simulate(self, request: SimulationRequest) -> SimulationResult: ...


class EvaluationPort(Protocol):
    async def evaluate(self, request: EvaluationRequest) -> EvaluationResult: ...


class NodeExecutionPort(Protocol):
    async def execute(self, request: NodeExecutionRequest) -> NodeExecutionResult: ...
