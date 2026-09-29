from fastapi import APIRouter, Depends

from app.schemas.planner import PlannerRunRequest, PlannerRunResponse
from app.services.planner import PlannerService

router = APIRouter(prefix="/planner", tags=["planner"])


def get_planner_service() -> PlannerService:
    return PlannerService()


@router.post("/run")
async def run_planner(
    request: PlannerRunRequest,
    service: PlannerService = Depends(get_planner_service),
) -> PlannerRunResponse:
    return await service.run_planner(str(request.mission_id))
