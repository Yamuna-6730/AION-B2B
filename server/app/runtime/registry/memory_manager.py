class MemoryManager:
    async def load(self, mission_id: str) -> None:
        raise NotImplementedError

    async def persist(self, mission_id: str) -> None:
        raise NotImplementedError

