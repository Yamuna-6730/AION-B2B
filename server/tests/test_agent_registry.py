from app.agents.base.agent_registry import AgentRegistry
from app.agents.catalog import PlannerAgent


def test_agent_registry_registers_and_returns_agents() -> None:
    registry = AgentRegistry()
    agent = PlannerAgent()

    registry.register(agent)

    assert registry.get_agent("planner") is agent
    assert list(registry.list_agents()) == [agent]

