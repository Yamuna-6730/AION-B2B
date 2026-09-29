from collections.abc import Iterable

from app.agents.base.base_agent import BaseAgent


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def unregister(self, agent_name: str) -> None:
        self._agents.pop(agent_name, None)

    def get_agent(self, agent_name: str) -> BaseAgent | None:
        return self._agents.get(agent_name)

    def list_agents(self) -> Iterable[BaseAgent]:
        return self._agents.values()

