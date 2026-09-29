class MissionService:
    async def create_mission(self) -> None:
        raise NotImplementedError

    async def list_missions(self) -> None:
        raise NotImplementedError

    async def get_mission(self, mission_id: str) -> None:
        raise NotImplementedError

