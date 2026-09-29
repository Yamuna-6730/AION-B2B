class MissionRuntime:
    async def start(self, mission_id: str) -> None:
        raise NotImplementedError

    async def stop(self, mission_id: str) -> None:
        raise NotImplementedError

