class EventBus:
    async def publish(self, mission_id: str, event_type: str) -> None:
        raise NotImplementedError

    async def subscribe(self, event_type: str) -> None:
        raise NotImplementedError

