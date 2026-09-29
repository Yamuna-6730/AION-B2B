from enum import StrEnum


class AgentState(StrEnum):
    CREATED = "created"
    INITIALIZED = "initialized"
    WAITING = "waiting"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

