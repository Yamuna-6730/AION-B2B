from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.schemas.missions import MissionCreateRequest, MissionOrchestratorResponse, MissionRunRequest
from app.services.mission_orchestrator import MissionOrchestratorService
from app.supabase.repositories.mission_repository import MissionRepository

router = APIRouter(prefix="/missions", tags=["missions"])


def get_mission_orchestrator_service() -> MissionOrchestratorService:
    return MissionOrchestratorService()


@router.post("/run", response_model=MissionOrchestratorResponse, status_code=status.HTTP_200_OK)
async def run_mission(
    request: MissionRunRequest,
    service: MissionOrchestratorService = Depends(get_mission_orchestrator_service),
) -> MissionOrchestratorResponse:
    return await service.run(request.mission_id)


@router.post("/create", response_model=MissionOrchestratorResponse, status_code=status.HTTP_201_CREATED)
async def create_and_run_mission(
    request: MissionCreateRequest,
    service: MissionOrchestratorService = Depends(get_mission_orchestrator_service),
) -> MissionOrchestratorResponse:
    mission = await service.mission_repository.create_mission(
        title=request.title,
        objective=request.objective,
        domain=request.domain,
        mission_type=request.mission_type,
        created_by=request.created_by,
        metadata=request.metadata,
    )
    mission_id = str(mission.get("id") or mission.get("mission_id"))
    return await service.run(mission_id)


@router.post("", response_model=MissionOrchestratorResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(
    request: MissionCreateRequest,
    service: MissionOrchestratorService = Depends(get_mission_orchestrator_service),
) -> MissionOrchestratorResponse:
    return await create_and_run_mission(request, service)


@router.get("")
async def list_missions() -> dict[str, object]:
    repository = MissionRepository()
    items = await repository.list_missions()
    return {"items": items, "total": len(items)}


@router.get("/{mission_id}")
async def get_mission(mission_id: str) -> dict[str, object]:
    repository = MissionRepository()
    return await repository.get_mission(mission_id)
