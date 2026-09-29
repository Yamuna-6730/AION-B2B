class AgentOrchestrator:
    async def dispatch(self, mission_id: str, task_id: str) -> None:
        raise NotImplementedError

