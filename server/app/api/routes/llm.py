from fastapi import APIRouter

from app.llm import llm_manager

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health")
async def llm_health() -> dict[str, object]:
    return await llm_manager.health_check()
