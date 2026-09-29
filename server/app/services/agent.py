class AgentService:
    async def list_agents(self) -> None:
        raise NotImplementedError

    async def execute_agent(self, agent_name: str) -> None:
        raise NotImplementedError

