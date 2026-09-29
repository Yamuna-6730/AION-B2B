from app.agents.base.response import AgentResponse
from app.agents.base.task import AgentTask


class BaseAgent:
    name: str
    description: str
    category: str
    version: str
    priority: int
    supported_inputs: tuple[str, ...]
    supported_outputs: tuple[str, ...]

    async def initialize(self) -> None:
        raise NotImplementedError

    async def run(self, task: AgentTask) -> AgentResponse:
        raise NotImplementedError

    async def validate(self, task: AgentTask) -> bool:
        raise NotImplementedError

    async def summarize(self, response: AgentResponse) -> str:
        raise NotImplementedError

    async def calculate_confidence(self, response: AgentResponse) -> float:
        raise NotImplementedError

    async def cleanup(self) -> None:
        raise NotImplementedError

